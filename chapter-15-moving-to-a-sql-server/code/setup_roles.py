"""Create the dashboard login using an administrative DATABASE_URL."""
import os
import psycopg
from psycopg import sql
ROLE = 'imdb_reader'
with psycopg.connect(os.environ['DATABASE_URL']) as conn:
    if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s",(ROLE,)).fetchone():
        conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(ROLE)))
    unsafe=conn.execute('SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls FROM pg_roles WHERE rolname=%s',(ROLE,)).fetchone()[0]
    memberships=conn.execute('SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=%s)',(ROLE,)).fetchone()
    if unsafe or memberships:
        raise RuntimeError('Existing imdb_reader has extra powers or memberships; inspect before reusing it')
    dbname=conn.execute('SELECT current_database()').fetchone()[0]
    conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(dbname),sql.Identifier(ROLE)))
    conn.execute('GRANT USAGE ON SCHEMA imdb_course TO imdb_reader')
    conn.execute('GRANT SELECT ON ALL TABLES IN SCHEMA imdb_course TO imdb_reader')
    conn.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA imdb_course GRANT SELECT ON TABLES TO imdb_reader')
print('imdb_reader can read the existing course tables and future tables created by this owner.')

with psycopg.connect(os.environ['DATABASE_URL']) as conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS imdb_course.movie_notes (
        title_id text PRIMARY KEY REFERENCES imdb_course.titles(title_id),
        note text NOT NULL CHECK (length(btrim(note)) BETWEEN 1 AND 2000))""")
    if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='imdb_writer'").fetchone():
        conn.execute('CREATE ROLE imdb_writer LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
    unsafe=conn.execute("SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls FROM pg_roles WHERE rolname='imdb_writer'").fetchone()[0]
    memberships=conn.execute("SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname='imdb_writer')").fetchone()
    if unsafe or memberships:raise RuntimeError('Existing imdb_writer has unexpected privileges or memberships')
    dbname=conn.execute('SELECT current_database()').fetchone()[0]
    conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO imdb_writer').format(sql.Identifier(dbname)))
    conn.execute('GRANT USAGE ON SCHEMA imdb_course TO imdb_writer')
    conn.execute('GRANT SELECT ON imdb_course.titles,imdb_course.ratings,imdb_course.movie_notes TO imdb_writer')
    conn.execute('GRANT INSERT, UPDATE, DELETE ON imdb_course.movie_notes TO imdb_writer')
    conn.execute('GRANT SELECT ON imdb_course.movie_notes TO imdb_reader')
print('imdb_writer can read IMDb and perform CRUD on movie_notes only.')
