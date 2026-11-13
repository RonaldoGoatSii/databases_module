"""
Shows each pattern working, step by step. Run: uv run python demo.py
"""
import time

from patterns import (
    allow_request,
    get_film,
    pg_connect,
    recent_views,
    record_view,
    redis_client,
    update_film_rate,
)


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> None:
    r = redis_client()
    conn = pg_connect()

    section("1. recently viewed films")
    r.delete("customer:1:viewed")
    for film_id in range(1, 26):
        record_view(r, 1, film_id)
    views = recent_views(r, 1)
    print(f"after films 1 to 25: {views}")
    print(f"count: {len(views)} (expected 20), first: {views[0]} (expected 25), last: {views[-1]} (expected 6)")
    record_view(r, 1, 10)
    views = recent_views(r, 1)
    print(f"after viewing film 10 again: {views}")
    print(f"film 10 at the front: {views[0] == 10}; no duplicates: {len(views) == len(set(views))}")
    print(f"TTL: {r.ttl('customer:1:viewed')} seconds (expected close to 2592000)")

    section("2. cache-aside")
    r.delete("cache:film:1")
    film, hit = get_film(r, conn, 1)
    print(f"first read: hit={hit}, rental_rate={film['rental_rate']}")
    film, hit = get_film(r, conn, 1)
    print(f"second read: hit={hit}, rental_rate={film['rental_rate']}")
    print(f"cache TTL: {r.ttl('cache:film:1')} seconds (expected close to 300)")
    update_film_rate(r, conn, 1, 1.99)
    print("updated rental rate of film 1 to 1.99 (database write, then cache key deleted)")
    film, hit = get_film(r, conn, 1)
    print(f"read after update: hit={hit}, rental_rate={film['rental_rate']} (expected miss and 1.99)")

    section("3. lock")
    print("run two refreshes at the same time with:  uv run python refresh.py & uv run python refresh.py & wait")

    section("4. rate limit")
    r.delete(f"ratelimit:1:{int(time.time() // 60)}")
    results = [allow_request(r, 1) for _ in range(12)]
    print(f"12 calls for customer 1: {results}")
    print(f"True: {results.count(True)} (expected 10), False: {results.count(False)} (expected 2)")
    print("waiting for the next minute window...")
    time.sleep(60 - (time.time() % 60) + 0.1)
    print(f"first call in the new minute: {allow_request(r, 1)} (expected True)")

    conn.close()


if __name__ == "__main__":
    main()