"""Bootstrap through the localhost exception, then provision scoped users."""
import getpass
import os
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from server import PORT


def password(env, prompt):
    value = os.environ.get(env) or getpass.getpass(prompt)
    if not value:
        raise ValueError('A nonempty password is required.')
    return value


def connect(user, secret, auth_db):
    # Separate arguments avoid URI password-encoding mistakes.
    return MongoClient('127.0.0.1', PORT, username=user, password=secret,
                       authSource=auth_db, directConnection=True,
                       serverSelectionTimeoutMS=5000)


def bootstrap(admin_secret, app_secret, reader_secret):
    with MongoClient('127.0.0.1', PORT, directConnection=True,
                     serverSelectionTimeoutMS=5000) as local:
        try:
            local.admin.command('createUser', 'siteAdmin', pwd=admin_secret,
                                roles=[{'role': 'root', 'db': 'admin'}])
            print('Created the first administrator through the localhost exception.')
        except OperationFailure as error:
            # On a repeat run, the existing admin must authenticate below.
            if error.code not in (13, 51003):
                raise
    with connect('siteAdmin', admin_secret, 'admin') as admin:
        admin.admin.command('connectionStatus')
        for name, secret, role in [('petsApp', app_secret, 'readWrite'),
                                   ('petsReader', reader_secret, 'read')]:
            found = admin.pets_demo.command('usersInfo', name)['users']
            if not found:
                admin.pets_demo.command('createUser', name, pwd=secret,
                                        roles=[{'role': role, 'db': 'pets_demo'}])
                print('Created', name)
            else:
                print('Kept existing', name, '(password unchanged)')
    # Verify provided credentials, including on repeated setup.
    for user, secret in [('petsApp', app_secret), ('petsReader', reader_secret)]:
        with connect(user, secret, 'pets_demo') as client:
            client.pets_demo.pets.find_one()


if __name__ == '__main__':
    bootstrap(password('MONGO_ADMIN_PASSWORD', 'Administrator password: '),
              password('MONGO_APP_PASSWORD', 'Application password: '),
              password('MONGO_READER_PASSWORD', 'Report reader password: '))
    print('Accounts verified. No passwords were written to disk.')
