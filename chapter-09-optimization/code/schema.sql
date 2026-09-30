-- Two of the IMDb files, loaded with no secondary indexes yet.
-- tconst is the text identifier IMDb uses for a title, such as tt0000001.
create table titles (
    tconst text primary key,
    title_type text,
    primary_title text,
    original_title text,
    is_adult integer,
    start_year integer,
    end_year integer,
    runtime_minutes integer,
    genres text
);

create table ratings (
    tconst text primary key,
    average_rating real,
    num_votes integer
);
