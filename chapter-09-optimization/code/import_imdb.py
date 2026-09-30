"""Load IMDb title.basics and title.ratings into SQLite, in chunks.

Usage: python3 import_imdb.py [--data-dir data] [--database imdb.db] [--replace]

Reads the compressed files (title.basics.tsv.gz, title.ratings.tsv.gz) directly,
one row at a time, so memory use stays small however large the files are.
Rows go to the database in chunks of 50,000. The tables are created from
schema.sql with no secondary indexes, so the load does not have to maintain
them row by row. (The primary keys are indexed automatically.) The
chapter adds the indexes afterward.
"""
import argparse
import csv
import gzip
from itertools import islice
import os
from pathlib import Path
import sqlite3
import time

HERE = Path(__file__).resolve().parent
CHUNK_SIZE = 50_000

FILES = [
    ("title.basics.tsv.gz", "titles",
     ["text", "text", "text", "text", "int", "int", "int", "int", "text"]),
    ("title.ratings.tsv.gz", "ratings", ["text", "real", "int"]),
]


def convert(value, kind):
    """IMDb writes a missing value as \\N. Convert it to None, and numbers to numbers."""
    if value == "\\N":
        return None
    if kind == "int":
        return int(value)
    if kind == "real":
        return float(value)
    return value


def rows(path, kinds):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(reader)
        for record in reader:
            yield tuple(convert(value, kind) for value, kind in zip(record, kinds))


def load(connection, path, table, kinds):
    marks = ", ".join("?" for _ in kinds)
    statement = f"insert into {table} values ({marks})"
    source = rows(path, kinds)
    total = 0
    while True:
        chunk = list(islice(source, CHUNK_SIZE))
        if not chunk:
            break
        connection.executemany(statement, chunk)
        connection.commit()
        before = total
        total += len(chunk)
        if total // 1_000_000 > before // 1_000_000:
            print(f"  {table}: {total:,} rows", flush=True)
    print(f"  {table}: {total:,} rows in total")
    return total


def import_all(data_dir, database):
    connection = sqlite3.connect(database)
    try:
        connection.executescript((HERE / "schema.sql").read_text())
        for filename, table, kinds in FILES:
            started = time.perf_counter()
            print(f"Loading {filename}")
            load(connection, Path(data_dir) / filename, table, kinds)
            print(f"  {time.perf_counter() - started:.1f} seconds")
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load IMDb files into SQLite.")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--database", default="imdb.db")
    parser.add_argument("--replace", action="store_true",
                        help="replace the database file if it already exists")
    args = parser.parse_args()
    if Path(args.database).exists():
        if not args.replace:
            raise SystemExit(f"{args.database} already exists. Use --replace to rebuild it.")
        os.remove(args.database)
    import_all(args.data_dir, args.database)
