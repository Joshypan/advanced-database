"""Transactional connection with rights on movie_notes only."""
import os
import psycopg
from psycopg.rows import dict_row

def connect():
    return psycopg.connect(os.environ['TRANSACTION_DATABASE_URL'],row_factory=dict_row)
def valid(title_id,note):
    title_id=title_id.strip();note=note.strip()
    if not title_id.startswith('tt') or not title_id[2:].isdigit():raise ValueError('Use an IMDb title identifier such as tt0000001.')
    if not note or len(note)>2000:raise ValueError('A note must contain 1 to 2000 characters.')
    return title_id,note

def list_notes():
    with connect() as c:
        return c.execute('SELECT n.title_id,t.primary_title,n.note FROM imdb_course.movie_notes n JOIN imdb_course.titles t USING(title_id) ORDER BY n.title_id').fetchall()
def create_note(title_id,note):
    title_id,note=valid(title_id,note)
    try:
        with connect() as c:c.execute('INSERT INTO imdb_course.movie_notes(title_id,note) VALUES(%s,%s)',(title_id,note))
    except psycopg.errors.UniqueViolation:raise ValueError('That movie already has a note; edit it instead.') from None
    except psycopg.errors.ForeignKeyViolation:raise ValueError('That title is not in the imported sample.') from None
def update_note(title_id,note):
    title_id,note=valid(title_id,note)
    with connect() as c:
        if c.execute('UPDATE imdb_course.movie_notes SET note=%s WHERE title_id=%s',(note,title_id)).rowcount!=1:raise ValueError('Note no longer exists.')
def delete_note(title_id):
    with connect() as c:
        if c.execute('DELETE FROM imdb_course.movie_notes WHERE title_id=%s',(title_id,)).rowcount!=1:raise ValueError('Note no longer exists.')

def get_movie(title_id):
    with connect() as c:
        return c.execute('SELECT title_id,primary_title FROM imdb_course.titles WHERE title_id=%s',(title_id,)).fetchone()
