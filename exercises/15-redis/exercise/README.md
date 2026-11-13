# Session 15 exercise: four Redis patterns on Pagila data

## Files

- `patterns.py`: the functions of the four patterns (recent views, cache-aside, lock release script, rate limit).
- `demo.py`: runs each demonstration and prints every step.
- `refresh.py`: refreshes `monthly_revenue` under a lock. Two copies started together show the lock at work.
- `pyproject.toml`, `.env.example`: the uv project and the connection variables.

## Setup

From the repository root:

```bash
./scripts/create-db.sh ex15 --pagila --reset
```

Create the materialised view (run it in the `ex15` database):

```bash
docker compose exec -T postgres psql -U postgres -d ex15 -v ON_ERROR_STOP=1 <<'SQL'
CREATE MATERIALIZED VIEW monthly_revenue AS
SELECT date_trunc('month', payment_date)::date AS month, sum(amount) AS revenue
FROM payment
GROUP BY 1;

CREATE UNIQUE INDEX ON monthly_revenue (month);
SQL
```

Then, from `exercises/15-redis/exercise`:

```bash
cp .env.example .env          # then change the passwords
uv sync
```

## Commands

```bash
# Demonstrations of the four patterns, step by step (about 1 minute, because of the rate-limit step)
uv run --env-file .env python demo.py

# Lock: two refreshes at the same time
uv run --env-file .env python refresh.py & uv run --env-file .env python refresh.py & wait
```

## Output of demo.py

Before this run, the rental rate of film 1 was reset to 0.99 (the value of the Pagila data), so that the cache demonstration shows the change from 0.99 to 1.99:

```
UPDATE film SET rental_rate = 0.99 WHERE film_id = 1;
```

```
=== 1. recently viewed films ===
after films 1 to 25: [25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6]
count: 20 (expected 20), first: 25 (expected 25), last: 6 (expected 6)
after viewing film 10 again: [10, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 9, 8, 7, 6]
film 10 at the front: True; no duplicates: True
TTL: 2592000 seconds (expected close to 2592000)

=== 2. cache-aside ===
first read: hit=False, rental_rate=0.99
second read: hit=True, rental_rate=0.99
cache TTL: 300 seconds (expected close to 300)
updated rental rate of film 1 to 1.99 (database write, then cache key deleted)
read after update: hit=False, rental_rate=1.99 (expected miss and 1.99)

=== 3. lock ===
run two refreshes at the same time with:  uv run python refresh.py & uv run python refresh.py & wait

=== 4. rate limit ===
12 calls for customer 1: [True, True, True, True, True, True, True, True, True, True, False, False]
True: 10 (expected 10), False: 2 (expected 2)
waiting for the next minute window...
first call in the new minute: True (expected True)
```

The demonstrations 1, 2 and 4 show the expected results. Demonstration 3 (the lock) is shown by the two-process output below.

## Output of the two refresh.py processes

```
[31308] lock held by another process: skipped
[31307] lock acquired, refreshing monthly_revenue
[31307] refreshed; holding the lock for 5 s
[31307] released lock: yes
```

One process acquired the lock, refreshed the view and released it. The other found the lock held and skipped. The lock was released only by the process that held it.

Expected: one process acquires the lock and refreshes, the other is skipped because the lock is held. The lock is released by the process that acquired it, and only by that process (the release script compares the token first).

## Keys used

| Key | Redis type | TTL | Purpose |
|---|---|---|---|
| `customer:{id}:viewed` | sorted set (score = view time, member = film id) | 30 days, renewed on each view | the 20 most recent films viewed by a customer |
| `cache:film:{id}` | string (JSON) | 300 seconds | cache of a film read from PostgreSQL |
| `lock:refresh:monthly_revenue` | string (random token) | 60 seconds (safety net) | prevents two refreshes of the materialised view at the same time |
| `ratelimit:{customer}:{minute}` | string (integer counter) | 120 seconds (the window is 60) | at most 10 requests per customer per minute |

## Design notes

- **Recent views:** `ZADD` with the time as score moves an existing film to the front, which gives the "no duplicates" property for free. `ZREMRANGEBYRANK 0 -21` keeps the 20 highest scores. The pipeline sends the three commands together.
- **Cache-aside:** the database is always the source of truth. The cache is filled on a miss, and invalidated after a write (the database write comes first, then the key is deleted).
- **Lock:** `SET NX EX` makes the acquisition atomic. The random token identifies the owner. The release is a Lua script that deletes the key only if its value is still our token, so a process whose lock expired cannot delete the lock of the process that now holds it. The 60-second TTL is a safety net for a process that crashes while holding the lock.
- **Rate limit:** a fixed window keyed by the minute. The counter is created with `INCR`, and gets an expiry on its first increment. The expiry (120 seconds) is longer than the window, so the key outlives the minute it counts.

**Known limits:** the rate limit uses a fixed window, so a customer can send 10 requests at the end of one minute and 10 at the start of the next. A sliding window would avoid this, at a higher cost. The `INCR` and the first `EXPIRE` are two commands, not one atomic step; if the process dies between them, the counter has no expiry (rare, but possible).