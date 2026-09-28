"""Build current tables and reload the data from an older pets database.

Usage: python3 upgrade_database.py [database_file]

create_tables() never changes a table that already exists, so a file made by
an earlier example keeps its old rules. This script builds a new file with the
current tables, reloads every row that satisfies the rules, and then swaps the
new file into place. The original file is kept beside it as
<name>.before-upgrade, so nothing is lost.

Files that are already current, and files that do not exist yet, are left
alone or created empty.
"""
import argparse
from datetime import datetime
import os
from pathlib import Path
import sqlite3

from peewee import IntegrityError

import database
from database import Owner, Pet

UNASSIGNED = "Unassigned"
# Old columns this example reads, directly or by turning them into owners.
USED_COLUMNS = {"id", "name", "type", "age", "owner_id", "owner", "city", "type_of_home"}


def read_old_rows(path):
    connection = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {row[0] for row in connection.execute(
            "select name from sqlite_master where type = 'table'")}
        owners = []
        pets = []
        pet_columns = set()
        if "owner" in tables:
            owners = [dict(row) for row in connection.execute("select * from owner order by id")]
        if "pet" in tables:
            pets = [dict(row) for row in connection.execute("select * from pet order by id")]
            pet_columns = {row[1] for row in connection.execute("pragma table_info(pet)")}
        return owners, pets, pet_columns
    finally:
        connection.close()


def clean(value):
    return (value or "").strip() or None


def load_rows(owners, pets, report):
    """Insert what satisfies the rules. Anything else is listed in the report."""
    loaded_owner_ids = set()
    owner_ids_by_name = {}
    for row in owners:
        try:
            with database.db.atomic():
                Owner.create(id=row["id"], name=(row["name"] or "").strip(),
                             city=clean(row.get("city")),
                             type_of_home=clean(row.get("type_of_home")))
        except IntegrityError as error:
            report["skipped"].append(f"owner {row['id']} ({row['name']!r}): {error}")
            continue
        loaded_owner_ids.add(row["id"])
        owner_ids_by_name.setdefault(row["name"].strip().lower(), row["id"])
        report["owners"] += 1

    unassigned_id = None
    for row in pets:
        owner_id = row.get("owner_id")
        if owner_id is None and clean(row.get("owner")):
            # An earlier example kept the owner's name as text on the pet.
            key = row["owner"].strip().lower()
            if key not in owner_ids_by_name:
                owner_ids_by_name[key] = Owner.create(name=row["owner"].strip()).id
                report["owners"] += 1
            owner_id = owner_ids_by_name[key]
        elif owner_id is not None and owner_id not in loaded_owner_ids:
            report["skipped"].append(f"pet {row['id']} ({row['name']!r}): its owner was not loaded")
            continue
        if owner_id is None:
            if unassigned_id is None:
                unassigned_id = Owner.create(name=UNASSIGNED).id
                report["owners"] += 1
            owner_id = unassigned_id
            report["unassigned"] += 1

        try:
            age = 0 if row.get("age") is None else int(row["age"])
            with database.db.atomic():
                Pet.create(id=row["id"], name=(row["name"] or "").strip(),
                           type=(row["type"] or "").strip(), age=age, owner=owner_id)
        except (IntegrityError, ValueError) as error:
            report["skipped"].append(f"pet {row['id']} ({row['name']!r}): {error}")
            continue
        report["pets"] += 1


def backup_name(path):
    backup = Path(f"{path}.before-upgrade")
    if backup.exists():
        backup = Path(f"{path}.before-upgrade-{datetime.now():%Y%m%d%H%M%S}")
    return backup


def upgrade(database_file):
    """Make database_file current. Returns a dictionary describing what happened."""
    path = Path(database_file)
    report = {"status": "current", "owners": 0, "pets": 0, "unassigned": 0,
              "skipped": [], "not_carried": [], "problems": [], "backup": None}

    problems = database.schema_problems(path)
    if not path.exists():
        database.initialize(path)
        database.close_connection()
        report["status"] = "created"
        return report
    if not problems:
        return report

    report["problems"] = problems
    owners, pets, pet_columns = read_old_rows(path)
    report["not_carried"] = sorted(pet_columns - USED_COLUMNS)

    new_path = Path(f"{path}.new")
    new_path.unlink(missing_ok=True)
    try:
        database.initialize(new_path)
        load_rows(owners, pets, report)
    finally:
        database.close_connection()
    backup = backup_name(path)
    os.replace(path, backup)
    os.replace(new_path, path)
    report["backup"] = str(backup)
    report["status"] = "upgraded"
    return report


def print_report(database_file, report):
    if report["status"] == "current":
        print(f"{database_file} already matches the current tables.")
        return
    if report["status"] == "created":
        print(f"{database_file} did not exist. Created empty current tables.")
        return
    print(f"Upgraded {database_file}.")
    for problem in report["problems"]:
        print(f"  found: {problem}")
    print(f"  loaded {report['owners']} owners and {report['pets']} pets")
    if report["unassigned"]:
        print(f"  {report['unassigned']} pets had no owner and now belong to '{UNASSIGNED}'")
    if report["not_carried"]:
        print("  not carried over (no column for them here): " + ", ".join(report["not_carried"]))
    for line in report["skipped"]:
        print(f"  skipped {line}")
    print(f"  original file kept as {report['backup']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build current tables and reload an older pets database.")
    parser.add_argument("database_file", nargs="?", default="pets.db")
    args = parser.parse_args()
    print_report(args.database_file, upgrade(args.database_file))
