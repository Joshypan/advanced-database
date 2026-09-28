import os
from pathlib import Path
import sqlite3

from peewee import (
    Check,
    ForeignKeyField,
    IntegerField,
    IntegrityError,
    Model,
    SqliteDatabase,
    TextField,
)

# Bind the file later so the app and tests can use different databases.
db = SqliteDatabase(None)


class BaseModel(Model):
    class Meta:
        database = db


class Owner(BaseModel):
    name = TextField(null=False, constraints=[Check("length(trim(name)) > 0")])
    city = TextField(null=True)
    type_of_home = TextField(null=True)


class Pet(BaseModel):
    name = TextField(null=False, constraints=[Check("length(trim(name)) > 0")])
    type = TextField(null=False, constraints=[Check("length(trim(type)) > 0")])
    age = IntegerField(default=0, constraints=[Check("age >= 0")])
    owner = ForeignKeyField(Owner, backref="pets", null=False, on_delete="RESTRICT")


class SchemaNotCurrent(Exception):
    """An existing database file does not have this example's tables and rules."""


def schema_problems(database_file):
    """List the known differences between an existing file and the models.

    This is a heuristic. It recognizes the layouts earlier examples produced
    (no owner table, no owner_id, no ON DELETE RESTRICT, no CHECK rules) and
    does not compare every rule or index. A missing file or a file without
    owner and pet tables has no problems, because create_tables() can build
    what is missing. The file is opened read-only and never changed.
    """
    path = Path(database_file)
    if not path.exists():
        return []
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        sql = dict(connection.execute(
            "select name, sql from sqlite_master "
            "where type = 'table' and name in ('owner', 'pet')").fetchall())
        pet_columns = {row[1] for row in connection.execute("pragma table_info(pet)")}
    finally:
        connection.close()

    problems = []
    if "pet" in sql:
        pet_sql = sql["pet"].lower()
        if "owner" not in sql:
            problems.append("There is a pet table but no owner table.")
        if "owner_id" not in pet_columns:
            problems.append("The pet table has no owner_id column.")
        elif "on delete restrict" not in pet_sql:
            problems.append("The pet table does not restrict deleting an owner who has pets.")
        if "check" not in pet_sql:
            problems.append("The pet table has no CHECK rules.")
    if "owner" in sql and "check" not in sql["owner"].lower():
        problems.append("The owner table has no CHECK rule on name.")
    return problems


