"""Import prepared CSV files transactionally into the imdb_course schema."""
import argparse
import os
from pathlib import Path
import psycopg

HERE = Path(__file__).resolve().parent

def load(data_dir='data', replace=False):
    paths = [(table, Path(data_dir)/(table+'.csv')) for table in ['titles', 'ratings']]
    for table, path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        exists = connection.execute("SELECT 1 FROM pg_namespace WHERE nspname='imdb_course'").fetchone()
        if exists and not replace:
            raise RuntimeError('imdb_course already exists. Use --replace only to replace this exercise schema.')
        if exists:
            connection.execute('DROP SCHEMA imdb_course CASCADE')
        connection.execute('CREATE SCHEMA imdb_course')
        connection.execute((HERE/'schema.sql').read_text())
        for table, path in paths:
            statement = psycopg.sql.SQL('COPY imdb_course.{} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)').format(psycopg.sql.Identifier(table))
            with path.open('rb') as source, connection.cursor().copy(statement) as target:
                while block := source.read(1024*1024):
                    target.write(block)
        connection.execute((HERE/'indexes.sql').read_text())
        for table, _ in paths:
            count = connection.execute(psycopg.sql.SQL('SELECT count(*) FROM imdb_course.{}').format(psycopg.sql.Identifier(table))).fetchone()[0]
            print(f'{table}: {count:,} rows')
    print('Committed import, indexes and statistics.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default='data')
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    load(args.data_dir, args.replace)
