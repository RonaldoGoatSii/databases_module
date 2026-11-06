#!/usr/bin/env bash
# Restores the latest archive in backups/ into pagila_docs_restored, then prints the document count
# of every collection in pagila_docs and pagila_docs_restored.
# Usage: bash restore_mongo.sh
set -euo pipefail

cd "$(dirname "$0")"
COMPOSE_FILE="$(cd ../../.. && pwd)/docker-compose.yml"

LATEST="$(ls -t backups/pagila_docs_*.archive.gz | head -1)"
echo "restoring: $LATEST"

docker compose -f "$COMPOSE_FILE" exec -T mongo sh -c \
  'mongorestore --uri "mongodb://$MONGO_INITDB_ROOT_USERNAME:$MONGO_INITDB_ROOT_PASSWORD@127.0.0.1:27017/?authSource=admin" --archive --gzip --nsFrom "pagila_docs.*" --nsTo "pagila_docs_restored.*" --drop' \
  < "$LATEST"

echo
echo "document counts (collection, pagila_docs, pagila_docs_restored):"
docker compose -f "$COMPOSE_FILE" exec -T mongo sh -c \
  'mongosh "mongodb://$MONGO_INITDB_ROOT_USERNAME:$MONGO_INITDB_ROOT_PASSWORD@127.0.0.1:27017/?authSource=admin" --quiet' <<'JS'
const original = db.getSiblingDB("pagila_docs");
const restored = db.getSiblingDB("pagila_docs_restored");
original.getCollectionNames().sort().forEach((name) => {
  print(name, original[name].countDocuments({}), restored[name].countDocuments({}));
});
JS