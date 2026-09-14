import argparse
import database

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update the pet database.")
    parser.add_argument("database_file", nargs="?", default="pets.db")
    args = parser.parse_args()
    database.setup_database(args.database_file)
    database.connection.close()
    print(f"Ready: {args.database_file}")
