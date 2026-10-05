"""Run the mongoose session with visible output.

Run with --reset to replace the lesson collection before the demonstration.
The original interactive transcripts remain in session.txt and mongita-example.txt.
"""
import argparse
from pprint import pprint
from bson.objectid import ObjectId
from lesson import connect, seed


def demonstrate(collection):
    print("Starting documents:", collection.count_documents({}))
    pprint(list(collection.find({})))

    # The filter selects a document; $set adds or changes just this field.
    result = collection.update_one({"name": "Meercat"}, {"$set": {"weight": 2}})
    print("Matched:", result.matched_count, "Modified:", result.modified_count)
    cursor = collection.find({"weight": {"$gt": 1}})
    mongooses = list(cursor)
    print("First pass:", len(mongooses))
    print("Second pass through cursor:", list(cursor))
    print("Saved list still has:", len(mongooses))

    # A single result is a dictionary, and its identifier is an ObjectId.
    yellow = collection.find_one({"eats": "Termites"})
    identifier = str(yellow["_id"])
    print("String identifier:", identifier)
    pprint(collection.find_one({"_id": ObjectId(identifier)}))
    print("Missing single result:", collection.find_one({"weight": {"$gt": 300}}))
    print("Missing multiple results:", list(collection.find({"weight": {"$gt": 300}})))

    old = collection.find_one({"name": "Meercat"})
    result = collection.delete_one({"_id": old["_id"]})
    print("Deleted:", result.deleted_count)
    inserted = collection.insert_one({"name": "Meercat", "does_not_eat": "Snakes"})
    print("New identifier:", inserted.inserted_id != old["_id"])
    print("Weight query after reinsertion:", list(collection.find({"weight": {"$gt": 1}})))
    print("Final documents:")
    pprint(list(collection.find({})))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true",
                        help="delete the lesson documents and run from the beginning")
    args = parser.parse_args()
    if not args.reset:
        parser.error("pass --reset to replace the lesson collection and run the demonstration")
    client, collection = connect()
    try:
        seed(collection, reset=True)
        demonstrate(collection)
    finally:
        client.close()


if __name__ == "__main__":
    main()
