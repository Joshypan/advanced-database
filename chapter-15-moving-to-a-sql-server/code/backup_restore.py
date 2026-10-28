"""Back up the exercise schema and verify a fresh, separate restore."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import uuid
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo, conninfo_to_dict
uri=os.environ['DATABASE_URL']
restore_db='imdb_restore_'+uuid.uuid4().hex[:10]
folder=Path('.private-backups'); folder.mkdir(mode=0o700,exist_ok=True)
archive=folder/(restore_db+'.dump')
def binary(name):
    found=shutil.which(name)
    if not found: raise RuntimeError('Install PostgreSQL client tools: missing '+name)
    return found

def fingerprint(connection,table):
    digest=hashlib.sha256();count=0
    with connection.cursor(name='backup_check') as cur:
        cur.execute(sql.SQL('SELECT * FROM imdb_course.{} ORDER BY title_id').format(sql.Identifier(table)))
        for row in cur:
            digest.update((repr(row)+'\n').encode());count+=1
    return count,digest.hexdigest()
# Use a private environment variable, rather than putting a connection URI in process arguments.
env=dict(os.environ)
# libpq environment fields are individual values, not an expandable URI.
for key,value in conninfo_to_dict(uri).items():
    env['PG'+('DATABASE' if key=='dbname' else key.upper())]=value
subprocess.run([binary('pg_dump'),'--format=custom','--schema=imdb_course','--file',str(archive)],env=env,check=True)
with psycopg.connect(make_conninfo(uri,dbname='postgres'),autocommit=True) as admin:
    admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(restore_db)))
restore_uri=make_conninfo(uri,dbname=restore_db)
subprocess.run([binary('pg_restore'),'--dbname',restore_db,'--exit-on-error','--single-transaction','--no-owner','--no-privileges',str(archive)],env=dict(env,PGDATABASE=restore_db),check=True)
with psycopg.connect(uri) as source, psycopg.connect(restore_uri) as target:
    tables=['titles','ratings']
    if source.execute("SELECT to_regclass('imdb_course.movie_notes')").fetchone()[0]:tables.append('movie_notes')
    for table in tables:
        original=fingerprint(source,table); restored=fingerprint(target,table)
        assert original==restored,(table,'Restored data differ')
        print('PASS:',table,original[0],'rows, matching content digest')
    index_query="SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='imdb_course' ORDER BY indexname"
    assert source.execute(index_query).fetchall()==target.execute(index_query).fetchall()
    print('PASS: restored index definitions match')
print('Archive:',archive)
print('Restore database:',restore_db)
print('Restore uses the administrative owner; application grants were deliberately omitted.')
print('Original database unchanged. Restore database kept for inspection.')
