"""Run with python3 -m unittest -v. Checks the behavior the chapter describes.

Every test uses temporary files.
"""
from datetime import date
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

import dataset
from sqlalchemy.exc import IntegrityError, OperationalError

import build_mystery

HERE = Path(__file__).resolve().parent


class DatasetBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "scratch.db"
        self.db = dataset.connect(f"sqlite:///{self.path}")
        self.addCleanup(self.db.close)

    def columns(self, table):
        with sqlite3.connect(self.path) as connection:
            return {row[1]: row[2] for row in connection.execute(f"pragma table_info({table})")}

    def test_a_table_creates_itself_with_an_integer_key(self):
        self.db["pet"].insert({"name": "Dorothy", "age": 9})
        self.assertEqual(self.columns("pet"), {"id": "INTEGER", "name": "TEXT", "age": "BIGINT"})

    def test_a_new_key_adds_a_column(self):
        pets = self.db["pet"]
        pets.insert({"name": "Dorothy"})
        pets.insert({"name": "Heidi", "food": "tuna"})
        self.assertEqual(pets.columns, ["id", "name", "food"])
        self.assertIsNone(pets.find_one(name="Dorothy")["food"])

    def test_a_typo_in_a_key_creates_a_column_too(self):
        pets = self.db["pet"]
        pets.insert({"name": "Dorothy", "age": 9})
        pets.insert({"name": "Heidi", "aeg": 15})
        self.assertIn("aeg", pets.columns)

    def test_types_come_from_the_first_value(self):
        self.db["sample"].insert({
            "a_int": 1, "a_float": 2.5, "a_bool": True, "a_date": date(2026, 9, 1),
            "a_dict": {"x": 1}, "a_text": "hi"})
        self.assertEqual(self.columns("sample"), {
            "id": "INTEGER", "a_int": "BIGINT", "a_float": "FLOAT", "a_bool": "BOOLEAN",
            "a_date": "DATE", "a_dict": "JSON", "a_text": "TEXT"})

    def test_ensure_schema_false_stops_new_tables_and_drops_unknown_keys(self):
        self.db["pet"].insert({"name": "A"})
        self.db.close()
        strict = dataset.connect(f"sqlite:///{self.path}", ensure_schema=False)
        self.addCleanup(strict.close)
        strict["pet"].insert({"name": "B", "aeg": 15})
        self.assertEqual(strict["pet"].columns, ["id", "name"])
        self.assertEqual(len(strict["pet"]), 2)
        with self.assertRaises(dataset.util.DatasetError):
            strict["newtable"].insert({"name": "C"})

    def test_no_alembic_bookkeeping_table_is_created(self):
        self.db["pet"].insert({"name": "Dorothy"})
        self.db["pet"].insert({"name": "Heidi", "food": "tuna"})
        self.assertEqual(self.db.tables, ["pet"])

    def test_write_methods_and_their_return_values(self):
        pets = self.db["pet"]
        self.assertEqual(pets.insert({"name": "A", "age": 1}), 1)
        pets.insert_many([{"name": "B", "age": 2}, {"name": "C", "age": 3}])
        self.assertEqual(pets.update({"name": "B", "age": 22}, ["name"]), 1)
        pets.upsert({"name": "A", "age": 9}, ["name"])
        pets.upsert({"name": "D", "age": 4}, ["name"])
        self.assertEqual(len(pets), 4)
        self.assertEqual(pets.find_one(name="A")["age"], 9)
        self.assertTrue(pets.delete(name="C"))
        self.assertFalse(pets.delete(name="nobody"))
        self.assertEqual(pets.count(age={">=": 4}), 3)

    def test_upsert_return_values_and_upsert_many_runs_row_by_row(self):
        pets = self.db["pets"]
        pets.insert({"name": "Buddy", "age": 6})
        self.assertIs(pets.upsert({"name": "Buddy", "age": 7}, ["name"]), True)
        new_id = pets.upsert({"name": "Rex", "age": 2}, ["name"])
        self.assertIsNot(new_id, True)
        self.assertEqual(new_id, pets.find_one(name="Rex")["id"])
        pets.upsert_many([{"name": "Rex", "age": 3}, {"name": "Fido", "age": 1}], ["name"])
        self.assertEqual(pets.find_one(name="Rex")["age"], 3)
        self.assertEqual(pets.count(), 3)

    def test_find_options(self):
        pets = self.db["pet"]
        pets.insert_many([{"name": n, "age": a} for n, a in [("A", 1), ("B", 5), ("C", 3)]])
        found = pets.find(age={">=": 3}, order_by="-age", _limit=1)
        self.assertEqual([p["name"] for p in found], ["B"])
        self.assertEqual([p["name"] for p in pets.find(name=["A", "C"], order_by="name")], ["A", "C"])
        self.assertEqual(sorted(p["age"] for p in pets.distinct("age")), [1, 3, 5])

    def test_rows_are_dictionaries(self):
        self.db["pet"].insert({"name": "A"})
        self.assertIsInstance(self.db["pet"].find_one(name="A"), dict)

    def test_a_transaction_rolls_back_as_a_group(self):
        self.db["pet"].insert({"name": "Existing"})
        with self.assertRaises(RuntimeError):
            with dataset.connect(f"sqlite:///{self.path}") as tx:
                tx["pet"].insert({"name": "Inside"})
                raise RuntimeError("stop")
        self.assertIsNone(self.db["pet"].find_one(name="Inside"))

    def test_rules_written_in_sql_still_apply_but_foreign_keys_need_asking(self):
        with sqlite3.connect(self.path) as connection:
            connection.executescript("""
                create table kind (id integer primary key, name text not null);
                create table pets (id integer primary key, name text not null,
                    age integer check (age >= 0), kind_id integer references kind(id));
                insert into kind values (1, 'Dog');
            """)
        pets = self.db["pets"]
        with self.assertRaises(IntegrityError):
            pets.insert({"name": None, "age": 1, "kind_id": 1})
        with self.assertRaises(IntegrityError):
            pets.insert({"name": "x", "age": -1, "kind_id": 1})
        pets.insert({"name": "orphan", "age": 1, "kind_id": 999})
        self.assertIsNotNone(pets.find_one(name="orphan"))

        strict = dataset.connect(
            f"sqlite:///{self.path}", on_connect_statements=["PRAGMA foreign_keys=ON"])
        self.addCleanup(strict.close)
        with self.assertRaises(IntegrityError):
            strict["pets"].insert({"name": "orphan2", "age": 1, "kind_id": 999})

    def test_connecting_switches_sqlite_to_write_ahead_logging(self):
        self.db["pet"].insert({"name": "A"})
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("pragma journal_mode").fetchone()[0], "wal")


class MysteryDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / "mystery.db"
        build_mystery.build(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def open(self):
        db = dataset.connect(f"sqlite:///file:{self.path}?mode=ro&uri=true", sqlite_wal_mode=False)
        self.addCleanup(db.close)
        return db

    def test_the_builder_will_not_overwrite_a_file(self):
        result = subprocess.run(
            [sys.executable, str(HERE / "build_mystery.py"), str(self.path)],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--replace", result.stderr)

    def test_exploring_tables_views_and_columns(self):
        db = self.open()
        self.assertEqual(db.tables, ["category", "character", "timezone"])
        self.assertEqual(db.views, ["numeric_character", "script_summary"])
        self.assertEqual(db["timezone"].columns, [
            "name", "region", "city", "january_offset_minutes", "july_offset_minutes", "uses_dst"])
        self.assertGreater(len(db["character"]), 50000)

    def test_the_sample_questions_have_answers(self):
        db = self.open()
        top = next(iter(db["script_summary"].find(order_by="-characters")))
        self.assertEqual(top["script"], "CJK")
        sevens = [row["name"] for row in db["numeric_character"].find(numeric_value=7)]
        self.assertIn("DEVANAGARI DIGIT SEVEN", sevens)
        odd = {row["name"] for row in db.query(
            "select name from timezone where january_offset_minutes % 60 != 0")}
        self.assertIn("Asia/Kabul", odd)

    def test_a_read_only_connection_cannot_write_and_leaves_no_extra_files(self):
        db = self.open()
        with self.assertRaises(OperationalError):
            db["character"].insert({"codepoint": 1, "symbol": "x", "name": "n",
                                    "category": "Cc", "script": "n", "width": "N"})
        self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()), ["mystery.db"])

    def test_every_character_category_has_a_description(self):
        db = self.open()
        missing = list(db.query(
            "select distinct category from character where category not in (select code from category)"))
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
