"""
Rebuilds customer:{id}:categories from PostgreSQL.
- one query reads (customer, category) pairs from PostgreSQL
- one pipeline writes every set: built in a temporary key, then RENAMEd (readers never see a half-built set)
- stale keys (customers without rentals, or customers not in the database) are deleted in the same pipeline
Run: uv run --env-file .env python rebuild.py
"""
import os
from collections import defaultdict

import psycopg
import redis

PAIRS_SQL = """
SELECT DISTINCT r.customer_id, c.name
FROM rental r
JOIN inventory i ON i.inventory_id = r.inventory_id
JOIN film_category fc ON fc.film_id = i.film_id
JOIN category c ON c.category_id = fc.category_id
"""


def redis_client() -> redis.Redis:
    return redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


def key_for(customer_id: int) -> str:
    return f"customer:{customer_id}:categories"


def load_expected() -> dict[int, set[str]]:
    """What Redis should contain: customer_id -> set of category names. One query."""
    expected: dict[int, set[str]] = defaultdict(set)
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        for customer_id, category in conn.execute(PAIRS_SQL):
            expected[customer_id].add(category)
    return dict(expected)


def rebuild(r: redis.Redis, expected: dict[int, set[str]]) -> dict[str, int]:
    existing = set(r.scan_iter(match="customer:*:categories", count=1000))  # SCAN, never KEYS
    wanted = {key_for(c) for c in expected}

    pipe = r.pipeline(transaction=True)
    for customer_id, categories in expected.items():
        key = key_for(customer_id)
        tmp = f"{key}:tmp"
        pipe.delete(tmp)
        pipe.sadd(tmp, *categories)
        pipe.rename(tmp, key)                          # atomic replace of the old set
    for stale in existing - wanted:
        pipe.delete(stale)
    pipe.execute()
    return {"written": len(expected), "deleted": len(existing - wanted)}


def main() -> None:
    r = redis_client()
    expected = load_expected()
    result = rebuild(r, expected)
    print(f"sets written: {result['written']}, stale keys deleted: {result['deleted']}")


if __name__ == "__main__":
    main()