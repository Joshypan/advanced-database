"""Time IMDb queries in Atlas before and after building indexes.

Usage:
    python3 explore-imdb-indexes.py [--database imdb]

Run import-imdb-mongo.py first. For each experiment this script prints the
query, the plan stage MongoDB chose (COLLSCAN or IXSCAN), how many documents
MongoDB examined, how many it returned, and the best of three timings. Then it
builds the index for that experiment, prints how long the build took, and
measures the same query again.

It creates only indexes whose names start with idx_, and it drops those at the
start, so you can run it again. It never changes the data.

Your numbers will not match anyone else's. They depend on your cluster tier,
your network, and whether Atlas already has the data in memory. Record your
own results in the table in the chapter exercise.
"""
import argparse
import os
import time

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.server_api import ServerApi

# Each experiment: (heading, collection, filter, sort, index keys, index name).
# sort is None when the query has no ordering.
EXPERIMENTS = [
    (
        "One title, one field",
        "titles",
        {"primary_title": "The Godfather"},
        None,
        [("primary_title", ASCENDING)],
        "idx_titles_primary_title",
    ),
    (
        "Two conditions",
        "titles",
        {"title_type": "movie", "start_year": 1994},
        None,
        [("title_type", ASCENDING), ("start_year", ASCENDING)],
        "idx_titles_type_year",
    ),
    (
        "Top ten by votes",
        "ratings",
        {},
        [("num_votes", DESCENDING)],
        [("num_votes", DESCENDING)],
        "idx_ratings_num_votes",
    ),
]


def connect(database_name):
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise SystemExit("Set MONGODB_URI before running this script.")
    client = MongoClient(uri, server_api=ServerApi("1"), serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    return client, client[database_name]


def stages(plan):
    """Collect every stage name in a winning plan, from the top down."""
    found = []
    while plan:
        found.append(plan["stage"])
        plan = plan.get("inputStage")
    return found


def explain(collection, query, sort):
    cursor = collection.find(query)
    if sort:
        cursor = cursor.sort(sort)
    if sort:
        cursor = cursor.limit(10)
    report = cursor.explain()
    winning = report["queryPlanner"]["winningPlan"]
    executed = report["executionStats"]
    return (
        " > ".join(stages(winning)),
        executed["totalDocsExamined"],
        executed["nReturned"],
    )


def best_of_three(collection, query, sort):
    best = None
    for _ in range(3):
        cursor = collection.find(query)
        if sort:
            cursor = cursor.sort(sort).limit(10)
        started = time.perf_counter()
        list(cursor)
        elapsed = (time.perf_counter() - started) * 1000
        best = elapsed if best is None else min(best, elapsed)
    return best


def drop_experiment_indexes(database):
    for name in ("titles", "ratings"):
        collection = database[name]
        for index in collection.list_indexes():
            if index["name"].startswith("idx_"):
                collection.drop_index(index["name"])


def measure(label, collection, query, sort):
    plan, examined, returned = explain(collection, query, sort)
    milliseconds = best_of_three(collection, query, sort)
    print(f"  {label}")
    print(f"    plan: {plan}")
    print(f"    documents examined: {examined:,}   returned: {returned:,}")
    print(f"    best of three: {milliseconds:,.1f} ms")


def run(database_name):
    client, database = connect(database_name)
    try:
        drop_experiment_indexes(database)
        for heading, name, query, sort, keys, index_name in EXPERIMENTS:
            collection = database[name]
            print(f"\n{heading}: {name}.find({query})" + (f" sorted by {sort}" if sort else ""))
            measure("before the index", collection, query, sort)
            started = time.perf_counter()
            collection.create_index(keys, name=index_name)
            print(f"  built {index_name} in {time.perf_counter() - started:.1f} seconds")
            measure("after the index", collection, query, sort)
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Time IMDb queries before and after indexes.")
    parser.add_argument("--database", default="imdb")
    args = parser.parse_args()
    run(args.database)
