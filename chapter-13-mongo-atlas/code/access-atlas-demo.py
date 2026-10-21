"""Check the configured connection and read access; never print credentials."""
import database


def main():
    try:
        database.setup_database("pets")
        print("Connected to MongoDB; pets database is readable.")
        print("Owners:", database.owners_collection.count_documents({}))
        print("Pets:", database.pets_collection.count_documents({}))
    finally:
        database.close_connection()


if __name__ == "__main__":
    main()
