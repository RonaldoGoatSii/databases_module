"""
Refreshes monthly_revenue under a lock, so that two processes never refresh at the same time.
Run two at once:  uv run python refresh.py & uv run python refresh.py & wait
"""
import os
import time
import uuid

import psycopg

from patterns import RELEASE_SCRIPT, redis_client

LOCK_KEY = "lock:refresh:monthly_revenue"
LOCK_TTL = 60
HOLD_SECONDS = 5


def main() -> None:
    r = redis_client()
    token = uuid.uuid4().hex
    pid = os.getpid()

    if not r.set(LOCK_KEY, token, nx=True, ex=LOCK_TTL):
        print(f"[{pid}] lock held by another process: skipped")
        return

    print(f"[{pid}] lock acquired, refreshing monthly_revenue")
    try:
        with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
            conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_revenue")
        print(f"[{pid}] refreshed; holding the lock for {HOLD_SECONDS} s")
        time.sleep(HOLD_SECONDS)
    finally:
        released = r.register_script(RELEASE_SCRIPT)(keys=[LOCK_KEY], args=[token])
        print(f"[{pid}] released lock: {'yes' if released else 'no (not ours any more)'}")


if __name__ == "__main__":
    main()