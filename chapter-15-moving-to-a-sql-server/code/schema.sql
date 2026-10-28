CREATE TABLE imdb_course.titles (
    title_id text PRIMARY KEY,
    primary_title text NOT NULL,
    start_year integer,
    runtime_minutes integer,
    genres text
);
CREATE TABLE imdb_course.ratings (
    title_id text PRIMARY KEY REFERENCES imdb_course.titles(title_id),
    average_rating numeric(3,1) NOT NULL,
    num_votes integer NOT NULL CHECK (num_votes >= 0)
);
