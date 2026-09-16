"""Run with python3 -m unittest -v test_json_database.py."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from jsonbase import JsonBase
import json_database_layer as database


class JsonDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / "records"

    def test_records_and_reopening(self):
        store = JsonBase(self.folder)
        id = store.create({"name": "O'Malley", "food": "tuna"})
        self.assertEqual(json.loads((self.folder / f"{id}.json").read_text())["food"], "tuna")
        reopened = JsonBase(self.folder)
        self.assertEqual(reopened.get(str(id))["name"], "O'Malley")
        reopened.update(id, {"id": 900, "name": "Changed"})
        self.assertEqual(store.get(id), {"id": id, "name": "Changed"})
        reopened.delete(id)
        self.assertIsNone(store.get(id))
        self.assertEqual(store.get_all(), [])
        self.assertGreater(JsonBase(self.folder).create({"name": "Next"}), id)

    def test_separate_folders_and_missing_records(self):
        first = JsonBase(self.folder)
        second = JsonBase(Path(self.temp.name) / "other")
        first.create({"name": "A"})
        second.update(99, {"name": "Absent"})
        second.delete(99)
        self.assertIsNone(second.get(99))
        self.assertEqual(second.get_all(), [])

    def test_failed_serialization_preserves_record(self):
        store = JsonBase(self.folder)
        id = store.create({"name": "Original"})
        with self.assertRaises(TypeError):
            store.update(id, {"name": object()})
        self.assertEqual(store.get(id)["name"], "Original")

    def test_adapter_and_sqlite_file_preserved(self):
        path = Path(self.temp.name) / "pets.db"
        path.write_bytes(b"leave this file alone")
        database.setup_database(path)
        data = dict(name="Dorothy", type="dog", age="bad", food="kibble", owner="Greg")
        self.assertIsNone(database.create_pet(data))
        pet = database.get_pets()[0]
        self.assertEqual(pet["age"], 0)
        data.update(age="12", food="salmon", owner="Sam")
        self.assertIsNone(database.update_pet(pet["id"], data))
        database.setup_database(path)
        saved = database.get_pet(pet["id"])
        self.assertEqual((saved["age"], saved["food"], saved["owner"]), (12, "salmon", "Sam"))
        self.assertIsNone(database.delete_pet(pet["id"]))
        self.assertIsNone(database.get_pet(pet["id"]))
        self.assertEqual(path.read_bytes(), b"leave this file alone")

    def test_same_app_with_both_backends(self):
        source = Path(__file__).resolve().parent
        for backend in ("database", "json_database_layer"):
            with self.subTest(backend=backend):
                work = Path(self.temp.name) / backend
                work.mkdir()
                for name in ("app.py", "database.py", "jsonbase.py", "json_database_layer.py"):
                    shutil.copy2(source / name, work / name)
                shutil.copytree(source / "templates", work / "templates")
                p = work / "app.py"
                p.write_text(p.read_text().replace("import database\n", f"import {backend} as database\n", 1))
                script = '''import app
c = app.app.test_client()
for path in ('/', '/pets', '/list', '/create'):
    assert c.get(path).status_code == 200
assert c.get('/update').status_code == 400
assert c.get('/update/999').status_code == 404
assert c.post('/update/999', data={}).status_code == 404
data = dict(name="O'Malley", type='cat', age='4', food='tuna', owner='Alex')
assert c.post('/create', data=data).status_code == 302
pet = app.database.get_pets()[0]
assert c.get('/update/'+str(pet['id'])).status_code == 200
assert b'O&#39;Malley' in c.get('/list').data
data.update(food='salmon', owner='Sam', age='5')
assert c.post('/update/'+str(pet['id']), data=data).status_code == 302
saved = app.database.get_pet(pet['id'])
assert (saved['food'], saved['owner'], saved['age']) == ('salmon', 'Sam', 5)
'''
                restart = '''import app
pet = app.database.get_pets()[0]
assert (pet['food'], pet['owner'], pet['age']) == ('salmon', 'Sam', 5)
c = app.app.test_client()
assert c.get('/delete/'+str(pet['id'])).status_code == 302
assert app.database.get_pet(pet['id']) is None
assert app.database.get_pets() == []
'''
                for program in (script, restart):
                    result = subprocess.run([sys.executable, "-B", "-c", program], cwd=work,
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
