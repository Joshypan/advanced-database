"""Test the real database and Streamlit forms in temporary storage."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import database


class PetsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"PETS_DATABASE": str(Path(self.temp.name) / "pets.db")})
        self.env.start()
        database.initialize()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def app(self):
        at = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=20).run()
        self.assertFalse(at.exception)
        return at

    def button(self, at, label):
        next(x for x in at.button if x.label == label).click().run()
        self.assertFalse(at.exception)

    def test_hello_world_counter(self):
        path = str(Path(__file__).with_name("hello_world.py"))
        at = AppTest.from_file(path).run()
        self.assertEqual(at.session_state["count"], 0)
        for expected in (1, 2, 3):
            at.button[0].click().run()
            self.assertEqual(at.session_state["count"], expected)
        at.run()
        self.assertEqual(at.session_state["count"], 3)
        fresh = AppTest.from_file(path).run()
        self.assertEqual(fresh.session_state["count"], 0)
        self.assertFalse(at.exception)

    def test_database_rules_and_persistence(self):
        self.assertTrue(database.seed_demo())
        self.assertFalse(database.seed_demo())
        pet = database.get_pets()[0]
        owner = pet["owner_id"]
        with self.assertRaises(database.ConstraintError):
            database.delete_owner(owner)
        with self.assertRaises(database.ConstraintError):
            database.create_pet(dict(pet, owner_id=99999))
        with self.assertRaises(ValueError):
            database.create_pet(dict(pet, age=-1))
        database.update_pet(pet["id"], dict(pet, food="Rice", age=4))
        database.initialize()
        self.assertEqual(database.get_pet(pet["id"])["food"], "Rice")
        database.delete_pet(pet["id"])
        database.delete_owner(owner)
        self.assertIsNone(database.get_owner(owner))

    def test_ui_create_update_delete_pet(self):
        database.seed_demo()
        at = self.app()
        at.sidebar.radio[1].set_value("Add").run()
        at.text_input(key="pet_new_name").set_value("Milo")
        at.text_input(key="pet_new_type").set_value("Cat")
        at.text_input(key="pet_new_food").set_value("Fish")
        at.number_input(key="pet_new_age").set_value(2)
        self.button(at, "Save pet")
        pet = next(x for x in database.get_pets() if x["name"] == "Milo")
        at.run()  # A normal rerun must not insert another row.
        self.assertEqual(len(database.get_pets()), 3)
        at.sidebar.radio[1].set_value("Edit").run()
        at.selectbox(key="Pets_selected").set_value(pet["id"]).run()
        self.assertEqual(at.text_input(key=f"pet_{pet['id']}_name").value, "Milo")
        at.text_input(key=f"pet_{pet['id']}_food").set_value("Chicken")
        owners = database.get_owners()
        at.selectbox(key=f"pet_{pet['id']}_owner").set_value(owners[1]["id"])
        self.button(at, "Save pet")
        updated = database.get_pet(pet["id"])
        self.assertEqual(updated["food"], "Chicken")
        self.assertEqual(updated["owner_id"], owners[1]["id"])
        at.sidebar.radio[1].set_value("Delete").run()
        self.assertTrue(next(x for x in at.button if x.label == "Delete record").disabled)
        at.checkbox[0].check().run()
        self.button(at, "Delete record")
        self.assertIsNone(database.get_pet(pet["id"]))

    def test_ui_owners_validation_and_restriction(self):
        at = self.app()
        at.sidebar.radio[1].set_value("Add").run()
        self.assertTrue(any("Add an owner" in x.value for x in at.info))
        at.sidebar.radio[0].set_value("Owners").run()
        self.button(at, "Save owner")
        self.assertTrue(at.error)
        at.text_input(key="owner_new_name").set_value("Robin")
        self.button(at, "Save owner")
        owner = database.get_owners()[0]
        at.sidebar.radio[1].set_value("Edit").run()
        at.text_input(key=f"owner_{owner['id']}_city").set_value("Kent")
        self.button(at, "Save owner")
        self.assertEqual(database.get_owner(owner["id"])["city"], "Kent")
        pet = database.create_pet({"name": "Spot", "type": "Dog", "age": 1,
                                   "food": "Kibble", "owner_id": owner["id"]})
        at.sidebar.radio[1].set_value("Delete").run()
        at.checkbox[0].check().run()
        self.button(at, "Delete record")
        self.assertTrue(at.error)
        self.assertIsNotNone(database.get_owner(owner["id"]))
        database.delete_pet(pet)
        self.button(at, "Delete record")
        self.assertEqual(database.get_owners(), [])


if __name__ == "__main__":
    unittest.main()
