\set ON_ERROR_STOP on
-- Deterministic tie fixture: dense ranks 1,1,2; row numbers 1,2,3.
WITH films(title,rating) AS (VALUES ('Alpha',8.0),('Beta',8.0),('Gamma',7.0))
SELECT title, rating, dense_rank() OVER (ORDER BY rating DESC) AS rating_rank,
 row_number() OVER (ORDER BY rating DESC,title) AS movie_number
FROM films ORDER BY rating DESC,title;
-- Missing-year fixture: changes NULL,-2; totals 3,4.
WITH yearly(year,movies) AS (VALUES (2000,3),(2002,1))
SELECT year,movies,lag(year) OVER (ORDER BY year) AS previous_year,
 movies-lag(movies) OVER (ORDER BY year) AS change,
 sum(movies) OVER (ORDER BY year ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
FROM yearly ORDER BY year;
-- Same ranking operation on imported movies.
WITH ranked AS (
 SELECT t.primary_title,t.start_year,r.average_rating,r.num_votes,
 dense_rank() OVER (PARTITION BY t.start_year ORDER BY r.average_rating DESC) AS year_rank
 FROM imdb_course.titles t JOIN imdb_course.ratings r USING(title_id)
 WHERE t.start_year IS NOT NULL AND r.num_votes>=1000
)
SELECT * FROM ranked WHERE year_rank<=3
ORDER BY start_year DESC,year_rank,num_votes DESC,primary_title LIMIT 100;
-- A movie and the mean of its retained year group.
SELECT t.primary_title,t.start_year,r.average_rating,
 avg(r.average_rating) OVER (PARTITION BY t.start_year) AS year_mean,
 r.average_rating-avg(r.average_rating) OVER (PARTITION BY t.start_year) AS above_year_mean
FROM imdb_course.titles t JOIN imdb_course.ratings r USING(title_id)
WHERE t.start_year IS NOT NULL AND r.num_votes>=1000
ORDER BY t.start_year DESC,t.title_id LIMIT 100;
