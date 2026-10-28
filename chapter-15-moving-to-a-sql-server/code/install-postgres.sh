#!/usr/bin/env bash
set -euo pipefail
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql postgresql-client libpq-dev python3-venv
psql --version
printf '%s\n' 'Server and client installed. Next: bash start-postgres.sh'
