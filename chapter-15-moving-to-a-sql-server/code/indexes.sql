CREATE INDEX IF NOT EXISTS titles_year_title
    ON imdb_course.titles (start_year, primary_title);
CREATE INDEX IF NOT EXISTS titles_primary_title
    ON imdb_course.titles (primary_title);
CREATE INDEX IF NOT EXISTS ratings_votes
    ON imdb_course.ratings (num_votes DESC);
ANALYZE imdb_course.titles;
ANALYZE imdb_course.ratings;