def initialize(database_file):
    if not db.is_closed():
        db.close()

    # create_tables() never changes a table that already exists, so an older
    # file has to be rebuilt with upgrade_database.py. Nothing here drops data.
    problems = schema_problems(database_file)
    if problems:
        raise SchemaNotCurrent(
            f"{database_file} does not match this example's tables. "
            + " ".join(problems)
            + " Run python3 upgrade_database.py to build current tables "
            "and reload the data."
        )

    db.init(database_file, pragmas={"foreign_keys": 1})
    db.connect(reuse_if_open=True)
    db.create_tables([Owner, Pet])

    fk = db.execute_sql("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1, "Foreign key constraints are not active on this connection."


def close_connection():
    if not db.is_closed():
        db.close()


def _normalize_age(value):
    if value is None:
        return 0
    if isinstance(value, str) and value.strip() == "":
        return 0

    age = int(value)
    if age < 0:
        raise ValueError("Age must be non-negative.")
    return age


def owner_to_dict(owner):
    return {
        "id": owner.id,
        "name": owner.name,
        "city": owner.city,
        "type_of_home": owner.type_of_home,
    }


def pet_to_dict(pet):
    return {
        "id": pet.id,
        "name": pet.name,
        "type": pet.type,
        "age": pet.age,
        "owner_id": pet.owner_id,
        "owner_name": pet.owner.name,
    }


def get_owners():
    query = Owner.select().order_by(Owner.name, Owner.id)
    return [owner_to_dict(owner) for owner in query]


def get_owner(id):
    owner = Owner.get_or_none(Owner.id == int(id))
    if owner is None:
        return None
    return owner_to_dict(owner)


def create_owner(data):
    name = (data.get("name") or "").strip()
    if name == "":
        raise ValueError("Owner name is required.")

    owner = Owner.create(
        name=name,
        city=(data.get("city") or "").strip() or None,
        type_of_home=(data.get("type_of_home") or "").strip() or None,
    )
    return owner.id


def delete_owner(id):
    owner = Owner.get_or_none(Owner.id == int(id))
    if owner is None:
        return
    owner.delete_instance()


def update_owner(id, data):
    owner = Owner.get_or_none(Owner.id == int(id))
    if owner is None:
        return

    name = (data.get("name") or "").strip()
    if name == "":
        raise ValueError("Owner name is required.")

    owner.name = name
    owner.city = (data.get("city") or "").strip() or None
    owner.type_of_home = (data.get("type_of_home") or "").strip() or None
    owner.save()


def get_pets():
    query = Pet.select(Pet, Owner).join(Owner).order_by(Pet.name, Pet.id)
    return [pet_to_dict(pet) for pet in query]


def get_pet(id):
    pet = (
        Pet.select(Pet, Owner)
        .join(Owner)
        .where(Pet.id == int(id))
        .first()
    )
    if pet is None:
        return None
    return pet_to_dict(pet)


def create_pet(data):
    name = (data.get("name") or "").strip()
    pet_type = (data.get("type") or "").strip()
    owner_id = data.get("owner_id")

    if name == "":
        raise ValueError("Pet name is required.")
    if pet_type == "":
        raise ValueError("Pet type is required.")
    if owner_id is None or str(owner_id).strip() == "":
        raise ValueError("owner_id is required.")

    pet = Pet.create(
        name=name,
        type=pet_type,
        age=_normalize_age(data.get("age")),
        owner=int(owner_id),
    )
    return pet.id


def delete_pet(id):
    Pet.delete().where(Pet.id == int(id)).execute()


def update_pet(id, data):
    pet = Pet.get_or_none(Pet.id == int(id))
    if pet is None:
        return

    name = (data.get("name") or "").strip()
    pet_type = (data.get("type") or "").strip()
    owner_id = data.get("owner_id")

    if name == "":
        raise ValueError("Pet name is required.")
    if pet_type == "":
        raise ValueError("Pet type is required.")
    if owner_id is None or str(owner_id).strip() == "":
        raise ValueError("owner_id is required.")

    pet.name = name
    pet.type = pet_type
    pet.age = _normalize_age(data.get("age"))
    pet.owner = int(owner_id)
    pet.save()


def setup_test_database(db_file="test_pets.db"):
    close_connection()
    try:
        os.remove(db_file)
    except FileNotFoundError:
        pass

    initialize(db_file)

    owners = [
        {"name": "greg", "city": "Portland", "type_of_home": "condo"},
        {"name": "david", "city": "Seattle", "type_of_home": "farm"},
    ]
    owner_ids = {}
    for owner in owners:
        owner_id = create_owner(owner)
        owner_ids[owner["name"]] = owner_id

    pets = [
        {"name": "dorothy", "type": "dog", "age": 9, "owner_id": owner_ids["greg"]},
        {"name": "suzy", "type": "mouse", "age": 9, "owner_id": owner_ids["greg"]},
        {"name": "casey", "type": "dog", "age": 9, "owner_id": owner_ids["greg"]},
        {"name": "heidi", "type": "cat", "age": 15, "owner_id": owner_ids["david"]},
    ]
    for pet in pets:
        create_pet(pet)

    assert len(get_pets()) == 4
    return owner_ids


def test_constraints_are_active():
    fk = db.execute_sql("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1


def test_get_pets():
    pets = get_pets()
    assert type(pets) is list
    assert len(pets) >= 1
    assert type(pets[0]) is dict
    for key in ["id", "name", "type", "age", "owner_id", "owner_name"]:
        assert key in pets[0]
    assert type(pets[0]["name"]) is str


def test_create_pet_and_get_pet(owner_ids):
    new_id = create_pet(
        {"name": "walter", "age": "2", "type": "mouse", "owner_id": owner_ids["greg"]}
    )
    pet = get_pet(new_id)
    assert pet is not None
    assert pet["name"] == "walter"
    assert pet["age"] == 2
    assert pet["type"] == "mouse"
    assert pet["owner_id"] == owner_ids["greg"]


def test_fk_rejects_bad_owner_id():
    try:
        create_pet({"name": "ghost", "age": 1, "type": "dog", "owner_id": 999999})
        assert False, "Expected FOREIGN KEY constraint failure, but insert succeeded."
    except IntegrityError as e:
        msg = str(e).lower()
        assert "foreign key" in msg or "constraint" in msg


def test_delete_owner_restricted(owner_ids):
    try:
        delete_owner(owner_ids["greg"])
        assert False, "Expected delete restriction failure, but delete succeeded."
    except IntegrityError as e:
        msg = str(e).lower()
        assert "foreign key" in msg or "constraint" in msg


def test_delete_pet_then_delete_owner_succeeds():
    owner_id = create_owner({"name": "solo", "city": "Akron", "type_of_home": "house"})
    pet_id = create_pet(
        {"name": "onepet", "age": 3, "type": "cat", "owner_id": owner_id}
    )

    try:
        delete_owner(owner_id)
        assert False, "Expected delete restriction failure, but delete succeeded."
    except IntegrityError:
        pass

    delete_pet(pet_id)
    delete_owner(owner_id)
    assert get_owner(owner_id) is None


def test_get_owners():
    owners = get_owners()
    assert type(owners) is list
    assert len(owners) >= 1
    assert type(owners[0]) is dict
    for key in ["id", "name", "city", "type_of_home"]:
        assert key in owners[0]


def test_get_owner():
    owner = get_owner(2)
    assert owner["name"] == "david"


def test_create_owner():
    create_owner({"name": "santa", "city": "north pole", "type_of_home": "workshop"})
    owners = get_owners()
    owners = [owner for owner in owners if owner["name"] == "santa"]
    owner = owners[0]
    assert owner["name"] == "santa"
    assert owner["city"] == "north pole"
    assert owner["type_of_home"] == "workshop"


def test_update_owner():
    owners = get_owners()
    owner = [owner for owner in owners if owner["name"] == "david"][0]
    owner["name"] = "dave"
    owner["city"] = "riverside"
    owner["type_of_home"] = "suburban"
    owner_id = owner["id"]
    update_owner(owner_id, owner)
    owner = get_owner(owner_id)
    assert owner["id"] == owner_id
    assert owner["name"] == "dave"
    assert owner["city"] == "riverside"
    assert owner["type_of_home"] == "suburban"


def test_delete_owner():
    owners = get_owners()
    owner = [owner for owner in owners if owner["name"] == "santa"][0]
    owner_id = owner["id"]
    delete_owner(owner_id)
    owners = get_owners()
    owners = [owner for owner in owners if owner["name"] == "santa"]
    assert owners == []


if __name__ == "__main__":
    owner_ids = setup_test_database()

    test_constraints_are_active()
    test_get_pets()
    test_create_pet_and_get_pet(owner_ids)
    test_fk_rejects_bad_owner_id()
    test_delete_owner_restricted(owner_ids)
    test_delete_pet_then_delete_owner_succeeds()
    test_get_owners()
    test_get_owner()
    test_create_owner()
    test_update_owner()
    test_delete_owner()
    close_connection()
    print("done.")
