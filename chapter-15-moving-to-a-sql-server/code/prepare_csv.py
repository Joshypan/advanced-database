"""Convert local IMDb TSV archives to portable movie/ratings CSV files."""
import argparse
import csv
import gzip
from pathlib import Path


def prepare(data_dir, limit=100000, start_year=None, end_year=None):
    if limit < 0:
        raise ValueError('limit must be nonnegative; zero means all movies')
    if start_year is not None and end_year is not None and start_year > end_year:
        raise ValueError('start year must not exceed end year')
    data_dir = Path(data_dir)
    for name in ['title.basics.tsv.gz', 'title.ratings.tsv.gz']:
        if not (data_dir/name).is_file():
            raise FileNotFoundError(data_dir/name)
    ids = set()
    with gzip.open(data_dir/'title.basics.tsv.gz', 'rt', encoding='utf-8', newline='') as source, (data_dir/'titles.csv').open('w', encoding='utf-8', newline='') as target:
        reader = csv.DictReader(source, delimiter='\t', quoting=csv.QUOTE_NONE)
        writer = csv.writer(target)
        writer.writerow(['title_id', 'primary_title', 'start_year', 'runtime_minutes', 'genres'])
        for row in reader:
            if row['titleType'] != 'movie' or row['isAdult'] != '0':
                continue
            year = None if row['startYear'] == r'\N' else int(row['startYear'])
            if start_year is not None and (year is None or year < start_year):
                continue
            if end_year is not None and (year is None or year > end_year):
                continue
            ids.add(row['tconst'])
            writer.writerow([row['tconst'], row['primaryTitle'], '' if row['startYear'] == r'\N' else row['startYear'], '' if row['runtimeMinutes'] == r'\N' else row['runtimeMinutes'], '' if row['genres'] == r'\N' else row['genres']])
            if limit and len(ids) >= limit:
                break
    ratings = 0
    with gzip.open(data_dir/'title.ratings.tsv.gz', 'rt', encoding='utf-8', newline='') as source, (data_dir/'ratings.csv').open('w', encoding='utf-8', newline='') as target:
        reader = csv.DictReader(source, delimiter='\t', quoting=csv.QUOTE_NONE)
        writer = csv.writer(target)
        writer.writerow(['title_id', 'average_rating', 'num_votes'])
        for row in reader:
            if row['tconst'] in ids:
                writer.writerow([row['tconst'], row['averageRating'], row['numVotes']])
                ratings += 1
    print(f'Prepared {len(ids):,} movies and {ratings:,} matching ratings.')
    return len(ids), ratings

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default='data')
    parser.add_argument('--limit', type=int, default=0, help='maximum movies; 0 loads all eligible movies')
    parser.add_argument('--start-year', type=int, default=1975)
    parser.add_argument('--end-year', type=int, default=1999)
    args = parser.parse_args()
    prepare(args.data_dir, args.limit, args.start_year, args.end_year)
