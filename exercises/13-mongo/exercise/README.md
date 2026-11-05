# Session 13 exercise: documents from Pagila, operations, validation and indexes

## Files

- `load.py`: reads Pagila from PostgreSQL and writes `films`, `customers` and `rentals` in the `pagila_docs` database.
- `operations.js`: the 8 operations, run in mongosh on freshly loaded collections.
- `validation.js`: the `$jsonSchema` validator on `films`, and the two rejected inserts.
- `index.js`: the explain before and after an index on `actors.actor_id`.
- `pyproject.toml`, `.env.example`: the uv project and the connection variables.

## How to run

From the repository root, on a fresh copy of Pagila:

```bash
./scripts/create-db.sh ex13 --pagila --reset
cd exercises/13-mongo/exercise
cp .env.example .env          # then change the passwords
uv sync
```

Load the three collections (run it twice to check that the result does not change):

```bash
uv run --env-file .env python load.py
uv run --env-file .env python load.py
```

Expected counts: `films: 1000`, `customers: 999`, `rentals: 51805`.

Operations, on freshly loaded collections (the operations change the data, so load again before running them on another copy):

```bash
set -a; source .env; set +a
mongosh "$MONGO_URL" --file operations.js
```

Validation, after the operations (operation 8 must run before the validator is installed):

```bash
mongosh "$MONGO_URL" --file validation.js
```

Index and explain:

```bash
mongosh "$MONGO_URL" --file index.js
```

## Task 1: what is embedded and what is referenced

**Actors and categories are embedded in `films`.** A film is read together with its actors and its categories almost every time (the film page, the catalogue). The lists are small and bounded (a film has a few actors and a few categories), and they change rarely. Embedding gives one read per film, with no joins. The cost is that an actor's name is copied into every film it appears in; if an actor is renamed, every film must be updated.

**Only the last 10 rentals are embedded in `customers`.** The customer screen usually shows the latest rentals, so 10 are enough for the common case. Embedding the whole history would make a customer document grow without limit (a customer with thousands of rentals would produce a very large document, close to MongoDB's 16 MB limit), and every new rental would rewrite it. Keeping only 10, with `$push` and `$slice` (operation 7), keeps the document a fixed size.

**The full history is in `rentals`, as one document per rental.** Rentals are unbounded and are queried in many ways (by customer, by film, by date, by store). A separate collection lets each query use its own index, and it avoids the unbounded growth described above. The rental refers to its customer and film by id, so the same film is not copied into the customer document. A few fields are copied on purpose (`title`, `categories`, `store_id`), so that the common reads do not need a second query.

## Task 2: the 8 operations

Output of `operations.js`, run on freshly loaded collections (the `TEST FILM` from an earlier run was removed and `load.py` was run again first):

```
1 PG-13 > 120 min: 118
2 actor 1: 19
3 Horror at 0.99: 43
4 unreturned in recent: 56
5 customer 1 projection: {"documents":1,"titles":10}
6 NC-17 < 60 min: {"matched":21,"modified":21}
7 recent_rentals size and first: {"size":10,"first":99999}
8 first run: {"acknowledged":true,"insertedId":1001,"matchedCount":0,"modifiedCount":0,"upsertedCount":1}
8 second run: {"acknowledged":true,"insertedId":null,"matchedCount":1,"modifiedCount":0,"upsertedCount":0}
```

| # | Operation | Expected | Result |
|---|---|---|---|
| 1 | films rated PG-13 and longer than 120 minutes | 118 | 118 |
| 2 | films with actor 1 | 19 | 19 |
| 3 | Horror films at rental rate 0.99 | 43 | 43 |
| 4 | customers with an unreturned rental in `recent_rentals` | 56 | 56 |
| 5 | customer 1, names and recent titles only | 1 document, 10 titles | 1 document, 10 titles |
| 6 | NC-17 films shorter than 60 minutes, `$inc` 0.50 | 21 modified | 21 modified |
| 7 | push a rental to customer 1's `recent_rentals`, keep 10 | 10 items, new one first | 10 items, first `99999` |
| 8a | upsert TEST FILM, first run | upserted 1 | upserted 1 (`_id` 1001) |
| 8b | upsert TEST FILM, second run | matched 1, modified 0 | matched 1, modified 0 |

Note: operations 6 and 7 change data, so they are only reproducible on freshly loaded collections. A second run without reloading gives different counts for operation 6 (the rates rise again) and adds another rental in operation 7.

## Task 3: validation

Output of `validation.js`:

```
validator installed on films
rejected rating XXX: Document failed validation
rejected length "long": Document failed validation
valid document accepted
```

- Rejected document with `rating: "XXX"`: `Document failed validation` (the rule is `rating` must be one of G, PG, PG-13, R, NC-17).
- Rejected document with `length: "long"`: `Document failed validation` (the rule is `length` must be an integer between 1 and 999).
- A valid document with the same fields was accepted, and then deleted by the script.

## Task 4: index and explain

Output of `index.js`, with the index dropped first so that the baseline is a collection scan:

```
before index: {"stage":"COLLSCAN","totalDocsExamined":1000,"nReturned":19}
after index: {"stage":"IXSCAN","totalDocsExamined":19,"nReturned":19}
plan changed from COLLSCAN to IXSCAN; examined 1000 -> 19
```

| Measure | Before index | After index |
|---|---|---|
| Stage | COLLSCAN | IXSCAN (under FETCH) |
| totalDocsExamined | 1000 | 19 |
| nReturned | 19 | 19 |

**Explanation:** without an index, MongoDB reads all 1000 film documents and checks the `actors` array of each one. With the index on `actors.actor_id` (a multikey index, because `actors` is an array), it finds the 19 index entries for actor 1 and reads only those 19 documents. The result is the same, but the work drops from 1000 documents to 19.

## Checks

- After `load.py`: `films` 1000, `customers` 999, `rentals` 51805 (confirmed).
- The second run of `load.py` leaves the same counts (`films` 1000, `customers` 999, `rentals` 51805): confirmed.
- Operations 1 to 8 give the expected values on freshly loaded collections (confirmed).
- Both invalid documents are rejected with `Document failed validation` (confirmed).
- The plan changes from COLLSCAN to IXSCAN, and the documents examined go from 1000 to 19 (confirmed).