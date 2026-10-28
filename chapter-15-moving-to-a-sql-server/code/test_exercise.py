"""Run against a disposable database: TEST_DATABASE_URL must name *_test."""
import csv
import gzip
import os
from pathlib import Path

import psycopg
import pytest
import database
import import_imdb
from prepare_csv import prepare


def test_prepare_csv_handles_quotes_missing_values_and_matching_ratings(tmp_path):
    with gzip.open(tmp_path/'title.basics.tsv.gz', 'wt') as f:
        f.write('tconst\ttitleType\tprimaryTitle\toriginalTitle\tisAdult\tstartYear\tendYear\truntimeMinutes\tgenres\n')
        f.write('tt1\tmovie\tA, "Movie"\tA\t0\t2000\t\\N\t\\N\tDrama\n')
        f.write('tt2\ttvSeries\tSeries\tSeries\t0\t2001\t\\N\t30\tComedy\n')
        f.write('tt3\tmovie\tOther\tOther\t0\t2002\t\\N\t90\tDrama\n')
    with gzip.open(tmp_path/'title.ratings.tsv.gz', 'wt') as f:
        f.write('tconst\taverageRating\tnumVotes\ntt1\t8.0\t2000\ntt2\t7.0\t900\ntt3\t9.0\t3000\n')
    assert prepare(tmp_path, 1) == (1, 1)
    rows = list(csv.DictReader((tmp_path/'titles.csv').open()))
    assert rows[0]['primary_title'] == 'A, "Movie"'
    assert rows[0]['runtime_minutes'] == ''
    assert prepare(tmp_path, 0, 2000, 2000) == (1, 1)
    with pytest.raises(ValueError):
        prepare(tmp_path, 0, 2002, 2000)
    with pytest.raises(ValueError):
        prepare(tmp_path, -1)


def test_import_queries_and_streamlit(tmp_path, monkeypatch):
    uri = os.environ.get('TEST_DATABASE_URL')
    if not uri:
        pytest.skip('Set TEST_DATABASE_URL to a disposable database ending in _test')
    with psycopg.connect(uri, autocommit=True) as c:
        assert c.execute('SELECT current_database()').fetchone()[0].endswith('_test')
        assert c.execute("SELECT 1 FROM pg_namespace WHERE nspname='imdb_course'").fetchone() is None
    monkeypatch.setenv('DATABASE_URL', uri)
    (tmp_path/'titles.csv').write_text('title_id,primary_title,start_year,runtime_minutes,genres\na,Alpha,2000,90,Drama\nb,Beta,2000,100,Drama\nc,Gamma,2000,110,Comedy\nd,Delta,2002,,Drama\ne,Unrated Movie,2003,95,Drama\n')
    (tmp_path/'ratings.csv').write_text('title_id,average_rating,num_votes\na,8.0,2000\nb,8.0,3000\nc,7.0,4000\nd,9.0,5000\n')
    try:
        import_imdb.load(tmp_path)
        with pytest.raises(RuntimeError):
            import_imdb.load(tmp_path)
        assert len(database.search_titles('', 0)) == 5
        assert database.search_titles("' OR 1=1 --", 0) == []
        assert database.search_titles('  unrated  ', 0)[0]['primary_title'] == 'Unrated Movie'
        assert database.search_titles('Unrated', 1) == []
        assert len(database.movies_by_year(2000,0)) == 3
        assert len(database.movies_by_rating(8.0,8.0,0)) == 2
        with pytest.raises(ValueError):database.movies_by_rating(9.0,8.0,0)
        years = database.yearly_summary(0)
        assert [r['movies'] for r in years] == [3, 1]
        ranks = {r['primary_title']: r['year_rank'] for r in database.ranked_movies(0)}
        assert ranks == {'Alpha': 1, 'Beta': 1, 'Gamma': 2, 'Delta': 1}
        changes = database.year_changes(0)
        assert changes[0]['change'] is None
        assert changes[1]['previous_year'] == 2000
        assert changes[1]['change'] == -2
        assert changes[1]['running_total'] == 4
        (tmp_path/'ratings.csv').write_text('title_id,average_rating,num_votes\nmissing,9.0,5\n')
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            import_imdb.load(tmp_path, replace=True)
        assert len(database.search_titles('', 0)) == 5  # replacement rolled back
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run(timeout=30)
        assert not app.exception
        assert not app.error
        assert [t.label for t in app.tabs] == ['By Name','By Year','By Rating']
        assert len(app.dataframe) == 3
        app.radio[0].set_value('Reports').run()
        assert not app.exception
        assert len(app.get('vega_lite_chart')) == 4
    finally:
        with psycopg.connect(uri, autocommit=True) as c:
            c.execute('DROP SCHEMA IF EXISTS imdb_course CASCADE')
