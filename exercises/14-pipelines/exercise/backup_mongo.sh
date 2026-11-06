#!/usr/bin/env bash
# Dumps pagila_docs into backups/ as a compressed archive with a dated name.
# Runs mongodump inside the mongo container (credentials come from the container's own variables).
# Usage: bash backup_mongo.sh
set -euo pipefail

cd "$(dirname "$0")"
COMPOSE_FILE="$(cd ../../.. && pwd)/docker-compose.yml"
mkdir -p backups

STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT="backups/pagila_docs_${STAMP}.archive.gz"

docker compose -f "$COMPOSE_FILE" exec -T mongo sh -c \
  'mongodump --uri "mongodb://$MONGO_INITDB_ROOT_USERNAME:$MONGO_INITDB_ROOT_PASSWORD@127.0.0.1:27017/?authSource=admin" --db pagila_docs --archive --gzip' \
  > "$OUT"

if [ ! -s "$OUT" ]; then
  echo "backup failed: $OUT is empty" >&2
  exit 1
fi
echo "backup written: $OUT"
ls -lh "$OUT"