"""Shared storage location and starting documents for the Mongita lesson.

Mongita API and original mongoose example:
https://github.com/scottrogowski/mongita
"""
from pathlib import Path
from mongita import MongitaClientDisk

DATA_DIR = Path(__file__).resolve().parent / "data" / "mongita"


def connect(data_dir=DATA_DIR):
    """Return the client and collection; use a supplied folder in tests."""
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    client = MongitaClientDisk(host=str(data_dir))
    collection = client.hello_world_db.mongoose_collection
    return client, collection


def seed(collection, reset=False):
    """Seed an empty collection, or explicitly reset this lesson collection."""
    if reset:
        collection.delete_many({})
    if collection.count_documents({}) == 0:
        # New dictionaries each time: insertion adds an _id to each document.
        collection.insert_many([
            {"name": "Meercat", "does_not_eat": "Snakes"},
            {"name": "Yellow mongoose", "eats": "Termites"},
        ])
