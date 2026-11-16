"""Query helpers for the IMDb search page.

No Streamlit code lives here, so the functions can be tested on their own.
Connection settings come from the MONGODB_URI environment variable.
"""
import os

from pymongo import ASCENDING, MongoClient

TITLE_INDEX = "idx_titles_primary_title"


def connect(database_name="imdb"):
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError("Set MONGODB_URI before starting the page.")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client, client[database_name]


def build_filter(title="", title_type="", year=None):
    """Turn the search form into a MongoDB filter. Empty fields are ignored."""
    query = {}
    if title.strip():
        query["primary_title"] = title.strip()
    if title_type:
        query["title_type"] = title_type
    if year:
        query["start_year"] = int(year)
    return query


def stage_names(plan):
    """List the stage names in a winning plan, from the top down."""
    plan = plan.get("queryPlan", plan)
    names = []
    while plan:
        names.append(plan["stage"])
        plan = plan.get("inputStage")
    return names


def explain_summary(report):
    """Reduce an explain('executionStats') report to the numbers we talk about."""
    stats = report["executionStats"]
    return {
        "plan": " > ".join(stage_names(report["queryPlanner"]["winningPlan"])),
        "keys_examined": stats["totalKeysExamined"],
        "docs_examined": stats["totalDocsExamined"],
        "returned": stats["nReturned"],
        "millis": stats["executionTimeMillis"],
    }


def search(database, query, limit=20):
    """Return (rows, work). Each row joins a title with its rating by _id."""
    titles = database.titles
    rows = list(titles.find(query).limit(limit))
    work = explain_summary(titles.find(query).limit(limit).explain())
    ratings = {
        r["_id"]: r
        for r in database.ratings.find({"_id": {"$in": [row["_id"] for row in rows]}})
    }
    for row in rows:
        rating = ratings.get(row["_id"], {})
        row["average_rating"] = rating.get("average_rating")
        row["num_votes"] = rating.get("num_votes")
    return rows, work


def has_title_index(database):
    return any(i["name"] == TITLE_INDEX for i in database.titles.list_indexes())


def create_title_index(database):
    database.titles.create_index([("primary_title", ASCENDING)], name=TITLE_INDEX)


def drop_title_index(database):
    if has_title_index(database):
        database.titles.drop_index(TITLE_INDEX)
