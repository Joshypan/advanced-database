\set ON_ERROR_STOP on
SELECT current_database(), current_user, version();
SELECT count(*) AS titles FROM imdb_course.titles;
SELECT count(*) AS ratings FROM imdb_course.ratings;
SELECT indexname, indexdef FROM pg_indexes WHERE schemaname='imdb_course';
SELECT start_year AS sample_year FROM imdb_course.titles
 WHERE start_year IS NOT NULL GROUP BY start_year
 ORDER BY count(*) DESC, start_year LIMIT 1 \gset
EXPLAIN (ANALYZE, BUFFERS)
SELECT title_id, primary_title FROM imdb_course.titles
 WHERE start_year = :sample_year ORDER BY primary_title;
