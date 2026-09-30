"""Watch the query planner and the clock as indexes are added to imdb.db.

Usage: python3 explore_indexes.py [--database imdb.db]

Each step shows a query, the plan SQLite chose (EXPLAIN QUERY PLAN), and the
best of three run times. Steps that add an index show the time to build it and
the growth of the file. The last two steps show what ANALYZE changes. The script removes every index it creates (names that
start with idx_) and any statistics from ANALYZE before it starts, so it can be
run again.
"""
import argparse
import sqlite3
import time

TITLE = "The Godfather"

# (heading, sql, parameters, index to create first or None)
STEPS = [
    ("Lookup by the primary key (tconst)",
     "select primary_title, start_year from titles where tconst = ?",
     ("tt0068646",), None),
    ("Lookup by a column with no index",
     "select tconst, start_year from titles where primary_title = ?",
     (TITLE,), None),
    ("The same query after an index on primary_title",
     "select tconst, start_year from titles where primary_title = ?",
     (TITLE,), "create index idx_titles_primary_title on titles(primary_title)"),
    ("LIKE with a prefix, against a case-sensitive index",
     "select tconst, primary_title from titles where primary_title like ?",
     ("The Godfather%",), None),
    ("The same LIKE after an index that ignores case",
     "select tconst, primary_title from titles where primary_title like ?",
     ("The Godfather%",),
     "create index idx_titles_primary_title_nocase on titles(primary_title collate nocase)"),
    ("LIKE with a wildcard at the front",
     "select tconst, primary_title from titles where primary_title like ?",
     ("%Godfather%",), None),
    ("Two conditions, no index that covers both",
     "select count(*) from titles where title_type = ? and start_year = ?",
     ("movie", 1994), None),
    ("The same query after an index on start_year",
     "select count(*) from titles where title_type = ? and start_year = ?",
     ("movie", 1994), "create index idx_titles_year on titles(start_year)"),
    ("The same query after a two-column index",
     "select count(*) from titles where title_type = ? and start_year = ?",
     ("movie", 1994),
     "create index idx_titles_type_year on titles(title_type, start_year)"),
    ("The second column alone, with the single-column index gone",
     "select count(*) from titles where start_year = ?",
     (1994,), "drop index idx_titles_year"),
    ("The first column alone",
     "select count(*) from titles where title_type = ?",
     ("movie",), None),
    ("Returning a column that is not in the index",
     "select primary_title from titles where title_type = ? and start_year = ?",
     ("movie", 1994), None),
    ("The same query after a covering index",
     "select primary_title from titles where title_type = ? and start_year = ?",
     ("movie", 1994),
     "create index idx_titles_type_year_title on titles(title_type, start_year, primary_title)"),
    ("Two OR-connected conditions, one of them with no index",
     "select tconst from titles where start_year = ? or primary_title = ?",
     (1894, TITLE), None),
    ("Two OR-connected conditions, each with an index",
     "select tconst from titles where start_year = ? or primary_title = ?",
     (1894, TITLE), "create index idx_titles_year on titles(start_year)"),
    ("The most-voted titles, with no index on num_votes",
     "select tconst, num_votes from ratings order by num_votes desc limit 10",
     (), None),
    ("The same query after an index on num_votes",
     "select tconst, num_votes from ratings order by num_votes desc limit 10",
     (), "create index idx_ratings_votes on ratings(num_votes)"),
    ("A join on the primary keys",
     "select t.primary_title, r.num_votes from ratings r "
     "join titles t on t.tconst = r.tconst "
     "order by r.num_votes desc limit 10",
     (), None),
    ("The second column alone, before ANALYZE",
     "select count(*) from titles where start_year = ?",
     (1994,), "drop index idx_titles_year"),
    ("The second column alone, after ANALYZE",
     "select count(*) from titles where start_year = ?",
     (1994,), "analyze"),
]


def drop_our_indexes(connection):
    names = connection.execute(
        "select name from sqlite_master where type = 'index' and name like 'idx_%'"
    ).fetchall()
    for (name,) in names:
        connection.execute(f"drop index {name}")
    has_statistics = connection.execute(
        "select count(*) from sqlite_master where name = 'sqlite_stat1'").fetchone()[0]
    if has_statistics:
        connection.execute("delete from sqlite_stat1")
    connection.commit()


def plan(connection, sql, parameters):
    rows = connection.execute("explain query plan " + sql, parameters).fetchall()
    return [row[3] for row in rows]


def best_time(connection, sql, parameters, repeats=3):
    best = None
    for _ in range(repeats):
        started = time.perf_counter()
        connection.execute(sql, parameters).fetchall()
        elapsed = time.perf_counter() - started
        best = elapsed if best is None else min(best, elapsed)
    return best


def size_mb(connection):
    """Megabytes of the file in use. Pages freed by DROP INDEX do not count."""
    page_size = connection.execute("pragma page_size").fetchone()[0]
    pages = connection.execute("pragma page_count").fetchone()[0]
    free = connection.execute("pragma freelist_count").fetchone()[0]
    return (pages - free) * page_size / 1_000_000


def write_cost(rows=500_000):
    """Time the same inserts into a scratch table with 0, 1, and 3 indexes."""
    print("\n== What indexes cost when writing")
    for count in (0, 1, 3):
        connection = sqlite3.connect(":memory:")
        connection.execute("create table scratch (a integer, b integer, c text)")
        for name in ("a", "b", "c")[:count]:
            connection.execute(f"create index idx_scratch_{name} on scratch({name})")
        data = [(i, (i * 7919) % 10007, f"name{(i * 31) % 50021}") for i in range(rows)]
        started = time.perf_counter()
        connection.executemany("insert into scratch values (?, ?, ?)", data)
        connection.commit()
        print(f"   {rows:,} inserts with {count} index(es): {time.perf_counter() - started:.2f} seconds")
        connection.close()


def main():
    parser = argparse.ArgumentParser(description="Explore indexes on imdb.db.")
    parser.add_argument("--database", default="imdb.db")
    args = parser.parse_args()

    connection = sqlite3.connect(args.database)
    drop_our_indexes(connection)
    connection.close()
    connection = sqlite3.connect(args.database)
    print(f"SQLite version {sqlite3.sqlite_version}")
    print(f"Database size with no extra indexes: {size_mb(connection):,.0f} MB")

    for heading, sql, parameters, create in STEPS:
        print(f"\n== {heading}")
        if create:
            print(f"   {create}", flush=True)
            before = size_mb(connection)
            started = time.perf_counter()
            connection.execute(create)
            connection.commit()
            elapsed = time.perf_counter() - started
            grew = size_mb(connection) - before
            if create.startswith("create"):
                print(f"   built in {elapsed:.1f} seconds; the database grew by {grew:,.0f} MB")
            elif create == "analyze":
                print(f"   analyzed in {elapsed:.1f} seconds")
        print(f"   {' '.join(sql.split())}")
        for line in plan(connection, sql, parameters):
            print(f"   plan: {line}")
        print(f"   time: {best_time(connection, sql, parameters) * 1000:,.1f} ms")
    connection.close()
    write_cost()


if __name__ == "__main__":
    main()
