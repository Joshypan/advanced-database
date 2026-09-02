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

connection.execute("""
            create table pet
            (
                id integer primary key autoincrement,
                name text not null,
                kind text not null,
                age integer,
                food text,
                breed text not null
            );
            """)
connection.commit()

connection.execute(
    "insert into pet (name, kind, age, food, breed)  values (?, ?, ?, ?, ?)",
    ("Sultan", "dog", 11, "Bread", "German Sheppard"),
)
connection.execute(
    "insert into pet (name, kind, age, food, breed) values (?, ?, ?, ?, ?)",
    ("Goliath", "dog", 7, "Chow", "Golden Retriever"),
)
connection.execute(
    "insert into pet (name, kind, age, food, breed) values (?, ?, ?, ?, ?)",
    ("Snow White", "bunny", 2, "carrots", "White Bunny"),
)

connection.commit()

cursor = connection.execute("select * from pet")
rows = cursor.fetchall()
pprint(rows)

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