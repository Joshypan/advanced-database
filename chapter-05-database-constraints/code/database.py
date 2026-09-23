import sqlite3
import os
from pprint import pprint

connection = None

def initialize(database_file):
    global connection

    # Close any prior connection so PRAGMAs and file handles are clean.
    if connection is not None:
        try:
            connection.close()
        except Exception:
            pass
        connection = None

    connection = sqlite3.connect(database_file, check_same_thread=False)
    connection.row_factory = sqlite3.Row

    # Enforce foreign keys (per-connection in SQLite).
    connection.execute("PRAGMA foreign_keys = ON")

    # Fail fast if constraints are not active.
    fk = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1, "Foreign key constraints are not active on this connection."
    print("succeeded in making connection.")

def close_connection():
    global connection
    if connection is not None:
        try:
            connection.close()
        finally:
            connection = None


def get_owners():
    cursor = connection.cursor()
    cursor.execute("""select * from owner""")
    owners = [dict(owner) for owner in cursor.fetchall()]
    return owners


def get_owner(id):
    id = int(id)
    cursor = connection.cursor()
    cursor.execute("select * from owner where id = ?", (id,))
    owners = [dict(row) for row in cursor.fetchall()]
    if len(owners) == 0:
        return None
    assert len(owners) == 1
    return owners[0]

def create_owner(data):
    cursor = connection.cursor()
    cursor.execute(
        """insert into owner(name, city, type_of_home) values (?,?,?)""",
        (data["name"], data.get("city"), data.get("type_of_home")),
    )
    connection.commit()
    return cursor.lastrowid

def delete_owner(id):
    id = int(id)
    cursor = connection.cursor()
    cursor.execute("""delete from owner where id = ?""", (id,))
    connection.commit()

def update_owner(id, data):
    cursor = connection.cursor()
    cursor.execute(
        """update owner set name=?, city=?, type_of_home=? where id=?""",
        (data["name"], data.get("city"), data.get("type_of_home"), id),
    )
    connection.commit()


def get_pets():
    cursor = connection.cursor()
    cursor.execute("""select * from pet order by id""")
    pets = cursor.fetchall()
    pets = [dict(pet) for pet in pets]
    return pets

def get_pet(id):
    id = int(id)
    cursor = connection.cursor()
    cursor.execute("""select * from pet where id = ?""", (id,))
    pet = cursor.fetchone()
    if pet is None:
        return None
    return dict(pet)

def create_pet(data):
    try:
        data["age"] = int(data["age"])
    except:
        data["age"] = 0
    cursor = connection.cursor()
    cursor.execute(
        """insert into pet(name, age, type, food, owner_id) values (?,?,?,?,?)""",
        (data["name"], data["age"], data["type"], data.get("food", ""), data["owner_id"]),
    )
    connection.commit()
    return cursor.lastrowid

def delete_pet(id):
    id = int(id)
    cursor = connection.cursor()
    cursor.execute("""delete from pet where id = ?""", (id,))
    connection.commit()

def update_pet(id, data):
    try:
        data["age"] = int(data["age"])
    except:
        data["age"] = 0
    cursor = connection.cursor()
    cursor.execute(
        """update pet set name=?, age=?, type=?, food=?, owner_id=? where id=?""",
        (data["name"], data["age"], data["type"], data.get("food", ""), data["owner_id"], id),
    )
    connection.commit()

def setup_database(database_file="pets.db"):
    initialize(database_file)

    cursor = connection.cursor()

    cursor.execute(
        """
        create table if not exists owner (
            id integer primary key autoincrement,
            name text not null,
            city text,
            type_of_home text
        )
        """
    )
    cursor.execute(
        """
        create table if not exists pet (
            id integer primary key autoincrement,
            name text not null,
            type text not null,
            age integer,
            food text,
            owner_id integer not null,
            foreign key (owner_id) references owner(id) on delete restrict
        )
        """
    )
    columns = {row["name"] for row in connection.execute("pragma table_info(pet)")}
    if "food" not in columns:
        connection.execute("alter table pet add column food text")
    connection.commit()


def setup_test_database(db_file="test_pets.db"):
    # Always start from a fresh file.
    close_connection()
    try:
        os.remove(db_file)
    except FileNotFoundError:
        pass

    setup_database(db_file)

    owners = [
        {"name": "greg", "city": "Portland", "type_of_home": "condo"},
        {"name": "david", "city": "Seattle", "type_of_home": "farm"},
    ]
    owner_ids = {}
    for owner in owners:
        owner_id = create_owner(owner)
        owner_ids[owner["name"]] = owner_id

    pets = [
        {"name": "dorothy", "type": "dog", "age": 9, "owner": "greg"},
        {"name": "suzy", "type": "mouse", "age": 9, "owner": "greg"},
        {"name": "casey", "type": "dog", "age": 9, "owner": "greg"},
        {"name": "heidi", "type": "cat", "age": 15, "owner": "david"},
    ]
    for pet in pets:
        pet["owner_id"] = owner_ids[pet["owner"]]
        create_pet(
            {
                "name": pet["name"],
                "age": pet["age"],
                "type": pet["type"],
                "food": "pet food",
                "owner_id": pet["owner_id"],
            }
        )

    assert len(get_pets()) == 4
    return owner_ids

