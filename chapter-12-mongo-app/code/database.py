"""Pets data layer backed by local Mongita documents.

The application uses string IDs; stored _id and owner_id values are ObjectIds.
Mongita: https://github.com/scottrogowski/mongita
ObjectId: https://pymongo.readthedocs.io/en/stable/api/bson/objectid.html
"""
from pathlib import Path
from bson.errors import InvalidId

from bson.objectid import ObjectId
from mongita import MongitaClientDisk

try:
    from mongita import MongitaClientMemory
except ImportError:  # pragma: no cover - some mongita installs may omit this helper
    MongitaClientMemory = None

try:
    import pytest
except ImportError:  # pragma: no cover - only needed when running the tests
    pytest = None

DATA_DIR = Path(__file__).resolve().parent / "data" / "mongita"

client = None
db = None
owners_collection = None
pets_collection = None


class NotFoundError(LookupError):
    pass


class ConstraintError(ValueError):
    pass


def initialize(database_name="pets", client_factory=MongitaClientDisk, data_dir=None):
    global client, db, owners_collection, pets_collection

    if client_factory is MongitaClientMemory and MongitaClientMemory is None:
        if pytest is not None:
            pytest.skip("MongitaClientMemory is not available in this environment.")
        raise RuntimeError("MongitaClientMemory is not available in this environment.")

    close_connection()

    if client_factory is MongitaClientDisk:
        folder = Path(data_dir) if data_dir is not None else DATA_DIR
        folder.mkdir(parents=True, exist_ok=True)
        client = client_factory(host=str(folder))
    else:
        client = client_factory()
    db = client[database_name]
    owners_collection = db.owners
    pets_collection = db.pets


def test_initialize_sets_globals():
    initialize("pytest_initialize", client_factory=MongitaClientMemory)
    assert client is not None
    assert db is not None
    assert owners_collection is not None
    assert pets_collection is not None
    close_connection()


def setup_database(database_name="pets", client_factory=MongitaClientDisk, data_dir=None):
    """
    Prepare the Mongo database and ensure the collections exist.

    Mongita creates collections lazily when they are accessed, so touching the
    collection attributes here is enough to initialize a fresh database.
    """

    initialize(database_name, client_factory=client_factory, data_dir=data_dir)
    owners_collection.count_documents({})
    pets_collection.count_documents({})


def test_setup_database_creates_collections():
    setup_database("pytest_setup", client_factory=MongitaClientMemory)
    assert owners_collection is not None
    assert pets_collection is not None
    assert owners_collection.count_documents({}) == 0
    assert pets_collection.count_documents({}) == 0
    close_connection()


def close_connection():
    global client, db, owners_collection, pets_collection

    if client is not None:
        try:
            client.close()
        except Exception:
            pass
    client = None
    db = None
    owners_collection = None
    pets_collection = None


def test_close_connection_resets_globals():
    initialize("pytest_close", client_factory=MongitaClientMemory)
    close_connection()
    assert client is None
    assert db is None
    assert owners_collection is None
    assert pets_collection is None


def _normalize_age(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return 0
    try:
        age = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Age must be a whole number.") from exc
    if age < 0:
        raise ValueError("Age must be non-negative.")
    return age


def _require_text(value, field_name):
    text = (value or "").strip()
    if text == "":
        raise ValueError(f"{field_name} is required.")
    return text


def _to_object_id(value, field_name="id"):
    # A URL/form supplies text; an _id filter needs the stored ObjectId type.
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError) as exc:
        raise ValueError(f"{field_name} must be a valid ObjectId string.") from exc


def _require_owner(owner_id):
    object_id = _to_object_id(owner_id, "owner_id")
    owner = owners_collection.find_one({"_id": object_id})
    if owner is None:
        raise ConstraintError("owner_id does not reference an existing owner.")
    return object_id


def _require_existing_pet(id):
    object_id = _to_object_id(id, "pet id")
    pet = pets_collection.find_one({"_id": object_id})
    if pet is None:
        raise NotFoundError("pet not found.")
    return object_id, pet


def _require_existing_owner(id):
    object_id = _to_object_id(id, "owner id")
    owner = owners_collection.find_one({"_id": object_id})
    if owner is None:
        raise NotFoundError("owner not found.")
    return object_id, owner


def _normalize_pet_data(data):
    owner_id = data.get("owner_id")
    if (owner_id or "").strip() == "":
        raise ValueError("owner_id is required.")

    return {
        "name": _require_text(data.get("name"), "name"),
        "type": _require_text(data.get("type"), "type"),
        "age": _normalize_age(data.get("age")),
        "owner_id": _require_owner(owner_id),
    }


def _normalize_owner_data(data):
    return {
        "name": _require_text(data.get("name"), "name"),
        "city": (data.get("city") or "").strip() or None,
        "type_of_home": (data.get("type_of_home") or "").strip() or None,
    }


def pet_to_dict(pet):
    # Keep BSON identifiers inside this layer; the app receives ordinary strings.
    return {
        "id": str(pet["_id"]),
        "name": pet["name"],
        "type": pet["type"],
        "age": pet["age"],
        "owner_id": str(pet["owner_id"]),
    }


