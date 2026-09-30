"""Compare doing the work in Python with asking the database to do it.

Usage: python3 compare_python_sql.py [--database imdb.db]

Two comparisons on imdb.db. The first looks up 2,000 titles one query at a
time and then with one join. The second counts movies per decade, first by
fetching every year into Python and then with GROUP BY.

SQLite runs inside the Python process, so it hides the cost of sending rows
over a network. With a database server the differences would be larger.
"""
import argparse
from collections import Counter
import sqlite3
import time

INDEXES = [
    "create index if not exists idx_ratings_votes on ratings(num_votes)",
    "create index if not exists idx_titles_type_year on titles(title_type, start_year)",
]


def timed(function):
    started = time.perf_counter()
    result = function()
    return result, time.perf_counter() - started


def one_query_per_title(connection, ids):
    total = 0
    for tconst in ids:
        row = connection.execute(
            "select primary_title from titles where tconst = ?", (tconst,)).fetchone()
        total += len(row[0])
    return total


def one_join(connection, count):
    rows = connection.execute(
        "select t.primary_title from ratings r join titles t on t.tconst = r.tconst "
        "order by r.num_votes desc limit ?", (count,)).fetchall()
    return sum(len(row[0]) for row in rows)


def movies_per_decade_in_python(connection):
    counts = Counter()
    for (year,) in connection.execute(
            "select start_year from titles where title_type = 'movie' and start_year is not null"):
        counts[year // 10 * 10] += 1
    return dict(sorted(counts.items()))


def movies_per_decade_in_sql(connection):
    return dict(connection.execute(
        "select start_year / 10 * 10 as decade, count(*) from titles "
        "where title_type = 'movie' and start_year is not null "
        "group by decade order by decade"))


def main():
    parser = argparse.ArgumentParser(description="Compare Python and SQL.")
    parser.add_argument("--database", default="imdb.db")
    args = parser.parse_args()
    connection = sqlite3.connect(args.database)
    for statement in INDEXES:
        connection.execute(statement)
    connection.commit()

    count = 2000
    ids = [row[0] for row in connection.execute(
        "select tconst from ratings order by num_votes desc limit ?", (count,))]
    _, slow = timed(lambda: one_query_per_title(connection, ids))
    _, fast = timed(lambda: one_join(connection, count))
    print(f"Titles for the {count:,} most-voted ratings")
    print(f"  one query per title: {slow * 1000:8.1f} ms  ({count:,} queries)")
    print(f"  one join:            {fast * 1000:8.1f} ms  (1 query)")

    in_python, python_time = timed(lambda: movies_per_decade_in_python(connection))
    in_sql, sql_time = timed(lambda: movies_per_decade_in_sql(connection))
    print("\nMovies per decade")
    print(f"  fetch every year, count in Python: {python_time * 1000:8.1f} ms  ({sum(in_python.values()):,} rows fetched)")
    print(f"  GROUP BY in SQL:                   {sql_time * 1000:8.1f} ms  ({len(in_sql)} rows fetched)")
    print(f"  same answer: {in_python == in_sql}")
    for decade in list(in_sql)[-4:]:
        print(f"    {decade}s: {in_sql[decade]:,}")
    connection.close()


if __name__ == "__main__":
    main()
