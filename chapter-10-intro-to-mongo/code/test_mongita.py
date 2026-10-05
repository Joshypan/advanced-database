"""Exercise actual Mongita disk storage, isolated from the lesson data."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from bson.objectid import ObjectId
from lesson import connect, seed


class MongitaLessonTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.client, self.collection = connect(Path(self.folder.name) / "data" / "mongita")
        seed(self.collection)

    def tearDown(self):
        self.client.close()
        self.folder.cleanup()

    def test_seed_preserves_work_and_reset_is_scoped(self):
        self.collection.insert_one({"name": "Student example"})
        other = self.client.hello_world_db.other_collection
        other.insert_one({"keep": True})
        seed(self.collection)
        self.assertEqual(self.collection.count_documents({}), 3)
        seed(self.collection, reset=True)
        self.assertEqual(self.collection.count_documents({}), 2)
        self.assertEqual(other.count_documents({}), 1)

    def test_update_filter_cursor_and_dictionary(self):
        result = self.collection.update_one({"name": "Meercat"}, {"$set": {"weight": 2}})
        self.assertEqual((result.matched_count, result.modified_count), (1, 1))
        cursor = self.collection.find({"weight": {"$gt": 1}})
        saved = list(cursor)
        self.assertEqual([x["name"] for x in saved], ["Meercat"])
        self.assertEqual(list(cursor), [])
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["does_not_eat"], "Snakes")
        self.assertNotIn("weight", self.collection.find_one({"name": "Yellow mongoose"}))
        self.assertIsNone(self.collection.find_one({"weight": {"$gt": 300}}))
        self.assertEqual(list(self.collection.find({"weight": {"$gt": 300}})), [])
        self.assertIn("_id", list(saved[0]))  # Iterating a dictionary yields keys.

    def test_identifier_delete_reinsert(self):
        old = self.collection.find_one({"name": "Meercat"})
        identifier = str(old["_id"])
        self.assertEqual(self.collection.find_one({"_id": ObjectId(identifier)}), old)
        self.collection.update_one({"_id": old["_id"]}, {"$set": {"weight": 2}})
        self.assertEqual(self.collection.delete_one({"_id": old["_id"]}).deleted_count, 1)
        self.assertIsNone(self.collection.find_one({"_id": old["_id"]}))
        new = self.collection.insert_one({"name": "Meercat", "does_not_eat": "Snakes"})
        self.assertNotEqual(new.inserted_id, old["_id"])
        self.assertEqual(list(self.collection.find({"weight": {"$gt": 1}})), [])

    def test_persistence_in_a_new_process(self):
        self.collection.update_one({"name": "Meercat"}, {"$set": {"weight": 7}})
        self.client.close()
        result = subprocess.run([sys.executable, "-c",
            "from lesson import connect; import sys; "
            "c, col = connect(sys.argv[1]); "
            "print(col.find_one({'name': 'Meercat'})['weight']); c.close()",
            str(Path(self.folder.name) / "data" / "mongita")], cwd=Path(__file__).parent, text=True,
            capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), "7")


if __name__ == "__main__":
    unittest.main()
