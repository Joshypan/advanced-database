import sqlite3
from pprint import pprint

connection = None

def initialize(database_file):
    global connection
    connection = sqlite3.connect(database_file, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    print("succeeded in making connection.")

def setup_database(database_file):
    initialize(database_file)
    connection.execute(
        """create table if not exists pet (
            id integer primary key autoincrement,
            name text not null,
            type text not null,
            age integer,
            food text,
            owner text
        )"""
    )
    columns = {row["name"] for row in connection.execute("pragma table_info(pet)")}
    for column in ("food", "owner"):
        if column not in columns:
            connection.execute("alter table pet add column " + column + " text")
    connection.commit()


def get_pets():
    cursor = connection.cursor()
    cursor.execute("""select * from pet order by id""")
    pets = cursor.fetchall()
    pets = [dict(pet) for pet in pets]
    for pet in pets:
        print(pet)
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
        """insert into pet(name, age, type, food, owner) values (?,?,?,?,?)""",
        (data["name"], data["age"], data["type"], data["food"], data["owner"]),
    )
    connection.commit()

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
        """update pet set name=?, age=?, type=?, food=?, owner=? where id=?""",
        (data["name"], data["age"], data["type"], data["food"], data["owner"], id),
    )
    connection.commit()

def setup_test_database():
    setup_database("test_pets.db")
    connection.execute("delete from pet")
    connection.commit()
    pets = [
        {"name": "dorothy", "type": "dog", "age": 9, "food": "pet food", "owner": "greg"},
        {"name": "suzy", "type": "mouse", "age": 9, "food": "pet food", "owner": "greg"},
        {"name": "casey", "type": "dog", "age": 9, "food": "pet food", "owner": "greg"},
        {"name": "heidi", "type": "cat", "age": 15, "food": "tuna", "owner": "david"},
    ]
    for pet in pets:
        create_pet(pet)
    pets = get_pets()
    assert len(pets) == 4


def test_get_pets():
    print("testing get_pets()")
    pets = get_pets()
    assert type(pets) is list
    assert type(pets[0]) is dict
    for key in ["name", "age", "type", "food", "owner"]:
        assert key in pets[0]
        assert type(pets[0]["name"]) == str 


def test_create_pet():
    print("testing create_pet()")
    create_pet({"name": "Food test", "age": 2, "type": "cat",
                "food": "salmon", "owner": "alex"})
    pet = get_pets()[-1]
    assert pet["food"] == "salmon"
    assert pet["owner"] == "alex"
    pet["food"] = "tuna"
    pet["owner"] = "sam"
    update_pet(pet["id"], pet)
    saved = get_pet(pet["id"])
    assert saved["food"] == "tuna"
    assert saved["owner"] == "sam"
    delete_pet(pet["id"])
    assert get_pet(pet["id"]) is None


if __name__ == "__main__":
    setup_test_database()
    test_get_pets()
    test_create_pet()
    print("done.")

# initialize("pets.db")
# cursor = connection.execute("select * from pet")
# rows = [dict(row) for row in cursor.fetchall()]
# pprint(rows)

# These is a tuple
# ("a",1,"b",2)
# This is a dictionary
# { "name": "a","age":1,"kind":"b","whatever":2 }