def test_pet_to_dict():
    sample = {
        "_id": ObjectId("67d8c61b5180a31695e90744"),
        "name": "meercat",
        "type": "mammal",
        "age": 2,
        "owner_id": ObjectId("67d8c61b5180a31695e90745"),
    }
    converted = pet_to_dict(sample)
    assert converted["id"] == "67d8c61b5180a31695e90744"
    assert converted["owner_id"] == "67d8c61b5180a31695e90745"
    assert converted["name"] == "meercat"
    assert converted["type"] == "mammal"
    assert converted["age"] == 2


def owner_to_dict(owner):
    return {
        "id": str(owner["_id"]),
        "name": owner["name"],
        "city": owner.get("city"),
        "type_of_home": owner.get("type_of_home"),
    }


def test_owner_to_dict():
    sample = {
        "_id": ObjectId("67d8c61b5180a31695e90746"),
        "name": "greg",
        "city": "Portland",
        "type_of_home": "condo",
    }
    converted = owner_to_dict(sample)
    assert converted["id"] == "67d8c61b5180a31695e90746"
    assert converted["name"] == "greg"
    assert converted["city"] == "Portland"
    assert converted["type_of_home"] == "condo"


def _seed_test_database(database_name="pytest_seed"):
    setup_database(database_name, client_factory=MongitaClientMemory)

    owners_collection.delete_many({})
    pets_collection.delete_many({})

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

    return owner_ids


def get_pets():
    return [pet_to_dict(pet) for pet in pets_collection.find()]


def test_get_pets():
    owner_ids = _seed_test_database()
    pets = get_pets()
    assert type(pets) is list
    assert len(pets) >= 1
    assert type(pets[0]) is dict
    for key in ["id", "name", "type", "age", "owner_id"]:
        assert key in pets[0]
    assert type(pets[0]["id"]) is str
    assert type(pets[0]["owner_id"]) is str
    assert pets[0]["owner_id"] in owner_ids.values()


def get_pet(id):
    object_id = _to_object_id(id, "pet id")
    pet = pets_collection.find_one({"_id": object_id})
    if pet is None:
        return None
    return pet_to_dict(pet)


def test_get_pet():
    owner_ids = _seed_test_database()
    pet = get_pets()[0]
    fetched = get_pet(pet["id"])
    assert fetched is not None
    assert fetched["id"] == pet["id"]
    assert fetched["owner_id"] in owner_ids.values()


def test_get_pet_missing_returns_none():
    _seed_test_database()
    assert get_pet("67d8c61b5180a31695e907ff") is None


def create_pet(data):
    pet = _normalize_pet_data(data)
    result = pets_collection.insert_one(pet)
    # insert_one returns an ObjectId; expose its 24-character text representation.
    return str(result.inserted_id)


def test_create_pet_and_get_pet():
    owner_ids = _seed_test_database()
    new_id = create_pet(
        {
            "name": "walter",
            "age": "2",
            "type": "mouse",
            "owner_id": owner_ids["greg"],
        }
    )
    assert type(new_id) is str
    pet = get_pet(new_id)
    assert pet is not None
    assert pet["id"] == new_id
    assert pet["name"] == "walter"
    assert pet["age"] == 2
    assert pet["type"] == "mouse"
    assert pet["owner_id"] == owner_ids["greg"]


def test_create_pet_requires_name():
    owner_ids = _seed_test_database()
    with pytest.raises(ValueError, match="name is required"):
        create_pet(
            {
                "name": "",
                "age": 1,
                "type": "cat",
                "owner_id": owner_ids["greg"],
            }
        )


def test_create_pet_requires_type():
    owner_ids = _seed_test_database()
    with pytest.raises(ValueError, match="type is required"):
        create_pet(
            {
                "name": "no-type",
                "age": 1,
                "type": "",
                "owner_id": owner_ids["greg"],
            }
        )


def test_create_pet_requires_owner():
    _seed_test_database()
    with pytest.raises(ValueError, match="owner_id is required"):
        create_pet({"name": "ghost", "age": 1, "type": "cat", "owner_id": ""})


def test_create_pet_rejects_unknown_owner():
    _seed_test_database()
    with pytest.raises(ConstraintError, match="owner_id"):
        create_pet(
            {
                "name": "ghost",
                "age": 1,
                "type": "cat",
                "owner_id": "000000000000000000000000",
            }
        )


def test_invalid_pet_id_rejected():
    _seed_test_database()
    with pytest.raises(ValueError, match="ObjectId"):
        get_pet("not-an-object-id")


def update_pet(id, data):
    object_id, _ = _require_existing_pet(id)
    pet = _normalize_pet_data(data)
    pets_collection.update_one({"_id": object_id}, {"$set": pet})


def test_update_pet():
    owner_ids = _seed_test_database()
    pet = get_pets()[0]
    update_pet(
        pet["id"],
        {"name": "updated", "age": "8", "type": "dog", "owner_id": owner_ids["david"]},
    )
    updated = get_pet(pet["id"])
    assert updated is not None
    assert updated["name"] == "updated"
    assert updated["age"] == 8
    assert updated["type"] == "dog"
    assert updated["owner_id"] == owner_ids["david"]


