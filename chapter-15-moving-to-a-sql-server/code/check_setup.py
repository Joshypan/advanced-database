"""Check the exercise server, row counts, named indexes and query functions."""
import database

if __name__ == '__main__':
    print(database.query('SELECT current_database() AS database, current_user AS role'))
    for table in ['titles', 'ratings']:
        count = database.query('SELECT count(*) AS count FROM imdb_course.'+table)[0]['count']
        assert count > 0, 'No rows in '+table
        print(table, count)
    indexes = database.query("SELECT indexname FROM pg_indexes WHERE schemaname='imdb_course'")
    names = {r['indexname'] for r in indexes}
    assert {'titles_year_title','titles_primary_title','ratings_votes'} <= names
    print('Indexes:', ', '.join(sorted(names)))
    for function in [database.yearly_summary, database.ranked_movies, database.year_changes]:
        print(function.__name__, len(function(0)), 'rows')
    print('PASS: server, data, indexes and dashboard queries.')
