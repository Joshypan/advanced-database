"""Show the indexes and query plans for the Pets application's lookups.

Run this against Atlas after setting MONGODB_URI. It never inserts, updates,
or deletes anything. It prints, for each query, whether MongoDB used an index
(IXSCAN) or read the whole collection (COLLSCAN), and how many documents it
examined to return how many.

Explain output is a nested document whose exact layout can differ between
MongoDB server versions, so this script searches for the stage names instead
of relying on one fixed path.
"""
from bson.objectid import ObjectId

import database


def find_stages(plan, found=None):
    """Collect every 'stage' name found anywhere inside an explain plan."""
    if found is None:
        found = []
    if isinstance(plan, dict):
        if "stage" in plan:
            found.append(plan["stage"])
        for value in plan.values():
            find_stages(value, found)
    elif isinstance(plan, list):
        for item in plan:
            find_stages(item, found)
    return found


def explain(collection, query):
    return collection.find(query).explain()


def describe(label, collection, query):
    result = explain(collection, query)
    stages = find_stages(result.get("queryPlanner", {}).get("winningPlan", {}))
    stats = result.get("executionStats", {})
    print(label)
    print("  query:", query)
    print("  plan stages:", " -> ".join(stages) or "(none found)")
    if "COLLSCAN" in stages:
        print("  result: reads the whole collection")
    elif any("IXSCAN" in stage for stage in stages):
        print("  result: uses an index")
    if stats:
        print("  documents examined:", stats.get("totalDocsExamined"))
        print("  keys examined:", stats.get("totalKeysExamined"))
        print("  documents returned:", stats.get("nReturned"))
    print()


def main():
    try:
        database.setup_database("pets")
        for collection in (database.owners_collection, database.pets_collection):
            print(f"Indexes on {collection.name}:")
            for name, info in collection.index_information().items():
                print("  ", name, info.get("key"))
            print()

        sample_owner = database.owners_collection.find_one()
        owner_id = sample_owner["_id"] if sample_owner else ObjectId()
        sample_pet = database.pets_collection.find_one()
        pet_name = sample_pet["name"] if sample_pet else "Casey"
        pet_type = sample_pet["type"] if sample_pet else "dog"
        owner_name = sample_owner["name"] if sample_owner else "Alex"

        describe("Pet lookup by identifier (automatic _id index)",
                 database.pets_collection, {"_id": sample_pet["_id"] if sample_pet else ObjectId()})
        describe("Does this owner still have pets? (used when deleting an owner)",
                 database.pets_collection, {"owner_id": owner_id})
        describe("Pets by name", database.pets_collection, {"name": pet_name})
        describe("Pets by type", database.pets_collection, {"type": pet_type})
        describe("Owners by name", database.owners_collection, {"name": owner_name})
        describe("Pets by age (no index on age)",
                 database.pets_collection, {"age": {"$gte": 0}})
    finally:
        database.close_connection()


if __name__ == "__main__":
    main()
