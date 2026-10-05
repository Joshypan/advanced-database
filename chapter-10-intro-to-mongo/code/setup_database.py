"""Create the two starting documents without overwriting existing work."""
import argparse
from lesson import DATA_DIR, connect, seed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true",
                        help="delete all documents in the lesson collection and reseed it")
    args = parser.parse_args()
    client, collection = connect()
    try:
        seed(collection, reset=args.reset)
        print("Storage:", DATA_DIR)
        print("Documents:", collection.count_documents({}))
    finally:
        client.close()


if __name__ == "__main__":
    main()