def test_constraints_are_active():
    fk = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1


def test_get_pets():
    pets = get_pets()
    assert type(pets) is list
    assert len(pets) >= 1
    assert type(pets[0]) is dict
    for key in ["name", "age", "type", "food", "owner_id", "id"]:
        assert key in pets[0]
    assert type(pets[0]["name"]) is str


def test_create_pet_and_get_pet(owner_ids):
    new_id = create_pet(
        {"name": "walter", "age": "2", "type": "mouse", "food": "seeds", "owner_id": owner_ids["greg"]}
    )
    pet = get_pet(new_id)
    assert pet is not None
    assert pet["name"] == "walter"
    assert pet["age"] == 2
    assert pet["type"] == "mouse"
    assert pet["owner_id"] == owner_ids["greg"]
    assert pet["food"] == "seeds"
    pet["food"] = "grain"
    update_pet(new_id, pet)
    assert get_pet(new_id)["food"] == "grain"
    delete_pet(new_id)
    assert get_pet(new_id) is None


def test_fk_rejects_bad_owner_id():
    try:
        create_pet({"name": "ghost", "age": 1, "type": "dog", "owner_id": 999999})
        assert False, "Expected FOREIGN KEY constraint failure, but insert succeeded."
    except sqlite3.IntegrityError as e:
        msg = str(e).lower()
        assert "foreign key" in msg or "constraint" in msg


def test_delete_owner_restricted(owner_ids):
    # greg owns multiple pets; delete should be restricted.
    try:
        delete_owner(owner_ids["greg"])
        assert False, "Expected delete restriction failure, but delete succeeded."
    except sqlite3.IntegrityError as e:
        msg = str(e).lower()
        assert "foreign key" in msg or "constraint" in msg


def test_delete_pet_then_delete_owner_succeeds(owner_ids):
    # Create a new owner with a single pet, then remove pet and ensure owner can be deleted.
    owner_id = create_owner({"name": "solo", "city": "Akron", "type_of_home": "house"})
    pet_id = create_pet(
        {"name": "onepet", "age": 3, "type": "cat", "owner_id": owner_id}
    )

    # Deleting owner now should fail.
    try:
        delete_owner(owner_id)
        assert False, "Expected delete restriction failure, but delete succeeded."
    except sqlite3.IntegrityError:
        pass

    # Remove pet, then delete owner should work.
    delete_pet(pet_id)
    delete_owner(owner_id)
    assert get_owner(owner_id) is None


def test_get_owners():
    print("test get_owners()")
    owners = get_owners()
    assert type(owners) is list
    assert type(owners[0]) is dict
    for key in ["name","city","type_of_home"]:
        assert key in owners[0]
        assert type(owners[0]["name"]) == str 
        assert type(owners[0]["type_of_home"]) == str 

def test_get_owner():
    print("test get_owner()")
    owner = get_owner(2)
    assert owner["name"] == "david"

def test_create_owner():
    print("test create_owner()")
    create_owner({
        "name":"santa",
        "city":"north pole",
        "type_of_home":"workshop"
    })
    owners = get_owners()
    owners = [owner for owner in owners if owner["name"] == "santa"]
    owner = owners[0]
    assert owner["name"] == "santa"
    assert owner["city"] == "north pole"
    assert owner["type_of_home"] == "workshop"

def test_update_owner():
    print("test update_owner()")
    owners = get_owners()
    owner = [owner for owner in owners if owner["name"] == "david"][0]
    owner["name"] = "dave"
    owner["city"] = "riverside"
    owner["type_of_home"] = "suburban"
    id = owner["id"]
    update_owner(id, owner)
    owners = get_owners()
    owners = [owner for owner in owners if owner["name"] == "dave"][0]
    assert owner["id"] == id
    assert owner["name"] == "dave"
    assert owner["city"] == "riverside"
    assert owner["type_of_home"] == "suburban"

def test_delete_owner():
    print("test delete_owner()")
    owners = get_owners()
    owner = [owner for owner in owners if owner["name"] == "santa"][0]
    id = owner["id"]
    delete_owner(id)
    owners = get_owners()
    owners = [owner for owner in owners if owner["name"] == "santa"]
    assert owners == []


if __name__ == "__main__":
    owner_ids = setup_test_database()

    # Run tests in a simple way without pytest, but still pytest-compatible.
    test_constraints_are_active()
    test_get_pets()
    test_create_pet_and_get_pet(owner_ids)
    test_fk_rejects_bad_owner_id()
    test_delete_owner_restricted(owner_ids)
    test_delete_pet_then_delete_owner_succeeds(owner_ids)
    test_get_owners()
    test_get_owner()
    test_create_owner()
    test_update_owner()
    test_delete_owner()
    close_connection()
    print("done.")
