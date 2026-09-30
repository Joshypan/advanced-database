"""Run with python3 -m unittest -v. Checks the behavior the chapter describes.

Every test uses temporary files and a small made-up file in the IMDb format,
so nothing here needs the real IMDb download.
"""
import contextlib
import gzip
import io
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import tempfile
import unittest

import compare_python_sql
import explore_indexes
import fruits
import import_imdb

HERE = Path(__file__).resolve().parent
TYPES = ["movie", "short", "tvEpisode", "tvSeries"]


def write_gz(path, text):
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write(text)


def make_imdb_files(directory, count=3000):
    """Write small title.basics and title.ratings files with IMDb's layout."""
    generator = random.Random(1)
    basics = ["tconst\ttitleType\tprimaryTitle\toriginalTitle\tisAdult\tstartYear\t"
              "endYear\truntimeMinutes\tgenres"]
    ratings = ["tconst\taverageRating\tnumVotes"]
    for number in range(1, count + 1):
        tconst = f"tt{number:07d}"
        kind = generator.choice(TYPES)
        year = generator.choice([r"\N"] + [str(y) for y in range(1990, 2000)])
        title = f"Title {generator.randrange(500)}"
        basics.append(f"{tconst}\t{kind}\t{title}\t{title}\t0\t{year}\t\\N\t90\tDrama")
        if number % 2 == 0:
            ratings.append(f"{tconst}\t{generator.randrange(10, 100) / 10}\t"
                           f"{generator.randrange(5, 5000)}")
    basics.append("tt0068646\tmovie\tThe Godfather\tThe Godfather\t0\t1972\t\\N\t175\tCrime,Drama")
    ratings.append("tt0068646\t9.2\t2000000")
    directory = Path(directory)
    write_gz(directory / "title.basics.tsv.gz", "\n".join(basics) + "\n")
    write_gz(directory / "title.ratings.tsv.gz", "\n".join(ratings) + "\n")


class FruitsTests(unittest.TestCase):
    def plans(self):
        connection = fruits.build()
        self.addCleanup(connection.close)
        found = {}
        for heading, index, queries in fruits.STEPS:
            if index:
                connection.execute(index)
            for sql in queries:
                found[(heading, sql)] = " | ".join(fruits.plan(connection, sql))
        return found

    def test_the_seven_rows_are_there(self):
        connection = fruits.build()
        self.addCleanup(connection.close)
        self.assertEqual(connection.execute("select count(*) from fruitsforsale").fetchone()[0], 7)

    def test_each_index_changes_the_plan_as_the_chapter_says(self):
        plans = self.plans()
        self.assertIn("SCAN", plans[("No indexes", fruits.PEACH)])
        self.assertIn("INTEGER PRIMARY KEY", plans[("No indexes", fruits.ROWID)])
        self.assertIn("TEMP B-TREE FOR ORDER BY", plans[("No indexes", fruits.SORTED)])
        self.assertIn("SEARCH fruitsforsale USING INDEX Idx1",
                      plans[("Idx1 on fruit", fruits.PEACH)])
        self.assertNotIn("TEMP B-TREE", plans[("Idx1 on fruit", fruits.SORTED)])
        self.assertIn("USING INDEX Idx2 (state=?)", plans[("Idx2 on state", fruits.CA_ORANGE)])
        self.assertIn("Idx3 (fruit=? AND state=?)",
                      plans[("Idx3 on fruit, state", fruits.CA_ORANGE)])
        self.assertNotIn("TEMP B-TREE",
                         plans[("Idx3 on fruit, state", fruits.ORANGES_BY_STATE)])
        covering = "Idx4 on fruit, state, price (a covering index)"
        self.assertIn("COVERING INDEX Idx4", plans[(covering, fruits.CA_ORANGE)])
        self.assertIn("LAST TERM OF ORDER BY", plans[(covering, fruits.PARTIAL)])

    def test_indexes_never_change_the_answer(self):
        connection = fruits.build()
        self.addCleanup(connection.close)
        before = sorted(connection.execute(fruits.EITHER).fetchall())
        for _, index, _ in fruits.STEPS:
            if index:
                connection.execute(index)
        self.assertEqual(sorted(connection.execute(fruits.EITHER).fetchall()), before)
        self.assertEqual(before, [(0.8,), (0.85,), (1.05,)])


class ImdbTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        make_imdb_files(self.directory)
        self.database = str(self.directory / "imdb.db")
        with contextlib.redirect_stdout(io.StringIO()):
            import_imdb.import_all(self.directory, self.database)
        self.connection = sqlite3.connect(self.database)
        self.addCleanup(self.connection.close)

    def one(self, sql, *parameters):
        return self.connection.execute(sql, parameters).fetchone()[0]

    def test_all_rows_arrive(self):
        self.assertEqual(self.one("select count(*) from titles"), 3001)
        self.assertEqual(self.one("select count(*) from ratings"), 1501)

    def test_missing_values_become_null_and_numbers_become_numbers(self):
        self.assertGreater(self.one("select count(*) from titles where start_year is null"), 0)
        self.assertEqual(self.one("select count(*) from titles where start_year = '\\N'"), 0)
        self.assertEqual(self.one("select typeof(start_year) from titles where tconst = 'tt0068646'"),
                         "integer")
        self.assertEqual(self.one("select typeof(average_rating) from ratings where tconst = 'tt0068646'"),
                         "real")

    def test_loading_uses_more_than_one_chunk(self):
        original = import_imdb.CHUNK_SIZE
        import_imdb.CHUNK_SIZE = 700
        self.addCleanup(setattr, import_imdb, "CHUNK_SIZE", original)
        other = str(self.directory / "chunked.db")
        with contextlib.redirect_stdout(io.StringIO()):
            import_imdb.import_all(self.directory, other)
        connection = sqlite3.connect(other)
        self.addCleanup(connection.close)
        self.assertEqual(connection.execute("select count(*) from titles").fetchone()[0], 3001)

    def test_the_importer_will_not_overwrite_a_database(self):
        result = subprocess.run(
            [sys.executable, str(HERE / "import_imdb.py"), "--data-dir", str(self.directory),
             "--database", self.database], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)

    def plan(self, sql, parameters=()):
        return " | ".join(explore_indexes.plan(self.connection, sql, parameters))

    def test_the_steps_in_the_chapter_produce_the_plans_it_describes(self):
        seen = {}
        for heading, sql, parameters, create in explore_indexes.STEPS:
            if create:
                self.connection.execute(create)
            seen[heading] = self.plan(sql, parameters)
        self.assertIn("sqlite_autoindex_titles_1", seen["Lookup by the primary key (tconst)"])
        self.assertTrue(seen["Lookup by a column with no index"].startswith("SCAN titles"))
        self.assertIn("SEARCH titles USING INDEX idx_titles_primary_title",
                      seen["The same query after an index on primary_title"])
        self.assertTrue(seen["LIKE with a prefix, against a case-sensitive index"].startswith("SCAN titles"))
        self.assertIn("idx_titles_primary_title_nocase",
                      seen["The same LIKE after an index that ignores case"])
        self.assertTrue(seen["LIKE with a wildcard at the front"].startswith("SCAN titles"))
        self.assertIn("idx_titles_year", seen["The same query after an index on start_year"])
        self.assertIn("COVERING INDEX idx_titles_type_year (title_type=? AND start_year=?)",
                      seen["The same query after a two-column index"])
        self.assertIn("SCAN titles USING COVERING INDEX idx_titles_type_year",
                      seen["The second column alone, with the single-column index gone"])
        self.assertIn("SEARCH titles USING INDEX idx_titles_type_year ",
                      seen["Returning a column that is not in the index"])
        self.assertIn("COVERING INDEX idx_titles_type_year_title",
                      seen["The same query after a covering index"])
        self.assertTrue(seen["Two OR-connected conditions, one of them with no index"]
                        .startswith("SCAN titles"))
        self.assertIn("MULTI-INDEX OR", seen["Two OR-connected conditions, each with an index"])
        self.assertIn("USE TEMP B-TREE FOR ORDER BY",
                      seen["The most-voted titles, with no index on num_votes"])
        self.assertNotIn("TEMP B-TREE", seen["The same query after an index on num_votes"])
        self.assertNotIn("SEARCH", seen["The second column alone, before ANALYZE"])
        self.assertIn("ANY(title_type)", seen["The second column alone, after ANALYZE"])

    def test_a_query_gives_the_same_rows_with_and_without_an_index(self):
        sql = "select tconst from titles where primary_title = ? order by tconst"
        before = self.connection.execute(sql, ("Title 7",)).fetchall()
        self.connection.execute("create index idx_titles_primary_title on titles(primary_title)")
        self.assertEqual(self.connection.execute(sql, ("Title 7",)).fetchall(), before)
        self.assertGreater(len(before), 0)

    def test_dropping_our_indexes_leaves_the_primary_key_index(self):
        self.connection.execute("create index idx_titles_year on titles(start_year)")
        self.connection.execute("analyze")
        explore_indexes.drop_our_indexes(self.connection)
        self.assertEqual(self.one("select count(*) from sqlite_stat1"), 0)
        names = [row[0] for row in self.connection.execute(
            "select name from sqlite_master where type = 'index'")]
        self.assertNotIn("idx_titles_year", names)
        self.assertIn("sqlite_autoindex_titles_1", names)

    def test_python_and_sql_give_the_same_answers(self):
        for statement in compare_python_sql.INDEXES:
            self.connection.execute(statement)
        ids = [row[0] for row in self.connection.execute(
            "select tconst from ratings order by num_votes desc limit 50")]
        self.assertEqual(compare_python_sql.one_query_per_title(self.connection, ids),
                         compare_python_sql.one_join(self.connection, 50))
        self.assertEqual(compare_python_sql.movies_per_decade_in_python(self.connection),
                         compare_python_sql.movies_per_decade_in_sql(self.connection))


if __name__ == "__main__":
    unittest.main()
