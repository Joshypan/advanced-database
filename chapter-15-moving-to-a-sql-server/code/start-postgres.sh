#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
pg_bin="$(pg_config --bindir)"
pg_data="$PWD/.private-postgres"
mkdir -p "$pg_data"
chmod 700 "$pg_data"
exec 9>"$PWD/.private-postgres-start.lock"
flock 9
if [ ! -f "$pg_data/PG_VERSION" ]; then
    "$pg_bin/initdb" -D "$pg_data" -U student --auth-local=trust --auth-host=trust --encoding=UTF8 --locale=C.UTF-8
    cat >> "$pg_data/postgresql.conf" <<'CONF'
listen_addresses = '127.0.0.1'
port = 5433
unix_socket_directories = '/tmp'
CONF
fi
if ! "$pg_bin/pg_ctl" -D "$pg_data" status >/dev/null 2>&1; then
    # Keep the startup lock in this shell, not in the long-running server.
    "$pg_bin/pg_ctl" -D "$pg_data" -l "$pg_data/server.log" -w start 9>&-
fi
if ! psql 'postgresql://student@127.0.0.1:5433/postgres' -Atc "SELECT 1 FROM pg_database WHERE datname = 'imdb'" | grep -qx 1; then
    createdb -h 127.0.0.1 -p 5433 -U student imdb
fi
psql 'postgresql://student@127.0.0.1:5433/imdb' -c 'SELECT current_database(), current_user;'
