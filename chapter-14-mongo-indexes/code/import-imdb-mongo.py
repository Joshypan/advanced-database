"""Load IMDb title.basics and title.ratings into MongoDB Atlas, in chunks.

Usage:
    python3 import-imdb-mongo.py [--data-dir data] [--database imdb] [--replace]

Reads the same two compressed files the Chapter 9 loader uses
(title.basics.tsv.gz and title.ratings.tsv.gz), one row at a time, so memory
use stays small. Documents go to Atlas in batches of 10,000 with insert_many.

Collections: titles and ratings. The IMDb identifier (tconst, such as
tt0000001) is stored as the document's _id, so MongoDB's automatic _id index
plays the role of the SQLite primary key. No other indexes are created here.
Building them is the exercise in Chapter 14.

Set MONGODB_URI first, the same way as for the pets application.
The IMDb files are for personal, non-commercial use. Do not redistribute them
or commit them to a public repository.
"""
import argparse
import csv
import gzip
from itertools import islice
import os
from pathlib import Path
import time

from pymongo import MongoClient
from pymongo.server_api import ServerApi

BATCH_SIZE = 10_000

# (file name, collection, [(field, kind), ...]). The first field becomes _id.
FILES = [
    (
        "title.basics.tsv.gz",
        "titles",
        [
            ("_id", "text"),
            ("title_type", "text"),
            ("primary_title", "text"),
            ("original_title", "text"),
            ("is_adult", "int"),
            ("start_year", "int"),
            ("end_year", "int"),
            ("runtime_minutes", "int"),
            ("genres", "text"),
        ],
    ),
    (
        "title.ratings.tsv.gz",
        "ratings",
        [("_id", "text"), ("average_rating", "real"), ("num_votes", "int")],
    ),
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


def documents(path, fields):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(reader)  # header line
        for record in reader:
            yield {
                name: convert(value, kind)
                for (name, kind), value in zip(fields, record)
            }


def load(collection, path, fields, limit=None):
    source = documents(path, fields)
    if limit is not None:
        source = islice(source, limit)
    total = 0
    while True:
        batch = list(islice(source, BATCH_SIZE))
        if not batch:
            break
        collection.insert_many(batch, ordered=False)
        before = total
        total += len(batch)
        if total // 500_000 > before // 500_000:
            print(f"  {collection.name}: {total:,} documents", flush=True)
    print(f"  {collection.name}: {total:,} documents in total")
    return total


def connect():
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise SystemExit("Set MONGODB_URI before running this script.")
    client = MongoClient(uri, server_api=ServerApi("1"), serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    return client


def import_all(data_dir, database_name, replace, limit=None):
    if limit is not None and limit < 1:
        raise SystemExit("--limit must be positive.")
    for filename, _, _ in FILES:
        if not (Path(data_dir) / filename).is_file():
            raise SystemExit(f"Missing input: {Path(data_dir) / filename}")
    client = connect()
    try:
        database = client[database_name]
        existing = set(database.list_collection_names())
        for _, collection_name, _ in FILES:
            if collection_name in existing:
                if not replace:
                    raise SystemExit(
                        f"{database_name}.{collection_name} already exists. "
                        "Use --replace to rebuild it."
                    )
                database.drop_collection(collection_name)
        for filename, collection_name, fields in FILES:
            started = time.perf_counter()
            print(f"Loading {filename}")
            load(database[collection_name], Path(data_dir) / filename, fields, limit)
            print(f"  {time.perf_counter() - started:.1f} seconds")
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load IMDb files into MongoDB Atlas.")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--database", default="imdb")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="drop the titles and ratings collections first if they exist",
    )
    parser.add_argument("--limit", type=int, help="maximum documents per collection")
    args = parser.parse_args()
    import_all(args.data_dir, args.database, args.replace, args.limit)
