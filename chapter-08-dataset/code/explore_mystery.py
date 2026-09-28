"""Explore an unfamiliar SQLite database with the dataset library.

Usage: python3 explore_mystery.py [database_file]

The file is opened read-only, so nothing here can change it.
"""
import csv
import sys

import dataset

path = sys.argv[1] if len(sys.argv) > 1 else "mystery.db"

# mode=ro refuses every write. sqlite_wal_mode=False stops dataset from
# switching the file to write-ahead logging when it connects.
db = dataset.connect(f"sqlite:///file:{path}?mode=ro&uri=true", sqlite_wal_mode=False)


def show(title, rows):
    print(f"\n== {title}")
    for row in rows:
        print(dict(row))


print("tables:", db.tables)
print("views:", db.views)

for name in db.tables + db.views:
    table = db[name]
    print(f"\n{name}: {len(table)} rows")
    print("  columns:", table.columns)

show("A few characters", db["character"].find(_limit=3, order_by="codepoint"))
show("Character categories, largest first", db.query(
    "select category.description, count(*) as characters "
    "from character join category on category.code = character.category "
    "group by category.code order by characters desc limit 5"))
show("Scripts with the most characters", db["script_summary"].find(order_by="-characters", _limit=5))
print("\n== The largest numeric values")
for row in db["numeric_character"].find(order_by="-numeric_value", _limit=3):
    print(row["codepoint"], row["name"], row["numeric_value"])
print("\n== Digits from other writing systems that mean 7")
for row in db["numeric_character"].find(numeric_value=7, _limit=5):
    print(row["name"])
show("Time zones with an offset that is not a whole hour", db.query(
    "select name, january_offset_minutes from timezone "
    "where january_offset_minutes % 60 != 0 order by january_offset_minutes limit 5"))
show("Time zones by whether they use daylight saving time", db.query(
    "select region, sum(uses_dst) as with_dst, count(*) as zones "
    "from timezone group by region order by zones desc limit 4"))

with open("scripts.csv", "w", newline="") as output:
    rows = list(db["script_summary"].find(order_by="-characters"))
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
print(f"\nWrote scripts.csv with {len(rows)} rows.")
