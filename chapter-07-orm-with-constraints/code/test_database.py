"""Run with python3 -m unittest -v. All writes use temporary databases."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from peewee import IntegrityError

import database
from database import Pet
import upgrade_database


class ConstraintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "pets.db")
        database.initialize(self.path)
        self.owner_id = database.create_owner({"name": "Alex", "city": "Kent"})

    def tearDown(self):
        database.close_connection()
        self.temp.cleanup()

    def pet(self, **changes):
        values = {"name": "Casey", "type": "dog", "age": "9", "owner_id": self.owner_id}
        values.update(changes)
        return values

    def test_foreign_keys_are_on(self):
        self.assertEqual(database.db.execute_sql("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_missing_owner_is_rejected(self):
        with self.assertRaises(IntegrityError):
            database.create_pet(self.pet(owner_id=999999))
        self.assertEqual(database.get_pets(), [])

    def test_python_checks_come_first(self):
        for values in [self.pet(name=" "), self.pet(type=""), self.pet(age="-1"),
                       self.pet(age="abc"), {"name": "x", "type": "dog"}]:
            with self.assertRaises(ValueError):
                database.create_pet(values)
        self.assertEqual(database.get_pets(), [])

    def test_check_constraints_work_below_the_python_checks(self):
        # Pet.create skips our helper functions, so only the table's rules apply.
        for values in [dict(name="   ", type="dog", age=1),
                       dict(name="Casey", type="  ", age=1),
                       dict(name="Casey", type="dog", age=-1)]:
            with self.assertRaises(IntegrityError):
                Pet.create(owner=self.owner_id, **values)
        self.assertEqual(database.get_pets(), [])

    def test_blank_age_becomes_zero(self):
        pet_id = database.create_pet(self.pet(age=""))
        self.assertEqual(database.get_pet(pet_id)["age"], 0)

    def test_owner_with_pets_cannot_be_deleted(self):
        pet_id = database.create_pet(self.pet())
        with self.assertRaises(IntegrityError):
            database.delete_owner(self.owner_id)
        self.assertIsNotNone(database.get_owner(self.owner_id))
        database.delete_pet(pet_id)
        database.delete_owner(self.owner_id)
        self.assertIsNone(database.get_owner(self.owner_id))

    def test_reassigning_a_pet_frees_the_first_owner(self):
        other = database.create_owner({"name": "Sam"})
        pet_id = database.create_pet(self.pet())
        database.update_pet(pet_id, self.pet(owner_id=other))
        self.assertEqual(database.get_pet(pet_id)["owner_name"], "Sam")
        database.delete_owner(self.owner_id)

    def test_failed_update_leaves_the_pet_unchanged(self):
        pet_id = database.create_pet(self.pet())
        with self.assertRaises(IntegrityError):
            database.update_pet(pet_id, self.pet(name="Renamed", owner_id=999999))
        self.assertEqual(database.get_pet(pet_id)["name"], "Casey")

    def test_atomic_group_rolls_back_after_a_constraint_failure(self):
        with self.assertRaises(IntegrityError):
            with database.db.atomic():
                database.create_pet(self.pet(name="First"))
                database.create_pet(self.pet(name="Second", owner_id=999999))
        self.assertEqual(database.get_pets(), [])

    def test_blank_owner_details_are_stored_as_null(self):
        owner = database.get_owner(database.create_owner({"name": "Sam", "city": " ", "type_of_home": ""}))
        self.assertIsNone(owner["city"])
        self.assertIsNone(owner["type_of_home"])

    def test_pets_list_in_name_then_id_order(self):
        for name in ["Zelda", "Alex", "Alex"]:
            database.create_pet(self.pet(name=name))
        pets = database.get_pets()
        self.assertEqual([p["name"] for p in pets], ["Alex", "Alex", "Zelda"])
        self.assertLess(pets[0]["id"], pets[1]["id"])

    def test_table_definitions_carry_the_rules(self):
        with sqlite3.connect(self.path) as connection:
            sql = connection.execute("select sql from sqlite_master where name='pet'").fetchone()[0]
        for text in ["CHECK (age >= 0)", "CHECK (length(trim(name)) > 0)", "ON DELETE RESTRICT"]:
            self.assertIn(text, sql)


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / "pets.db")

    def tearDown(self):
        database.close_connection()

    def make(self, script):
        with sqlite3.connect(self.path) as connection:
            connection.executescript(script)

    def rows(self, sql):
        with sqlite3.connect(self.path) as connection:
            return connection.execute(sql).fetchall()

    # Table layouts from the earlier examples.
    TEXT_OWNER = """
        create table pet (id integer primary key autoincrement, name text not null,
            type text not null, age integer, food text, owner text);
        insert into pet values (1, 'Casey', 'dog', 9, 'kibble', 'Alex');
        insert into pet values (2, 'Heidi', 'cat', 15, 'tuna', 'alex');
        insert into pet values (3, 'Suzy', 'mouse', 2, 'seeds', '');
        insert into pet values (4, 'Bad', 'dog', -4, 'x', 'Sam');
    """
    OWNER_TABLE = """
        create table owner (id integer primary key autoincrement, name text not null, city text, type_of_home text);
        create table pet (id integer primary key autoincrement, name text not null, type text not null,
            age integer, food text, owner_id integer not null,
            foreign key (owner_id) references owner(id) on delete restrict);
        insert into owner values (1, 'Alex', 'Kent', 'house');
        insert into owner values (2, 'Sam', null, null);
        insert into pet values (1, 'Casey', 'dog', 9, 'kibble', 1);
        insert into pet values (2, '  ', 'dog', -2, null, 2);
    """
    NO_OWNERS = """
        create table pet (id integer primary key, name text not null, type text not null, age integer, food text);
        insert into pet (name, type, age) values ('Casey', 'dog', 9);
        insert into pet (name, type, age) values ('Felix', 'cat', 3);
    """

    def test_initialize_refuses_an_older_file_and_leaves_it_alone(self):
        self.make(self.NO_OWNERS)
        with self.assertRaises(database.SchemaNotCurrent) as caught:
            database.initialize(self.path)
        self.assertIn("upgrade_database.py", str(caught.exception))
        self.assertEqual(len(self.rows("select * from pet")), 2)
        self.assertEqual(self.rows("select name from sqlite_master where type='table'"), [("pet",)])

    def test_upgrade_of_the_text_owner_layout(self):
        self.make(self.TEXT_OWNER)
        report = upgrade_database.upgrade(self.path)
        self.assertEqual(report["status"], "upgraded")
        self.assertEqual(report["pets"], 3)
        self.assertEqual(report["unassigned"], 1)
        self.assertEqual(report["not_carried"], ["food"])
        self.assertEqual(len(report["skipped"]), 1)
        self.assertIn("age >= 0", report["skipped"][0])
        self.assertEqual(self.rows("select name from owner order by id"), [("Alex",), ("Unassigned",), ("Sam",)])
        self.assertEqual(self.rows("select id, owner_id from pet order by id"), [(1, 1), (2, 1), (3, 2)])
        # The original file is kept, unchanged.
        with sqlite3.connect(report["backup"]) as connection:
            self.assertEqual(connection.execute("select count(*) from pet").fetchone()[0], 4)

    def test_upgrade_of_the_owner_table_layout_keeps_ids_and_skips_bad_rows(self):
        self.make(self.OWNER_TABLE)
        report = upgrade_database.upgrade(self.path)
        self.assertEqual((report["owners"], report["pets"]), (2, 1))
        self.assertEqual(len(report["skipped"]), 1)
        self.assertEqual(self.rows("select pet.id, pet.name, owner.city, pet.owner_id from pet join owner on owner.id = pet.owner_id"),
                         [(1, "Casey", "Kent", 1)])
        self.assertEqual(database.schema_problems(self.path), [])

    def test_upgrade_of_the_layout_without_owners(self):
        self.make(self.NO_OWNERS)
        report = upgrade_database.upgrade(self.path)
        self.assertEqual((report["pets"], report["unassigned"]), (2, 2))
        self.assertEqual(self.rows("select name from owner"), [("Unassigned",)])
        database.initialize(self.path)
        self.assertEqual([p["owner_name"] for p in database.get_pets()], ["Unassigned", "Unassigned"])

    def test_upgraded_tables_enforce_the_rules(self):
        self.make(self.OWNER_TABLE)
        upgrade_database.upgrade(self.path)
        database.initialize(self.path)
        with self.assertRaises(IntegrityError):
            database.db.execute_sql("insert into pet (name, type, age, owner_id) values ('  ', 'dog', -4, 1)")

    def test_current_and_missing_files_are_left_alone_or_created(self):
        self.assertEqual(upgrade_database.upgrade(self.path)["status"], "created")
        self.assertEqual(upgrade_database.upgrade(self.path)["status"], "current")
        self.assertEqual(sorted(p.name for p in Path(self.temp.name).iterdir()), ["pets.db"])

    def test_a_second_upgrade_never_overwrites_the_first_backup(self):
        self.make(self.NO_OWNERS)
        first = upgrade_database.upgrade(self.path)["backup"]
        self.make("drop table pet; create table pet (id integer primary key, name text, type text, age integer)")
        second = upgrade_database.upgrade(self.path)["backup"]
        self.assertNotEqual(first, second)
        self.assertTrue(Path(first).exists() and Path(second).exists())


if __name__ == "__main__":
    unittest.main()
