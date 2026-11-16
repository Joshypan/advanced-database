"""Prove permitted data access and denied server administration."""
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from accounts import connect, password
from server import PORT


def expect_denied(operation):
    try:
        operation()
    except OperationFailure as error:
        if error.code != 13:
            raise
        return
    raise AssertionError('Expected Unauthorized (code 13).')


def demonstrate(app_secret, reader_secret):
    with connect('petsApp', app_secret, 'pets_demo') as client:
        pets = client.pets_demo.pets
        for item in [{'_id': 'mochi', 'name': 'Mochi', 'species': 'cat', 'age': 3},
                     {'_id': 'biscuit', 'name': 'Biscuit', 'species': 'dog', 'age': 5},
                     {'_id': 'dot', 'name': 'Dot', 'species': 'rabbit', 'age': 2}]:
            pets.update_one({'_id': item['_id']}, {'$setOnInsert': item}, upsert=True)
        assert pets.count_documents({'_id': {'$in': ['mochi','biscuit','dot']}}) == 3
        expect_denied(lambda: client.admin.command('usersInfo', 1))
        print('Application: demo records readable; server-user administration denied.')
    with connect('petsReader', reader_secret, 'pets_demo') as reader:
        assert reader.pets_demo.pets.find_one({'_id': 'mochi'})
        expect_denied(lambda: reader.pets_demo.pets.update_one(
            {'_id': 'mochi'}, {'$set': {'age': 99}}))
        print('Reader: query allowed; update denied.')
    with MongoClient('127.0.0.1', PORT, directConnection=True,
                     serverSelectionTimeoutMS=5000) as anonymous:
        expect_denied(lambda: anonymous.pets_demo.pets.find_one())
        print('Anonymous: data query denied. A successful ping alone proves no data access.')


if __name__ == '__main__':
    demonstrate(password('MONGO_APP_PASSWORD', 'Application password: '),
                password('MONGO_READER_PASSWORD', 'Report reader password: '))
