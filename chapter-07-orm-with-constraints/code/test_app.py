"""Run with python3 -m unittest -v test_app.py. Uses temporary databases."""
import os
from pathlib import Path
import tempfile
import unittest

# app.py opens pets.db when it is imported, so import it from a scratch folder.
SCRATCH = tempfile.TemporaryDirectory()
HERE = os.getcwd()
os.chdir(SCRATCH.name)
import app
import database
os.chdir(HERE)


class WebLayerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        database.initialize(str(Path(self.temp.name) / "pets.db"))
        self.client = app.app.test_client()
        self.owner_id = database.create_owner({"name": "Alex"})

    def tearDown(self):
        database.close_connection()
        self.temp.cleanup()

    def form(self, **changes):
        values = {"name": "Casey", "type": "dog", "age": "9", "owner_id": str(self.owner_id)}
        values.update(changes)
        return values

    def test_forms_carry_browser_rules(self):
        page = self.client.get("/create").get_data(as_text=True)
        for text in ['name="name" required', 'name="type" required',
                     'type="number" min="0"', 'name="owner_id" required']:
            self.assertIn(text, page)
        self.assertIn('name="name" required', self.client.get("/owner/create").get_data(as_text=True))

    def test_the_route_rejects_bad_forms_with_a_message(self):
        cases = [(dict(name=" "), "name is required"), (dict(type=""), "type is required"),
                 (dict(age="-1"), "age must be a whole number"), (dict(age="abc"), "age must be a whole number"),
                 (dict(owner_id=""), "must select an owner"), (dict(owner_id="x"), "owner_id must be a number")]
        for changes, message in cases:
            with self.subTest(changes=changes):
                response = self.client.post("/create", data=self.form(**changes))
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, response.get_data(as_text=True))
        self.assertEqual(database.get_pets(), [])

    def test_the_route_stops_bad_updates_too(self):
        pet_id = database.create_pet(self.form())
        response = self.client.post(f"/update/{pet_id}", data=self.form(age="-5"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(database.get_pet(pet_id)["age"], 9)

    def test_the_database_still_answers_when_the_route_passes_a_bad_reference(self):
        response = self.client.post("/create", data=self.form(owner_id="999999"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("Constraint error", response.get_data(as_text=True))
        self.assertEqual(database.get_pets(), [])

    def test_a_good_form_is_saved_and_a_blank_age_is_zero(self):
        self.assertEqual(self.client.post("/create", data=self.form(age="")).status_code, 302)
        self.assertEqual(database.get_pets()[0]["age"], 0)

    def test_owner_with_pets_cannot_be_deleted_through_the_route(self):
        pet_id = database.create_pet(self.form())
        response = self.client.get(f"/owner/delete/{self.owner_id}")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Cannot delete this owner", response.get_data(as_text=True))
        self.client.get(f"/delete/{pet_id}")
        self.assertEqual(self.client.get(f"/owner/delete/{self.owner_id}").status_code, 302)

    def test_health_reports_foreign_keys(self):
        self.assertEqual(self.client.get("/health").get_data(as_text=True), "ok")


if __name__ == "__main__":
    unittest.main()
