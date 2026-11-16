#!/usr/bin/env bash
# Restore only into the separate pets_restore database. Never drop live data.
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$#" != 1 || ! -f "$1" ]]; then
    echo 'Usage: bash restore.sh data/backups/<archive>.archive.gz' >&2
    exit 1
fi
mongorestore --host 127.0.0.1 --port "${MONGO16_PORT:-27117}" \
    --username siteAdmin --authenticationDatabase admin \
    --archive="$1" --gzip --nsInclude='pets_demo.*' \
    --nsFrom='pets_demo.*' --nsTo='pets_restore.*' --stopOnError
