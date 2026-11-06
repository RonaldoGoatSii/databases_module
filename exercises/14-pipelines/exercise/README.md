# Session 14 exercise: aggregation pipelines, backup and restore

## Files

- `pipelines.js`: the four pipelines (tasks 1 to 4), each printed with its document count and its first documents.
- `backup_mongo.sh`: task 5, dumps `pagila_docs` into `backups/` as a compressed archive with a dated name.
- `restore_mongo.sh`: task 5, restores the latest archive into `pagila_docs_restored` and prints the document count of each collection in both databases.
- `backups/`: the archives.

## Prerequisites

The `films` and `rentals` collections must be loaded from a fresh copy of Pagila, as in session 13 (`load.py`), and not changed afterwards. If they were changed, load them again.

The scripts run `mongodump`, `mongorestore` and `mongosh` inside the `mongo` container, using the container's own variables. Check that the tools are there:

```bash
docker compose -f ../../../docker-compose.yml exec -T mongo sh -c 'which mongodump mongorestore mongosh'
```

Three paths should be printed. If `mongodump` or `mongorestore` is missing, the scripts cannot run in this container, and that needs to be solved first (for example, with the MongoDB database tools installed in the image).

## Commands

From `exercises/14-pipelines/exercise`:

```bash
# Tasks 1 to 4
set -a; source ../../13-mongo/exercise/.env; set +a
mongosh "$MONGO_URL" --quiet --file pipelines.js

# Task 5: backup, then restore
bash backup_mongo.sh
bash restore_mongo.sh
```

`set -a; source ...` loads the `MONGO_URL` of the session 13 `.env`, which points to `pagila_docs`.

## Task 1: revenue per category per month, 2025

Output (first 5 of 192 documents):

```
{ category: 'Action', month: '2025-01', revenue: Decimal128('333.87') }
{ category: 'Action', month: '2025-02', revenue: Decimal128('342.98') }
{ category: 'Action', month: '2025-03', revenue: Decimal128('385.83') }
{ category: 'Action', month: '2025-04', revenue: Decimal128('349.91') }
{ category: 'Action', month: '2025-05', revenue: Decimal128('380.76') }
```

Result: 192 documents. `Action` in `2025-01` is `333.87`, as expected.

**Why this value differs from exercise 05 (314.94):** exercise 05 counted the payments by `payment_date`: each payment was attributed to the month in which the money was paid. This pipeline uses `rentals`, where each rental carries the sum of its payments, and attributes the whole amount to the month of `rental_date`: the month in which the film was rented. Money moves between the two months in two ways. A rental made in late December 2024 and paid in January 2025 counts in January in exercise 05 but in December 2024 here, so it is left out of 2025 in this pipeline. A rental made in January 2025 and paid later has its payments counted in January here, whatever the payment date. The totals per category are therefore not the same, and neither is "wrong": they answer different questions (cash received per month, or revenue earned per rental month).

## Task 2: the top actor per category

Output (first 5 of 16 documents):

```
{ category: 'Action', films: 10, actors: [ { actor_id: 181, name: 'MATTHEW CARREY', films: 10 }, { actor_id: 65, name: 'ANGELA HUDSON', films: 10 } ] }
{ category: 'Animation', films: 10, actors: [ { actor_id: 13, name: 'UMA WOOD', films: 10 }, { actor_id: 150, name: 'JAYNE NOLTE', films: 10 } ] }
{ category: 'Children', films: 9, actors: [ { actor_id: 105, name: 'SIDNEY CROWE', films: 9 }, { actor_id: 133, name: 'RICHARD PENN', films: 9 }, { actor_id: 139, name: 'EWAN GOODING', films: 9 } ] }
{ category: 'Classics', films: 10, actors: [ { actor_id: 94, name: 'KENNETH TORN', films: 10 } ] }
{ category: 'Comedy', films: 11, actors: [ { actor_id: 107, name: 'GINA DEGENERES', films: 11 } ] }
```

Result: 16 documents, one per category, with ties included (for example, `Action` has two actors, both with 10 films). The total number of actors across the `actors` arrays is 30, as expected. Check (run with a heredoc, so that the shell does not change the `$` operators):

```bash
docker compose -f ../../../docker-compose.yml exec -T mongo sh -c 'mongosh "mongodb://$MONGO_INITDB_ROOT_USERNAME:$MONGO_INITDB_ROOT_PASSWORD@127.0.0.1:27017/pagila_docs?authSource=admin" --quiet' <<'JS'
print(db.films.aggregate([
  { $unwind: "$categories" },
  { $unwind: "$actors" },
  { $group: { _id: { category: "$categories", actor_id: "$actors.actor_id" }, name: { $first: "$actors.name" }, films: { $sum: 1 } } },
  { $group: { _id: "$_id.category", max: { $max: "$films" }, actors: { $push: { actor_id: "$_id.actor_id", films: "$films" } } } },
  { $project: { actors: { $filter: { input: "$actors", as: "a", cond: { $eq: ["$$a.films", "$max"] } } } } },
  { $unwind: "$actors" },
  { $count: "total" }
]).toArray())
JS
```

Output: `[ { total: 30 } ]`.

## Task 3: the distribution of film lengths

Output:

```
{ _id: 0, count: 96 }
{ _id: 60, count: 224 }
{ _id: 90, count: 214 }
{ _id: 120, count: 216 }
{ _id: 150, count: 250 }
```

Result: 96, 224, 214, 216 and 250, as expected (the buckets are `[0,60)`, `[60,90)`, `[90,120)`, `[120,150)` and `[150,186)`).

## Task 4: the facet summary

Output:

```
totals:    { films: 1000, avg_rate: Decimal128('2.98') }
by_rating: G 178, PG 194, PG-13 223, R 195, NC-17 210
longest:   CHICAGO NORTH, CONTROL ANTHEM, DARN FORRESTER, GANGS PRIDE, HOME PITY (all 185 minutes)
```

Result: 1000 films, average rate 2.98, and the counts per rating and the five longest films match the expected values.

## Task 5: backup and restore

Output of `backup_mongo.sh` (the three collections, with their document counts, and the archive written):

```
writing pagila_docs.rentals, pagila_docs.films, pagila_docs.customers to archive on stdout
done dumping pagila_docs.films (1000 documents)
done dumping pagila_docs.customers (999 documents)
done dumping pagila_docs.rentals (51805 documents)
backup written: backups/pagila_docs_20261106_194247.archive.gz
-rw-r--r-- 1 root root 2.2M Nov  6 19:42 backups/pagila_docs_20261106_194247.archive.gz
```

Output of `restore_mongo.sh` (the document count of each collection in both databases):

```
document counts (collection, pagila_docs, pagila_docs_restored):
customers 999 999
films 1000 1000
rentals 51805 51805
```

Result: the restored database `pagila_docs_restored` has the same document count as `pagila_docs` in every collection.

**Note on the scripts.** The first version of `restore_mongo.sh` was a copy of the backup script, so it dumped again instead of restoring. The correct version restores the latest archive with `mongorestore --nsFrom 'pagila_docs.*' --nsTo 'pagila_docs_restored.*' --drop`. Because `--drop` is used, running the restore again replaces the restored database instead of duplicating its documents.

## Checks

- Each pipeline returns the expected result (tasks 1 to 4 confirmed: task 2 returns 16 documents with 30 actors in total).
- `pagila_docs_restored` has the same document count as `pagila_docs` in every collection (`customers` 999, `films` 1000, `rentals` 51805).