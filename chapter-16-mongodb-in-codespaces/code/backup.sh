#!/usr/bin/env bash
# Stop application writes before this small standalone logical backup.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data/backups
chmod 700 data/backups
archive="data/backups/pets-$(date -u +%Y%m%dT%H%M%SZ)-$$.archive.gz"
# With a username and no password argument, mongodump prompts interactively.
mongodump --host 127.0.0.1 --port "${MONGO16_PORT:-27117}" \
    --username siteAdmin --authenticationDatabase admin --db pets_demo \
    --archive="$archive" --gzip
printf 'Backup: %s\n' "$archive"
