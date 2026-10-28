\set ON_ERROR_STOP on
-- One row per movie.
SELECT t.primary_title, t.start_year, r.average_rating, r.num_votes
FROM imdb_course.titles t JOIN imdb_course.ratings r USING (title_id)
WHERE r.num_votes >= 1000 ORDER BY num_votes DESC, title_id LIMIT 20;
-- One row per year.
SELECT t.start_year, count(*) AS movies, round(avg(r.average_rating),2) AS mean_rating
FROM imdb_course.titles t JOIN imdb_course.ratings r USING (title_id)
WHERE t.start_year IS NOT NULL AND r.num_votes >= 1000
GROUP BY t.start_year ORDER BY t.start_year;
-- Movie filter in WHERE; group filter in HAVING.
SELECT t.start_year, count(*) AS movies
FROM imdb_course.titles t JOIN imdb_course.ratings r USING (title_id)
WHERE t.start_year IS NOT NULL AND r.num_votes >= 1000 AND t.runtime_minutes >= 90
GROUP BY t.start_year HAVING count(*) >= 5 ORDER BY t.start_year;
