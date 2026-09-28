"""Pet operations implemented with Peewee, returning ordinary dictionaries.

Peewee, Charles Leifer: models, queries, and writes.
https://docs.peewee-orm.com/en/latest/peewee/models.html
https://docs.peewee-orm.com/en/latest/peewee/querying.html
https://docs.peewee-orm.com/en/latest/peewee/writing.html
"""
import os

from peewee import IntegerField, Model, SqliteDatabase, TextField
from playhouse.migrate import SqliteMigrator, migrate

# Bind the file later so the app and tests can use different databases.
# https://docs.peewee-orm.com/en/latest/peewee/database.html
db = SqliteDatabase(None)


class BaseModel(Model):
    # Meta configures the model; it does not declare stored fields.
    class Meta:
        database = db


class Pet(BaseModel):
    # Class attributes describe columns. Peewee supplies an integer id field.
    name = TextField(null=False)
    type = TextField(null=False)
    age = IntegerField(default=0)
    food = TextField(null=True)


def initialize(database_file):
    close_connection()
    db.init(database_file)
    db.connect(reuse_if_open=True)
    db.create_tables([Pet])

    # Preserve rows in the original example when adding the food field.
    # create_tables() creates missing tables; it does not alter existing ones.
    # https://docs.peewee-orm.com/en/latest/peewee/db_tools.html#schema-migrations
    columns = {column.name for column in db.get_columns("pet")}
    if "food" not in columns:
        migrate(SqliteMigrator(db).add_column("pet", "food", TextField(null=True)))


def close_connection():
    if not db.is_closed():
        db.close()


def _normalize_age(value):
    # Keep the example's conversion rule for values received from a form.
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _pet_values(data):
    name = (data.get("name") or "").strip()
    pet_type = (data.get("type") or "").strip()
    if not name:
        raise ValueError("Pet name is required.")
    if not pet_type:
        raise ValueError("Pet type is required.")
    return {
        "name": name,
        "type": pet_type,
        "age": _normalize_age(data.get("age")),
        "food": data.get("food", ""),
    }


def pet_to_dict(pet):
    # Keep model objects inside this layer. Routes and templates use dictionaries.
    return {
        "id": pet.id, "name": pet.name, "type": pet.type,
        "age": pet.age, "food": pet.food,
    }


def get_pets():
    # select() builds a query. Iteration retrieves rows as Pet objects.
    query = Pet.select().order_by(Pet.name, Pet.id)
    return [pet_to_dict(pet) for pet in query]


def get_pet(id):
    # This comparison builds a SQL condition, not an ordinary Python Boolean.
    pet = Pet.get_or_none(Pet.id == int(id))
    if pet is None:
        return None
    return pet_to_dict(pet)


def create_pet(data):
    # create() inserts immediately and returns the saved model instance.
    pet = Pet.create(**_pet_values(data))
    return pet.id


def delete_pet(id):
    # where() selects the record. execute() runs the DELETE statement.
    Pet.delete().where(Pet.id == int(id)).execute()


def update_pet(id, data):
    # update() builds the statement; execute() sends it to SQLite.
    Pet.update(**_pet_values(data)).where(Pet.id == int(id)).execute()


def setup_test_database(db_file="test_pets.db"):
    close_connection()
    try:
        os.remove(db_file)
    except FileNotFoundError:
        pass

    initialize(db_file)

    pets = [
        {"name": "dorothy", "type": "dog", "age": 9, "food": "kibble"},
        {"name": "suzy", "type": "mouse", "age": 9},
        {"name": "casey", "type": "dog", "age": 9},
        {"name": "heidi", "type": "cat", "age": 15},
    ]
    for pet in pets:
        create_pet(pet)

    assert len(get_pets()) == 4


def test_get_pets():
    pets = get_pets()
    assert type(pets) is list
    assert len(pets) >= 1
    assert type(pets[0]) is dict
    for key in ["id", "name", "type", "age", "food"]:
        assert key in pets[0]
    assert type(pets[0]["name"]) is str


def test_create_pet_and_get_pet():
    new_id = create_pet({"name": "walter", "age": "2", "type": "mouse", "food": "seeds"})
    pet = get_pet(new_id)
    assert pet is not None
    assert pet["name"] == "walter"
    assert pet["age"] == 2
    assert pet["type"] == "mouse"
    assert pet["food"] == "seeds"


def test_update_pet():
    new_id = create_pet({"name": "temp", "age": 1, "type": "cat"})
    update_pet(new_id, {"name": "updated", "age": "8", "type": "dog", "food": "kibble"})
    pet = get_pet(new_id)
    assert pet is not None
    assert pet["name"] == "updated"
    assert pet["age"] == 8
    assert pet["type"] == "dog"
    assert pet["food"] == "kibble"


def test_delete_pet():
    new_id = create_pet({"name": "delete_me", "age": 3, "type": "fish"})
    delete_pet(new_id)
    assert get_pet(new_id) is None


if __name__ == "__main__":
    setup_test_database()
    test_get_pets()
    test_create_pet_and_get_pet()
    test_update_pet()
    test_delete_pet()
    close_connection()
    print("done.")
