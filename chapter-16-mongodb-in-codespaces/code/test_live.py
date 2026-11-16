"""Start an isolated authenticated server and test real permissions and restart."""
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import unittest
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parent


@unittest.skipUnless(__import__('shutil').which('mongod'), 'mongod must be installed')
class LiveServerTests(unittest.TestCase):
    def test_accounts_permissions_and_restart(self):
        with tempfile.TemporaryDirectory(prefix='mongo16-test-') as folder:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
            env=dict(os.environ, MONGO16_DATA=folder, MONGO16_PORT=str(port),
                     MONGO_ADMIN_PASSWORD=secrets.token_urlsafe(24),
                     MONGO_APP_PASSWORD=secrets.token_urlsafe(24),
                     MONGO_READER_PASSWORD=secrets.token_urlsafe(24))
            def run(*args):
                result=subprocess.run([sys.executable,*args],cwd=ROOT,env=env,
                                      text=True,capture_output=True,timeout=60)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                return result.stdout
            try:
                run('server.py','start')
                run('accounts.py')
                run('demo.py')
                run('accounts.py')  # Repeat setup preserves users and credentials.
                run('server.py','stop')
                run('server.py','start')
                with MongoClient('127.0.0.1',port,username='petsApp',
                                 password=env['MONGO_APP_PASSWORD'],authSource='pets_demo',
                                 serverSelectionTimeoutMS=5000) as client:
                    self.assertEqual(client.pets_demo.pets.count_documents({}),3)
                run('demo.py')  # Rerunning seed does not duplicate records.
            finally:
                run('server.py','stop')

    def test_imdb_search_plans(self):
        """A small imdb database: the search helpers show a scan, then an index scan."""
        import imdb_queries
        with tempfile.TemporaryDirectory(prefix='mongo16-test-') as folder:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
            admin=secrets.token_urlsafe(24)
            env=dict(os.environ, MONGO16_DATA=folder, MONGO16_PORT=str(port),
                     MONGO_ADMIN_PASSWORD=admin,
                     MONGO_APP_PASSWORD=secrets.token_urlsafe(24),
                     MONGO_READER_PASSWORD=secrets.token_urlsafe(24))
            def run(*args):
                result=subprocess.run([sys.executable,*args],cwd=ROOT,env=env,
                                      text=True,capture_output=True,timeout=60)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            try:
                run('server.py','start'); run('accounts.py')
                os.environ['MONGODB_URI']=(f'mongodb://siteAdmin:{admin}@127.0.0.1:{port}'
                                           '/?authSource=admin&directConnection=true')
                client,db=imdb_queries.connect('imdb_test')
                db.titles.insert_many([{'_id':f'tt{i:07d}','primary_title':f'Film {i}',
                                        'title_type':'movie','start_year':1990+i%20}
                                       for i in range(2000)])
                db.ratings.insert_one({'_id':'tt0000007','average_rating':7.5,'num_votes':100})
                query=imdb_queries.build_filter('Film 7')
                rows,work=imdb_queries.search(db,query)
                self.assertIn('COLLSCAN',work['plan'])
                self.assertEqual(work['docs_examined'],2000)
                self.assertEqual((len(rows),rows[0]['average_rating']),(1,7.5))
                imdb_queries.create_title_index(db)
                self.assertTrue(imdb_queries.has_title_index(db))
                rows,work=imdb_queries.search(db,query)
                self.assertIn('IXSCAN',work['plan'])
                self.assertEqual(work['docs_examined'],1)
                imdb_queries.drop_title_index(db)
                self.assertFalse(imdb_queries.has_title_index(db))
                client.close()
            finally:
                os.environ.pop('MONGODB_URI',None)
                run('server.py','stop')


if __name__=='__main__': unittest.main()
