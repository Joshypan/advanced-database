import argparse
import sqlite3
from pprint import pprint

ap = argparse.ArgumentParser()
ap.add_argument("--db", default="pets.db")
args = ap.parse_args()

connection = sqlite3.connect(args.db)

print("succeeded in making connection.")

connection.execute("drop table if exists pet")
connection.commit()

# list all the tables in the database
cursor = connection.execute(
    """
    select name from sqlite_master
    where type = 'table'
    order by name
    """
)
list_of_tables = [item[0] for item in cursor.fetchall()]
print("the tables:")
pprint(list_of_tables)

connection.execute("""
            create table pet
            (
                id integer primary key autoincrement,
                name text not null,
                kind text not null,
                age integer,
                food text
            );
            """)
connection.commit()

# list all the tables in the database
cursor = connection.execute(
    """
    select name from sqlite_master
    where type = 'table'
    order by name
    """
)
list_of_tables = [item[0] for item in cursor.fetchall()]
print("the tables:")
pprint(list_of_tables)

connection.execute(
    "insert into pet (name, kind, age, food) values (?, ?, ?, ?)",
    ("Dorothy", "dog", 11, "peanut butter"),
)
connection.execute(
    "insert into pet (name, kind, age, food) values (?, ?, ?, ?)",
    ("Whiskers", "hamster", 1, "hamster chow"),
)

connection.commit()

cursor = connection.execute("select sql from sqlite_master where type='table' and name=?",
    ("pet",))
row = cursor.fetchone()
pprint(row[0] if row else "")

cursor = connection.execute("select * from pet")
row = cursor.fetchone()
pprint(row)

cursor = connection.execute("select * from pet")
rows = cursor.fetchall()
pprint(rows)

print("try with a wrong name")
for i in [1,2]:
    try:
        connection.execute("insert into petz (name, kind, age, food) values (?, ?, ?, ?)",("Sandy","cat",9,"tuna"))
    except sqlite3.Error as e:
        print("Caught sqlite error:", e)

print("try with the correct name")
for i in [1,2]:
    try:
        connection.execute("insert into pet (name, kind, age, food) values (?, ?, ?, ?)",("Sandy","cat",9,"tuna"))
        connection.commit()
        print("insert succeeded")
        break
    except sqlite3.Error as e:
        print("Caught sqlite error:", e)

connection.execute(
    "insert into pet (name, kind, age, food) values (?, ?, ?, ?)",
    ("Maxwell", "cat", 11, "tuna"),
)
connection.execute(
    "insert into pet (name, kind, age, food) values (?, ?, ?, ?)",
    ("Stash", "mouse", 1, "cheese"),
)

connection.commit()

connection.execute(
    "delete from pet where name=?",("Stash",)
    )
connection.commit()
print("deletion complete")

connection.execute(
    "update pet set age=12, food='pretzels' where name=?",("Dorothy",)
    )
connection.commit()
print("update complete")



print("done.")