def test_update_pet_rejects_missing_pet():
    owner_ids = _seed_test_database()
    with pytest.raises(NotFoundError, match="pet not found"):
        update_pet(
            "67d8c61b5180a31695e907ff",
            {"name": "updated", "age": 8, "type": "dog", "owner_id": owner_ids["greg"]},
        )


def delete_pet(id):
    object_id, _ = _require_existing_pet(id)
    pets_collection.delete_one({"_id": object_id})


def test_delete_pet():
    owner_ids = _seed_test_database()
    new_id = create_pet(
        {"name": "delete_me", "age": 3, "type": "fish", "owner_id": owner_ids["greg"]}
    )
    delete_pet(new_id)
    assert get_pet(new_id) is None


def test_delete_missing_pet_raises_not_found():
    _seed_test_database()
    with pytest.raises(NotFoundError, match="pet not found"):
        delete_pet("000000000000000000000000")


def get_owners():
    return [owner_to_dict(owner) for owner in owners_collection.find()]


def test_get_owners():
    _seed_test_database()
    owners = get_owners()
    assert type(owners) is list
    assert len(owners) == 2
    assert type(owners[0]) is dict
    for key in ["id", "name", "city", "type_of_home"]:
        assert key in owners[0]


def get_owner(id):
    object_id = _to_object_id(id, "owner id")
    owner = owners_collection.find_one({"_id": object_id})
    if owner is None:
        return None
    return owner_to_dict(owner)


def test_get_owner():
    owner_ids = _seed_test_database()
    owner = get_owner(owner_ids["greg"])
    assert owner is not None
    assert owner["id"] == owner_ids["greg"]
    assert owner["name"] == "greg"
    assert owner["city"] == "Portland"


def test_get_owner_missing_returns_none():
    _seed_test_database()
    assert get_owner("67d8c61b5180a31695e907ff") is None


def create_owner(data):
    owner = _normalize_owner_data(data)
    result = owners_collection.insert_one(owner)
    # insert_one returns an ObjectId; expose its 24-character text representation.
    return str(result.inserted_id)


def test_create_owner_and_get_owner():
    _seed_test_database()
    new_id = create_owner({"name": "solo", "city": "Akron", "type_of_home": "house"})
    assert type(new_id) is str
    owner = get_owner(new_id)
    assert owner is not None
    assert owner["id"] == new_id
    assert owner["name"] == "solo"
    assert owner["city"] == "Akron"
    assert owner["type_of_home"] == "house"


def test_create_owner_requires_name():
    _seed_test_database()
    with pytest.raises(ValueError, match="name is required"):
        create_owner({"name": "", "city": "Akron", "type_of_home": "house"})


def update_owner(id, data):
    object_id, _ = _require_existing_owner(id)
    owner = _normalize_owner_data(data)
    owners_collection.update_one({"_id": object_id}, {"$set": owner})


def test_update_owner():
    owner_ids = _seed_test_database()
    update_owner(
        owner_ids["greg"],
        {"name": "gregory", "city": "Salem", "type_of_home": "cabin"},
    )
    updated = get_owner(owner_ids["greg"])
    assert updated is not None
    assert updated["name"] == "gregory"
    assert updated["city"] == "Salem"
    assert updated["type_of_home"] == "cabin"


def test_update_owner_rejects_missing_owner():
    _seed_test_database()
    with pytest.raises(NotFoundError, match="owner not found"):
        update_owner(
            "67d8c61b5180a31695e907ff",
            {"name": "missing", "city": "Nowhere", "type_of_home": "house"},
        )


def delete_owner(id):
    object_id, _ = _require_existing_owner(id)
    pet = pets_collection.find_one({"owner_id": object_id})
    if pet is not None:
        raise ConstraintError(
            "Cannot delete this owner because they have pets. Please delete their pets first."
        )

    owners_collection.delete_one({"_id": object_id})


def test_delete_owner_restricted():
    owner_ids = _seed_test_database()
    with pytest.raises(ConstraintError, match="have pets"):
        delete_owner(owner_ids["greg"])


def test_delete_owner_then_pet_succeeds():
    _seed_test_database()
    owner_id = create_owner({"name": "solo", "city": "Akron", "type_of_home": "house"})
    pet_id = create_pet(
        {"name": "onepet", "age": 3, "type": "cat", "owner_id": owner_id}
    )

    with pytest.raises(ConstraintError):
        delete_owner(owner_id)

    delete_pet(pet_id)
    delete_owner(owner_id)
    assert get_owner(owner_id) is None


def test_delete_missing_owner_raises_not_found():
    _seed_test_database()
    with pytest.raises(NotFoundError, match="owner not found"):
        delete_owner("000000000000000000000000")


if __name__ == "__main__":
    owner_ids = _seed_test_database("manual_seed")
    assert len(get_pets()) == 4
    assert len(get_owners()) == 2
    assert get_owner(owner_ids["greg"]) is not None
    close_connection()
    print("done.")
