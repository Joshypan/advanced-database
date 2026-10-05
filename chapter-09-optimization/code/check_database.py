"""Confirm that imdb.db built correctly, read-only.

Usage: python3 check_database.py [--database imdb.db]

Opens the database with mode=ro, so this never creates or changes a file.
Prints the table list, a row count for each table, and one joined row, so you
can compare the counts against what import_imdb.py reported.
"""
import argparse
from pathlib import Path
import sqlite3


def check(database):
    print(Path(database).resolve())
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    print(connection.execute(
        "select name from sqlite_master where type = 'table' order by name"
    ).fetchall())
    for table in ("titles", "ratings"):
        count = connection.execute(f"select count(*) from {table}").fetchone()[0]
        print(table, count)

    print(connection.execute("""
        select t.tconst, t.primary_title, t.start_year,
               r.average_rating, r.num_votes
        from titles t left join ratings r on r.tconst = t.tconst
        where t.tconst = ?
    """, ("tt0000001",)).fetchone())
    connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check that imdb.db built correctly.")
    parser.add_argument("--database", default="imdb.db")
    args = parser.parse_args()
    check(args.database)
