#!/usr/bin/env bash
# Install binaries only. The lab's Python controller starts its own server.
set -euo pipefail
. /etc/os-release
if [[ "$ID" != ubuntu || ( "$VERSION_CODENAME" != jammy && "$VERSION_CODENAME" != noble ) ]]; then
    echo "This walkthrough supports Ubuntu 22.04/jammy or 24.04/noble." >&2
    exit 1
fi
if [[ "$(dpkg --print-architecture)" != amd64 ]]; then
    echo "This course installer targets amd64. Consult MongoDB's platform guide for other architectures." >&2
    exit 1
fi
if [[ "$EUID" -eq 0 ]]; then SUDO=(); else SUDO=(sudo); fi
"${SUDO[@]}" apt-get update
"${SUDO[@]}" apt-get install -y curl gnupg
curl -fsSL https://pgp.mongodb.com/server-8.0.asc | \
    "${SUDO[@]}" gpg --batch --yes --dearmor -o /usr/share/keyrings/mongodb-server-8.0.gpg
printf 'deb [arch=amd64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg] https://repo.mongodb.org/apt/ubuntu %s/mongodb-org/8.0 multiverse\n' "$VERSION_CODENAME" | \
    "${SUDO[@]}" tee /etc/apt/sources.list.d/mongodb-org-8.0.list >/dev/null
"${SUDO[@]}" apt-get update
"${SUDO[@]}" apt-get install -y mongodb-org-server mongodb-org-mongos mongodb-mongosh mongodb-database-tools
mongod --version
mongosh --version
mongodump --version
