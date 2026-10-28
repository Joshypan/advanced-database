"""Exercise the live sandbox UI and permission boundaries; requires a clean first-title note."""
import os,sys
from pathlib import Path
from streamlit.testing.v1 import AppTest
import notes_store
kind='postgres'
if kind=='postgres':
 import psycopg
 from psycopg.conninfo import make_conninfo
 import database
 title=database.query('SELECT title_id FROM imdb_course.titles ORDER BY title_id LIMIT 1')[0]['title_id']
else:
 from database import database
 with database() as db:title=db.titles.find_one(sort=[('_id',1)])['_id']
assert not any(r['title_id']==title for r in notes_store.list_notes()),'Fixture title already has a note'
try:
 app=AppTest.from_file(str(Path('app.py').resolve())).run(timeout=60);assert not app.exception
 app.radio[0].set_value('Notes').run();assert not app.exception
 app.text_input[0].set_value(title);app.text_area[0].set_value('First note')
 next(b for b in app.button if b.label=='Create note').click().run()
 assert not app.exception
 assert next(r for r in notes_store.list_notes() if r['title_id']==title)['note']=='First note'
 try:notes_store.create_note(title,'Duplicate')
 except ValueError:pass
 else:raise AssertionError('Duplicate was accepted')
 app.text_area[1].set_value('Revised note')
 next(b for b in app.button if b.label=='Update note').click().run()
 assert not app.exception
 assert next(r for r in notes_store.list_notes() if r['title_id']==title)['note']=='Revised note'
 # A reader must not modify movie_notes; a writer must not modify imported titles.
 if kind=='postgres':
  for uri,statement in [(os.environ['DATABASE_URL'],'UPDATE imdb_course.movie_notes SET note=note WHERE false'),(os.environ['TRANSACTION_DATABASE_URL'],'UPDATE imdb_course.titles SET primary_title=primary_title WHERE false'),(os.environ['TRANSACTION_DATABASE_URL'],'CREATE ROLE denied_writer_probe NOLOGIN')]:
   with psycopg.connect(uri) as c:
    try:c.execute(statement)
    except psycopg.errors.InsufficientPrivilege:pass
    else:raise AssertionError('Unexpected PostgreSQL write/admin privilege')
    finally:c.rollback()
 else:
  from connection import uri
  from pymongo import MongoClient
  from pymongo.errors import OperationFailure
  for access,collection in [('reader','movie_notes'),('writer','titles')]:
   with MongoClient(uri(access)) as c:
    try:c.imdb_course[collection].update_one({'_id':'__nonexistent_probe__'},{'$set':{'probe':True}})
    except OperationFailure as e:assert e.code==13
    else:raise AssertionError('Unexpected MongoDB write privilege')
  with MongoClient(uri('writer')) as c:
   try:c.admin.command('usersInfo',1)
   except OperationFailure as e:assert e.code==13
   else:raise AssertionError('Unexpected MongoDB admin privilege')
 app.checkbox[0].check().run()
 next(b for b in app.button if b.label=='Delete note').click().run()
 assert not app.exception
 assert not any(r['title_id']==title for r in notes_store.list_notes())
 print(kind+': UI create/read/update/delete, duplicate rejection, reader denial and writer scope all passed')
finally:
 if any(r['title_id']==title for r in notes_store.list_notes()):notes_store.delete_note(title)
