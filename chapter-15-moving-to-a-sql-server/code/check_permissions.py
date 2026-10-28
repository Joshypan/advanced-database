"""Exercise actual allowed and denied operations; roll back every test."""
import os
import psycopg
from psycopg.conninfo import make_conninfo
uri=make_conninfo(os.environ['DATABASE_URL'],user='imdb_reader')
with psycopg.connect(uri) as conn:
    assert conn.execute('SELECT current_user').fetchone()[0]=='imdb_reader'
    assert conn.execute('SELECT count(*) FROM imdb_course.titles').fetchone()[0]>0
    print('PASS: dashboard login can read titles')
    conn.rollback()
    statements=[('UPDATE imdb_course.titles SET primary_title=primary_title WHERE false','update titles'),('CREATE ROLE imdb_permission_probe NOLOGIN','create a role')]
    for statement,label in statements:
        try:
            conn.execute(statement)
        except psycopg.errors.InsufficientPrivilege:
            print('PASS: denied '+label)
        else:
            raise AssertionError('Unexpected permission: '+label)
        finally:
            conn.rollback()
