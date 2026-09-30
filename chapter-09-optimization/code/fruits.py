"""The small FruitsForSale table from the SQLite query planner document.

Usage: python3 fruits.py

Builds the seven-row table in memory, adds the indexes one at a time, and prints
the plan SQLite chooses for each query. The chapter's figures show the same
steps. With seven rows the times mean nothing, but the plans are the ones a
large table would get.
"""
import sqlite3

ROWS = [
    (1, "Orange", "FL", 0.85),
    (2, "Apple", "NC", 0.45),
    (4, "Peach", "SC", 0.60),
    (5, "Grape", "CA", 0.80),
    (18, "Lemon", "FL", 1.25),
    (19, "Strawberry", "NC", 2.45),
    (23, "Orange", "CA", 1.05),
]

PEACH = "select price from fruitsforsale where fruit = 'Peach'"
ORANGE = "select price from fruitsforsale where fruit = 'Orange'"
CA_ORANGE = "select price from fruitsforsale where fruit = 'Orange' and state = 'CA'"
EITHER = "select price from fruitsforsale where fruit = 'Orange' or state = 'CA'"
ROWID = "select price from fruitsforsale where rowid = 4"
SORTED = "select * from fruitsforsale order by fruit"
ORANGES_BY_STATE = "select price from fruitsforsale where fruit = 'Orange' order by state"
PARTIAL = "select * from fruitsforsale order by fruit, price"

# (heading, index to create first or None, queries to plan)
STEPS = [
    ("No indexes", None, [PEACH, ROWID, SORTED]),
    ("Idx1 on fruit", "create index Idx1 on fruitsforsale(fruit)", [PEACH, ORANGE, SORTED]),
    ("Idx2 on state", "create index Idx2 on fruitsforsale(state)", [CA_ORANGE]),
    ("Idx3 on fruit, state", "create index Idx3 on fruitsforsale(fruit, state)",
     [CA_ORANGE, PEACH, ORANGES_BY_STATE]),
    ("Idx4 on fruit, state, price (a covering index)",
     "create index Idx4 on fruitsforsale(fruit, state, price)",
     [CA_ORANGE, SORTED, PARTIAL]),
]


def plan(connection, sql):
    return [row[3] for row in connection.execute("explain query plan " + sql)]


def build():
    connection = sqlite3.connect(":memory:")
    connection.execute("create table fruitsforsale (fruit text, state text, price real)")
    connection.executemany(
        "insert into fruitsforsale (rowid, fruit, state, price) values (?, ?, ?, ?)", ROWS)
    return connection


def main():
    connection = build()
    for heading, index, queries in STEPS:
        print(f"== {heading}")
        if index:
            connection.execute(index)
        for sql in queries:
            print(f"   {sql}")
            for line in plan(connection, sql):
                print(f"      {line}")
    connection.close()


if __name__ == "__main__":
    main()
