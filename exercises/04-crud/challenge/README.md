# Session 04 challenge: reproducible bulk load

## Files

- `seed.py`: adds 1,000,000 rows to `rental` with `COPY`. The database name is a command-line argument.
- `pyproject.toml`: the uv project (`psycopg` and `faker`, with `package = false`, since this is a script and not an installable package).

## Design decisions

- **Explicit IDs** from 100,001 to 1,100,000, so both databases get the same keys. After the load, `setval` moves the sequence past the last ID.
- **Fixed seed** (`random.Random(42)`) and reference lists ordered by ID, so the same choices are made on every run.
- **Valid references.** `inventory_id`, `customer_id` and `staff_id` are taken from the tables that exist in Pagila.
- **Dates.** `rental_date` is uniform between 2022-01-01 and 2026-07-31. `return_date` is NULL for about 10% of rows, and otherwise between 1 hour and 13 days after the rental.
- **Idempotency.** Before loading, the script counts the rows in the ID range. If all 1,000,000 exist, it does nothing. If some exist but not all, it stops, so that a partial load is never mixed with a new one.
- **`faker` is listed but not used.** Generating 1,000,000 rows with Faker would be much slower than the random module, and the rows only need valid values, not realistic names.

## How to run

Start from two fresh copies of Pagila, from the repository root:

```bash
./scripts/create-db.sh ch04_a --pagila --reset
./scripts/create-db.sh ch04_b --pagila --reset
```

Install the dependencies and run the load on each database, timing each run:

```bash
cd exercises/04-crud/challenge
uv sync
time uv run --env-file ../../../.env python seed.py ch04_a
time uv run --env-file ../../../.env python seed.py ch04_b
```

The checksum, run on each database:

```bash
docker compose exec -T postgres psql -U postgres -d ch04_a -c "SELECT md5(string_agg(concat_ws('|', rental_id, rental_date, inventory_id, customer_id, return_date, staff_id), ',' ORDER BY rental_id)) FROM rental WHERE rental_id > 100000;"
docker compose exec -T postgres psql -U postgres -d ch04_b -c "SELECT md5(string_agg(concat_ws('|', rental_id, rental_date, inventory_id, customer_id, return_date, staff_id), ',' ORDER BY rental_id)) FROM rental WHERE rental_id > 100000;"
```

Idempotency proof, on `ch04_a` only: count and checksum before, the second run, then count and checksum after.

```bash
docker compose exec -T postgres psql -U postgres -d ch04_a -c "SELECT count(*) FROM rental WHERE rental_id > 100000;"
uv run --env-file ../../../.env python seed.py ch04_a
docker compose exec -T postgres psql -U postgres -d ch04_a -c "SELECT count(*) FROM rental WHERE rental_id > 100000;"
```

## Results

### Load times

| Database | Output of `seed.py` | Time (`time`, real) |
|---|---|---|
| ch04_a | `ch04_a: inserted 1000000 rows in 18.69 s` | 0m19.627s |
| ch04_b | `ch04_b: inserted 1000000 rows in 17.82 s` | 0m18.710s |

Both loads are under 30 seconds. The `real` time includes the start-up of `uv`.

### Checksums

| Database | md5 |
|---|---|
| ch04_a | `104a9b493f2163004ef9c6dc258f1aa3` |
| ch04_b | `104a9b493f2163004ef9c6dc258f1aa3` |

The two values are equal, so the new rows are identical in both databases.

### Idempotency

| Step | Row count (`rental_id > 100000`) | Checksum |
|---|---|---|
| Before the second run | 1000000 | `104a9b493f2163004ef9c6dc258f1aa3` |
| Second run output | `ch04_a: the 1000000 rows already exist, nothing to do.` | |
| After the second run | 1000000 | `104a9b493f2163004ef9c6dc258f1aa3` |

The second run added no rows and did not change any: the count and the checksum are the same before and after.