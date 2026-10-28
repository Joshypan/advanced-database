"""Small read-only data layer for the IMDb dashboard."""
import os
import psycopg
from psycopg.rows import dict_row

def query(statement, parameters=()):
    # Each call owns and closes its connection; Streamlit does not share it.
    with psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row) as connection:
        return connection.execute(statement, parameters).fetchall()

def search_titles(text, minimum_votes=1000):
    return query("""
        SELECT t.title_id, t.primary_title, t.start_year,
               r.average_rating, r.num_votes
        FROM imdb_course.titles t LEFT JOIN imdb_course.ratings r USING (title_id)
        WHERE t.primary_title ILIKE %s AND coalesce(r.num_votes, 0) >= %s
        ORDER BY r.num_votes DESC, t.title_id LIMIT 100
    """, ('%'+text.strip()+'%', minimum_votes))

def yearly_summary(minimum_votes=1000):
    return query("""
        SELECT t.start_year, count(*) AS movies,
               round(avg(r.average_rating), 2) AS mean_rating
        FROM imdb_course.titles t JOIN imdb_course.ratings r USING (title_id)
        WHERE t.start_year IS NOT NULL AND r.num_votes >= %s
        GROUP BY t.start_year ORDER BY t.start_year
    """, (minimum_votes,))

def ranked_movies(minimum_votes=1000):
    return query("""
        WITH ranked AS (
            SELECT t.title_id, t.primary_title, t.start_year, r.average_rating, r.num_votes,
                   dense_rank() OVER (
                       PARTITION BY t.start_year
                       ORDER BY r.average_rating DESC
                   ) AS year_rank
            FROM imdb_course.titles t JOIN imdb_course.ratings r USING (title_id)
            WHERE t.start_year IS NOT NULL AND r.num_votes >= %s
        )
        SELECT * FROM ranked WHERE year_rank <= 3
        ORDER BY start_year DESC, year_rank, num_votes DESC, primary_title
        LIMIT 300
    """, (minimum_votes,))

def year_changes(minimum_votes=1000):
    return query("""
        WITH yearly AS (
            SELECT t.start_year, count(*) AS movies
            FROM imdb_course.titles t JOIN imdb_course.ratings r USING (title_id)
            WHERE t.start_year IS NOT NULL AND r.num_votes >= %s
            GROUP BY t.start_year
        )
        SELECT start_year, movies,
               lag(start_year) OVER (ORDER BY start_year) AS previous_year,
               movies - lag(movies) OVER (ORDER BY start_year) AS change,
               sum(movies) OVER (
                   ORDER BY start_year ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS running_total
        FROM yearly ORDER BY start_year
    """, (minimum_votes,))

def sample_summary():
    return query('SELECT count(*) AS titles, min(start_year) AS first_year, max(start_year) AS last_year FROM imdb_course.titles')[0]

def movies_by_year(year, minimum_votes=1000):
    return query("""SELECT t.title_id,t.primary_title,t.start_year,r.average_rating,r.num_votes
        FROM imdb_course.titles t LEFT JOIN imdb_course.ratings r USING(title_id)
        WHERE t.start_year=%s AND coalesce(r.num_votes,0)>=%s
        ORDER BY coalesce(r.num_votes,0) DESC,t.title_id LIMIT 100""",(int(year),minimum_votes))

def movies_by_rating(low, high, minimum_votes=1000):
    if not 0 <= low <= high <= 10:raise ValueError('Choose a rating range from 0 to 10.')
    return query("""SELECT t.title_id,t.primary_title,t.start_year,r.average_rating,r.num_votes
        FROM imdb_course.ratings r JOIN imdb_course.titles t USING(title_id)
        WHERE r.average_rating BETWEEN %s AND %s AND r.num_votes >= %s
        ORDER BY r.average_rating DESC,r.num_votes DESC,t.title_id LIMIT 100""",(low,high,minimum_votes))

def available_years():
    return [row['start_year'] for row in query('SELECT DISTINCT start_year FROM imdb_course.titles WHERE start_year IS NOT NULL ORDER BY start_year')]
