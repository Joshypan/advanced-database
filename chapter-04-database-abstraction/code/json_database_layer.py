"""Pet database operations using one JSON file per record.

Change app.py to: import json_database_layer as database
The existing setup_database("pets.db") call selects pets_json, leaving SQLite alone.
An explicit folder is also accepted: setup_database("practice_records").
"""
from pathlib import Path
from jsonbase import JsonBase

store = None


def initialize(database_file):
    global store
    folder = Path(database_file)
    if folder.suffix == ".db":
        folder = folder.with_name(folder.stem + "_json")
    store = JsonBase(folder)


def setup_database(database_file):
    initialize(database_file)


def get_pets():
    return store.get_all()


def get_pet(id):
    return store.get(id)


def pet_record(data):
    try:
        age = int(data["age"])
    except (KeyError, TypeError, ValueError):
        age = 0
    return {"name": data["name"], "age": age, "type": data["type"],
            "food": data["food"], "owner": data["owner"]}


def create_pet(data):
    store.create(pet_record(data))


def update_pet(id, data):
    store.update(id, pet_record(data))


def delete_pet(id):
    store.delete(id)
