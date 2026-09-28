#!/usr/bin/env bash
# Build pets.db from create_db.sql. Refuses to touch an existing file.
if [ -e pets.db ]; then
    echo "pets.db already exists. Delete it (and pets.db-shm and pets.db-wal) to rebuild." >&2
    exit 1
fi
sqlite3 pets.db < create_db.sql
