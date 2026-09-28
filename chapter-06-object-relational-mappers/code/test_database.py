"""Run with python3 -m unittest -v. All writes use temporary databases."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

import database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'pets.db')
        database.initialize(self.path)

    def tearDown(self):
        database.close_connection()
        self.temp.cleanup()

    def pet(self):
        return dict(name="O'Malley", type='cat', age='3', food='salmon')

    def test_crud_and_reopen(self):
        pet_id = database.create_pet(self.pet())
        self.assertEqual(database.get_pet(pet_id)['food'], 'salmon')
        database.update_pet(pet_id, {'name': "O'Malley", 'type': 'cat', 'age': '4', 'food': 'tuna'})
        database.close_connection()
        database.initialize(self.path)
        saved = database.get_pet(pet_id)
        self.assertEqual(saved['age'], 4)
        self.assertEqual(saved['food'], 'tuna')
        # Independent SQLite read confirms that the ORM saved a real table row.
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute('select food from pet where id=?', (pet_id,)).fetchone(), ('tuna',))
        database.delete_pet(pet_id)
        self.assertIsNone(database.get_pet(pet_id))

    def test_queries_and_validation(self):
        for name in ['Zelda', 'Alex', 'Alex']:
            database.create_pet({'name': name, 'type': 'dog', 'age': 'unknown'})
        pets = database.get_pets()
        self.assertEqual([p['name'] for p in pets], ['Alex', 'Alex', 'Zelda'])
        self.assertEqual(pets[0]['age'], 0)
        self.assertLess(pets[0]['id'], pets[1]['id'])
        for values in [{'name': ' ', 'type': 'dog'}, {'name': 'Casey', 'type': ''}]:
            with self.assertRaises(ValueError):
                database.create_pet(values)
        self.assertEqual(len(database.get_pets()), 3)

    def test_unsaved_object_and_explicit_save(self):
        pet = database.Pet(name='Casey', type='dog', food='kibble')
        self.assertEqual(database.get_pets(), [])
        pet.save()
        pet.food = 'chicken'
        self.assertEqual(database.get_pet(pet.id)['food'], 'kibble')
        pet.save()
        self.assertEqual(database.get_pet(pet.id)['food'], 'chicken')

    def test_atomic_rollback(self):
        with self.assertRaises(ValueError):
            with database.db.atomic():
                database.create_pet(self.pet())
                raise ValueError('Cancel the group of writes')
        self.assertEqual(database.get_pets(), [])

    def test_existing_table_gains_food_without_losing_rows(self):
        old_path = str(Path(self.temp.name) / 'older.db')
        with sqlite3.connect(old_path) as connection:
            connection.execute('create table pet (id integer primary key, name text not null, type text not null, age integer not null)')
            connection.execute("insert into pet values (1, 'Casey', 'dog', 9)")
        database.initialize(old_path)
        self.assertEqual(database.get_pet(1)['name'], 'Casey')
        self.assertIsNone(database.get_pet(1)['food'])
        database.initialize(old_path)
        self.assertEqual(len(database.get_pets()), 1)


if __name__ == '__main__':
    unittest.main()
