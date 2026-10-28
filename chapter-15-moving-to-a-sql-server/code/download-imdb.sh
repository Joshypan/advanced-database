#!/usr/bin/env bash
set -euo pipefail
mkdir -p data
for name in title.basics title.ratings; do
    if [ ! -s "data/$name.tsv.gz" ]; then
        curl --fail --location --retry 3 "https://datasets.imdbws.com/$name.tsv.gz" -o "data/$name.tsv.gz.partial"
        mv "data/$name.tsv.gz.partial" "data/$name.tsv.gz"
    fi
done
gzip -t data/title.basics.tsv.gz data/title.ratings.tsv.gz
printf '%s\n' 'IMDb compressed inputs ready. Existing files retained.'
