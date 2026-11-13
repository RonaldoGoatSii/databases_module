"""
Four Redis patterns on Pagila data. Connection settings come from DATABASE_URL and REDIS_URL.
"""
import json
import os
import time
from decimal import Decimal

import psycopg
import redis

VIEWED_LIMIT = 20
VIEWED_TTL = 30 * 24 * 3600          # 2,592,000 seconds
FILM_CACHE_TTL = 300
RATE_LIMIT = 10


def redis_client() -> redis.Redis:
    return redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


def pg_connect() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


# 1. Recently viewed films: a sorted set per customer, score = view time
def record_view(r: redis.Redis, customer_id: int, film_id: int) -> None:
    key = f"customer:{customer_id}:viewed"
    pipe = r.pipeline()
    pipe.zadd(key, {str(film_id): time.time()})            # same film again: score moves to the front
    pipe.zremrangebyrank(key, 0, -(VIEWED_LIMIT + 1))      # keep only the 20 most recent (lowest ranks are oldest)
    pipe.expire(key, VIEWED_TTL)                           # 30 days after the last view
    pipe.execute()


def recent_views(r: redis.Redis, customer_id: int) -> list[int]:
    ids = r.zrevrange(f"customer:{customer_id}:viewed", 0, VIEWED_LIMIT - 1)
    return [int(i) for i in ids]


# 2. Cache-aside: read the cache, fall back to PostgreSQL, store for 300 seconds
def get_film(r: redis.Redis, conn: psycopg.Connection, film_id: int) -> tuple[dict, bool]:
    """Returns (film, hit). hit is True when the value came from the cache."""
    key = f"cache:film:{film_id}"
    cached = r.get(key)
    if cached is not None:
        return json.loads(cached), True
    row = conn.execute(
        "SELECT title, rating, length, rental_rate FROM film WHERE film_id = %s", (film_id,)
    ).fetchone()
    film = {
        "title": row[0],
        "rating": row[1],
        "length": row[2],
        "rental_rate": float(row[3]),
    }
    r.set(key, json.dumps(film), ex=FILM_CACHE_TTL)
    return film, False


def update_film_rate(r: redis.Redis, conn: psycopg.Connection, film_id: int, rate: float) -> None:
    conn.execute("UPDATE film SET rental_rate = %s WHERE film_id = %s", (Decimal(str(rate)), film_id))
    conn.commit()
    r.delete(f"cache:film:{film_id}")                      # invalidate after the database write


# 3. Lock: release only by the process that holds the token (used by refresh.py)
RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
else
  return 0
end
"""


# 4. Rate limit: fixed window of one minute per customer, counter expires
def allow_request(r: redis.Redis, customer_id: int) -> bool:
    window = int(time.time() // 60)
    key = f"ratelimit:{customer_id}:{window}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, 120)                                  # a little longer than the window
    return count <= RATE_LIMIT