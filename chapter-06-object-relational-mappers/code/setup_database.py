"""Prepare the pet table without starting Flask."""
import argparse
import database

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare the Peewee pet database.")
    parser.add_argument("database_file", nargs="?", default="pets.db")
    args = parser.parse_args()
    database.initialize(args.database_file)
    database.close_connection()
    print(f"Ready: {args.database_file}")
