# Session 16 exercise: Redis as derived data

## Files

- `rebuild.py`: rebuilds `customer:{id}:categories` from PostgreSQL, with one query and one pipeline. It writes each set in a temporary key and renames it, and deletes stale keys.
- `verify.py`: compares every set with PostgreSQL (size and members) and reports unexpected keys. Exit code `1` if there is any difference, `0` otherwise.
- `pyproject.toml`: the uv project.

## Setup

From the repository root:

```bash
./scripts/create-db.sh ex16 --pagila --reset
```

From `exercises/16-consistency/exercise`:

```bash
uv sync
```

The `.env` of this folder must use Redis database 1: `REDIS_URL=redis://:PASSWORD@127.0.0.1:6379/1`. `DATABASE_URL` must end in `/ex16`.

## Commands

```bash
# 1. Rebuild the sets
uv run --env-file .env python rebuild.py

# 2. Empty database 1 and rebuild it (the password is the one of the redis service)
docker compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning -n 1 FLUSHDB
uv run --env-file .env python rebuild.py

# Count the keys with SCAN
docker compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning -n 1 --scan --pattern 'customer:*:categories' | wc -l

# 3. Verify
uv run --env-file .env python verify.py; echo "exit: $?"
```

Note: `$REDIS_PASSWORD` is read from the shell. Run `set -a; source .env; set +a` first, or replace it with the password.

## Task 2: rebuild after FLUSHDB

`FLUSHDB` on database 1 returned `OK`. Then:

```
$ uv run --env-file .env python rebuild.py
sets written: 997, stale keys deleted: 0
```

Count of the keys with `SCAN` on database 1:

```
997
```

Expected 997, as in the exercise. The customers 647 and 978 have no rentals, so they have no set.

**Note on database numbers.** The first rebuild wrote its 997 sets to database 0 by mistake. The cause was the `REDIS_URL` exported in the shell by `source` of the root `.env` (which ends in `/0`): `uv run --env-file` does not replace a variable that already exists in the shell. `unset REDIS_URL` fixed it. The keys left in database 0 belong to the other exercises and were not removed.

## Task 3: verify

**Starting state:**

```
$ uv run --env-file .env python verify.py; echo "exit: $?"
0 difference(s)
exit: 0
```

**a) A category removed from customer 1.** Customer 1 has 16 categories, among them `Action`:

```
$ redis-cli SREM customer:1:categories Action
1
$ uv run --env-file .env python verify.py; echo "exit: $?"
size of customer:1:categories: redis=15 postgres=16
customer:1:categories: missing member 'Action'
2 difference(s)
exit: 1
```

**b) A set for customer 647, who has no rentals.** The previous difference is still there, and the new key is reported:

```
$ redis-cli SADD customer:647:categories Fake
1
$ uv run --env-file .env python verify.py; echo "exit: $?"
size of customer:1:categories: redis=15 postgres=16
customer:1:categories: missing member 'Action'
unexpected key customer:647:categories (customer has no rentals or does not exist)
3 difference(s)
exit: 1
```

**c) After rebuilding.** `rebuild.py` rewrites the 997 sets and deletes the stale key `customer:647:categories`:

```
$ uv run --env-file .env python rebuild.py
sets written: 997, stale keys deleted: 1
$ uv run --env-file .env python verify.py; echo "exit: $?"
0 difference(s)
exit: 0
```

Result: `verify.py` detects the removed member and the unexpected key (exit 1), and passes after the rebuild (exit 0).

## Task 4: the keys of exercises 15 and 16

| Key | Class | What is lost if Redis loses it | How it comes back |
|---|---|---|---|
| `customer:{id}:viewed` (sorted set of viewed films) | source of truth | the view history: nothing in PostgreSQL has it | it does not come back. Only persistence (AOF) or a write to PostgreSQL protects it |
| `cache:film:{id}` (film JSON, TTL 300 s) | derived (cache) | nothing: the next read is a miss | the first `get_film` reads PostgreSQL and fills the key again |
| `lock:refresh:monthly_revenue` (token, TTL 60 s) | ephemeral | the lock is released early, so two refreshes can overlap for a moment | the next refresh acquires the lock; the TTL is a safety net |
| `ratelimit:{customer}:{minute}` (counter, TTL 120 s) | ephemeral | the counter restarts: the customer can make 10 more requests in that minute | the window ends by itself; the key is never needed again |
| `customer:{id}:categories` (set of category names) | derived | nothing that cannot be recomputed | `rebuild.py` recomputes every set from PostgreSQL in one query and one pipeline |

The materialised view `monthly_revenue` is in PostgreSQL, not in Redis, so it is not in this table: it is rebuilt with `REFRESH MATERIALIZED VIEW`.

## Task 5: the configuration

Chosen configuration (for the Redis instance of this exercise):

```
appendonly yes
appendfsync everysec
maxmemory 256mb
maxmemory-policy noeviction
```

To check it on the running instance:

```bash
docker compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning CONFIG GET appendonly
docker compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning CONFIG GET appendfsync
docker compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning CONFIG GET maxmemory-policy
```

**Justification:**

- **`appendonly yes`:** the viewed-films history is a source of truth, and nothing else can rebuild it. Without AOF, a restart loses it. The other keys (cache, locks, rate limits, categories) are derived or ephemeral, but they would share the same instance and the same file.
- **`appendfsync everysec`:** it writes the log to disk once per second. The worst case is losing the last second of views. `always` loses nothing but makes each write wait for the disk; `no` leaves the loss to the operating system. For view history, one second is the usual trade-off.
- **`maxmemory 256mb`:** an explicit limit, so that the instance does not take all the memory of the host. The value must be sized from the real usage (`INFO memory`) of the keys of the table.
- **`maxmemory-policy noeviction`:** the policy applies to the whole instance, not to one key. The trade-off:
  - `allkeys-lru` (or `allkeys-*`) can evict any key, including the view history (the source of truth). That is not acceptable on this instance.
  - `volatile-lru` or `volatile-ttl` evict only keys with a TTL. The view history has a TTL (30 days), so it can still be evicted. The categories sets have no TTL, so they would never be evicted.
  - `noeviction` never evicts. When the memory is full, writes fail with an error, including the locks and the rate limits. That is safer for the data, but the application must handle the errors, and the memory must be monitored.

**When to use two instances:** when the classes need different policies. A persistent instance (AOF, `noeviction`) for the source-of-truth keys, and a cache instance (`allkeys-lru`, no AOF) for the derived keys (film cache, categories) and the ephemeral keys (locks, rate limits). Then a full cache never evicts the view history, and the persistence costs are paid only where they are needed.

**About `docker-compose.redis-aof.yml`:** this exercise does not change the compose file. Before turning on AOF with that file, read the warning in `sessions/16-redis-consistency/`. (Not yet read: paste the warning here if you want the justification to refer to it.)

## Done when

- `rebuild.py` creates 997 sets with one query and one pipeline.
- `verify.py` detects the removed category (exit 1), detects the set of the customer without rentals (exit 1), and passes after the rebuild (exit 0).
- The tables and the configuration are justified as above.