"""Pets database operations, independent of the web interface.

The functions keep the pets-and-owners interface used by the SQL examples.
Each operation owns its connection so browser sessions do not share one.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3

DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "pets.db"
ConstraintError = sqlite3.IntegrityError


@contextmanager
def connection():
    path = Path(os.environ.get("PETS_DATABASE", DEFAULT_PATH))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        with db:  # Commit on success, roll back on an exception.
            yield db
    finally:
        db.close()


def initialize():
    with connection() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS owner (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL CHECK(length(trim(name)) > 0),
                city TEXT,
                type_of_home TEXT
            );
            CREATE TABLE IF NOT EXISTS pet (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL CHECK(length(trim(name)) > 0),
                age INTEGER NOT NULL CHECK(age >= 0),
                type TEXT NOT NULL CHECK(length(trim(type)) > 0),
                food TEXT,
                owner_id INTEGER NOT NULL REFERENCES owner(id) ON DELETE RESTRICT
            );
            CREATE INDEX IF NOT EXISTS idx_pet_owner_id ON pet(owner_id);
        """)

#show owners
def get_owners():
    with connection() as db:
        return [dict(x) for x in db.execute("SELECT * FROM owner ORDER BY name, id")]

#get food table
def get_foods():
    with connection() as db:
        return [dict(x) for x in db.execute("""
            SELECT pet.id AS id,
                    pet.food AS food,
                    pet.name AS pet_name,
                    owner.name AS owner_name
            FROM pet
            JOIN owner ON pet.owner_id = owner.id
        """)]
#show pets
def get_pets():
    with connection() as db:
        return [dict(x) for x in db.execute("""
            SELECT pet.*, owner.name AS owner_name FROM pet
            JOIN owner ON pet.owner_id = owner.id ORDER BY pet.name, pet.id
        """)]


def get_owner(id):
    with connection() as db:
        row = db.execute("SELECT * FROM owner WHERE id=?", (id,)).fetchone()
        return dict(row) if row else None


def get_pet(id):
    with connection() as db:
        row = db.execute("SELECT * FROM pet WHERE id=?", (id,)).fetchone()
        return dict(row) if row else None


def owner_values(data):
    name = data["name"].strip()
    if not name:
        raise ValueError("Owner name is required.")
    return name, data.get("city", "").strip(), data.get("type_of_home", "").strip()


def pet_values(data):
    name, kind = data["name"].strip(), data["type"].strip()
    if not name or not kind:
        raise ValueError("Pet name and type are required.")
    age = int(data["age"])
    if age < 0:
        raise ValueError("Age must be non-negative.")
    return name, age, kind, data.get("food", "").strip(), int(data["owner_id"])


def create_owner(data):
    with connection() as db:
        return db.execute("INSERT INTO owner(name,city,type_of_home) VALUES (?,?,?)",
                          owner_values(data)).lastrowid


def update_owner(id, data):
    with connection() as db:
        result = db.execute("UPDATE owner SET name=?,city=?,type_of_home=? WHERE id=?",
                            (*owner_values(data), id))
        if not result.rowcount:
            raise ValueError("That owner no longer exists. Refresh the page.")


def delete_owner(id):
    with connection() as db:
        db.execute("DELETE FROM owner WHERE id=?", (id,))


def create_pet(data):
    with connection() as db:
        return db.execute("""INSERT INTO pet(name,age,type,food,owner_id)
                             VALUES (?,?,?,?,?)""", pet_values(data)).lastrowid


def update_pet(id, data):
    with connection() as db:
        result = db.execute("""UPDATE pet SET name=?,age=?,type=?,food=?,owner_id=?
                               WHERE id=?""", (*pet_values(data), id))
        if not result.rowcount:
            raise ValueError("That pet no longer exists. Refresh the page.")


def delete_pet(id):
    with connection() as db:
        db.execute("DELETE FROM pet WHERE id=?", (id,))


def seed_demo():
    """Seed once into a completely empty database; never reset existing work."""
    initialize()
    with connection() as db:
        if db.execute("SELECT count(*) FROM owner").fetchone()[0]:
            return False
        alex = db.execute("INSERT INTO owner(name,city,type_of_home) VALUES (?,?,?)",
                          ("Alex", "Kent", "House")).lastrowid
        jordan = db.execute("INSERT INTO owner(name,city,type_of_home) VALUES (?,?,?)",
                            ("Jordan", "Akron", "Apartment")).lastrowid
        db.executemany("INSERT INTO pet(name,age,type,food,owner_id) VALUES (?,?,?,?,?)",
                       [("Casey", 3, "Dog", "Kibble", alex),
                        ("Luna", 5, "Cat", "Wet food", jordan)])
        return True


if __name__ == "__main__":
    print("Demo records created." if seed_demo() else "Existing records kept.")
