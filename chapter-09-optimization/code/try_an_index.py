"""Time one query before and after adding an index, by hand.

Usage: python3 try_an_index.py [--database imdb.db]

A small, readable version of the first step in explore_indexes.py: look up a
title by primary_title, add an index on that column, and look it up again.
Prints the plan and the time for both, and checks that the index did not
change the answer. Leaves idx_titles_primary_title in place afterward.
"""
import argparse
from time import perf_counter
import sqlite3

QUERY = "select tconst, start_year from titles where primary_title = ?"
PARAMETERS = ("The Godfather",)


def plan(connection, sql, parameters=()):
    for row in connection.execute("explain query plan " + sql, parameters):
        print(row[3])


def timed(connection, sql, parameters=()):
    started = perf_counter()
    rows = connection.execute(sql, parameters).fetchall()
    return rows, (perf_counter() - started) * 1000


def main(database):
    connection = sqlite3.connect(f"file:{database}?mode=rw", uri=True)
    connection.execute("drop index if exists idx_titles_primary_title")

    plan(connection, QUERY, PARAMETERS)
    before, before_ms = timed(connection, QUERY, PARAMETERS)
    print("Before:", before_ms, "ms")

    connection.execute("create index idx_titles_primary_title on titles(primary_title)")
    connection.commit()

    plan(connection, QUERY, PARAMETERS)
    after, after_ms = timed(connection, QUERY, PARAMETERS)
    print("After:", after_ms, "ms")

    print("Same rows:", sorted(before) == sorted(after))
    connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Time a query before and after an index.")
    parser.add_argument("--database", default="imdb.db")
    args = parser.parse_args()
    main(args.database)
