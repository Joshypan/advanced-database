"""Run with python3 -m unittest -v. Every test uses a temporary database."""
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SCHEMA = (HERE / "create_db.sql").read_text()

# app.py connects when it is imported, so point it at a scratch file first.
SCRATCH = tempfile.TemporaryDirectory()
os.environ["PETS_DATABASE_URL"] = f"sqlite:///{SCRATCH.name}/import.db"
os.chdir(HERE)
import app  # noqa: E402

app.db.close()


class PetsAppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "pets.db"
        with sqlite3.connect(self.path) as connection:
            connection.executescript(SCHEMA)
        import dataset
        app.db = dataset.connect(
            f"sqlite:///{self.path}", on_connect_statements=["PRAGMA foreign_keys=ON"])
        self.addCleanup(app.db.close)
        self.client = app.app.test_client()

    def form(self, **changes):
        values = {"name": "Casey", "age": "9", "owner": "Greg", "kind_id": "1"}
        values.update(changes)
        return values

    def pets(self):
        return list(app.db["pets"].all())

    def test_list_shows_the_joined_kind_information(self):
        page = self.client.get("/list").get_data(as_text=True)
        self.assertIn("Suzy", page)
        self.assertIn("Dog food", page)

    def test_a_good_form_is_saved(self):
        before = len(self.pets())
        self.assertEqual(self.client.post("/create", data=self.form()).status_code, 302)
        self.assertEqual(len(self.pets()), before + 1)

    def test_the_route_rejects_bad_forms_with_a_message(self):
        before = len(self.pets())
        cases = [(dict(name=" "), "name is required"),
                 (dict(age="-1"), "age must be a whole number"),
                 (dict(age="abc"), "age must be a whole number"),
                 (dict(age=""), "age must be a whole number"),
                 (dict(owner=""), "owner is required"),
                 (dict(kind_id="x"), "choose a kind")]
        for changes, message in cases:
            with self.subTest(changes=changes):
                response = self.client.post("/create", data=self.form(**changes))
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, response.get_data(as_text=True))
        self.assertEqual(len(self.pets()), before)

    def test_the_database_refuses_an_unknown_kind_when_the_route_passes_it_on(self):
        response = self.client.post("/create", data=self.form(kind_id="999"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("FOREIGN KEY", response.get_data(as_text=True))

    def test_update_and_delete(self):
        pet_id = app.db["pets"].find_one(name="Suzy")["id"]
        self.assertEqual(self.client.post(f"/update/{pet_id}", data=self.form(name="Suzy Q")).status_code, 302)
        self.assertEqual(app.db["pets"].find_one(id=pet_id)["name"], "Suzy Q")
        self.assertEqual(self.client.post(f"/update/{pet_id}", data=self.form(age="-5")).status_code, 400)
        self.assertEqual(app.db["pets"].find_one(id=pet_id)["age"], 9)
        self.client.get(f"/delete/{pet_id}")
        self.assertIsNone(app.db["pets"].find_one(id=pet_id))
        self.assertEqual(self.client.get("/update/9999").status_code, 404)

    def test_a_kind_that_pets_use_cannot_be_deleted(self):
        response = self.client.get("/kind/delete/1")
        self.assertEqual(response.status_code, 400)
        self.assertIn("pets use it", response.get_data(as_text=True))
        self.assertIsNotNone(app.db["kind"].find_one(id=1))
        for pet in self.pets():
            if pet["kind_id"] == 1:
                app.db["pets"].delete(id=pet["id"])
        self.assertEqual(self.client.get("/kind/delete/1").status_code, 302)

    def test_kind_forms_need_every_field(self):
        response = self.client.post("/kind/create", data={"kind_name": "Bird", "food": "", "noise": "Tweet"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post(
            "/kind/create", data={"kind_name": "Bird", "food": "Seed", "noise": "Tweet"}).status_code, 302)

    def test_health_reports_foreign_keys(self):
        self.assertEqual(self.client.get("/health").get_data(as_text=True), "ok")


if __name__ == "__main__":
    unittest.main()
