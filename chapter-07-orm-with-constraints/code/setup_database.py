"""Prepare the owner and pet tables without starting Flask."""
import argparse
import database

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare the Peewee pets and owners database.")
    parser.add_argument("database_file", nargs="?", default="pets.db")
    args = parser.parse_args()
    try:
        database.initialize(args.database_file)
    except database.SchemaNotCurrent as error:
        raise SystemExit(str(error))
    database.close_connection()
    print(f"Ready: {args.database_file}")
