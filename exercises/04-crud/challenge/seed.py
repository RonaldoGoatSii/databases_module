import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
 
import psycopg
 
SEED = 42
FIRST_ID = 100_001
LAST_ID = 1_100_000
EXPECTED = LAST_ID - FIRST_ID + 1
START = datetime(2022, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 7, 31, 23, 59, 59, tzinfo=timezone.utc)
SPAN_SECONDS = int((END - START).total_seconds())
 
COLUMNS = "rental_id, rental_date, inventory_id, customer_id, return_date, staff_id"
 
 
def dsn(dbname: str) -> str:
    return (
        f"host={os.getenv('POSTGRES_HOST', '127.0.0.1')} "
        f"port={os.getenv('POSTGRES_PORT', '5432')} "
        f"dbname={dbname} "
        f"user={os.getenv('POSTGRES_USER', 'postgres')} "
        f"password={os.getenv('POSTGRES_PASSWORD', '')}"
    )
 
 
def make_rows(rng, inventory_ids, customer_ids, staff_ids):
    for rental_id in range(FIRST_ID, LAST_ID + 1):
        rental_date = START + timedelta(seconds=rng.randrange(SPAN_SECONDS))
        if rng.random() < 0.10:
            return_date = None                       # still rented
        else:
            return_date = rental_date + timedelta(hours=rng.randrange(1, 14 * 24))
        yield (
            rental_id,
            rental_date,
            rng.choice(inventory_ids),
            rng.choice(customer_ids),
            return_date,
            rng.choice(staff_ids),
        )
 
 
def load(dbname: str) -> None:
    with psycopg.connect(dsn(dbname)) as conn:
        with conn.cursor() as cur:
            existing = cur.execute(
                "SELECT count(*) FROM rental WHERE rental_id BETWEEN %s AND %s",
                (FIRST_ID, LAST_ID),
            ).fetchone()[0]
 
            if existing == EXPECTED:
                print(f"{dbname}: the {EXPECTED} rows already exist, nothing to do.")
                return
            if existing != 0:
                sys.exit(f"{dbname}: {existing} rows found in the range, partial load. Reset the database.")
 
            # Reference lists, ordered, so that the same seed gives the same choices everywhere.
            inventory_ids = [r[0] for r in cur.execute("SELECT inventory_id FROM inventory ORDER BY inventory_id")]
            customer_ids = [r[0] for r in cur.execute("SELECT customer_id FROM customer ORDER BY customer_id")]
            staff_ids = [r[0] for r in cur.execute("SELECT staff_id FROM staff ORDER BY staff_id")]
 
            rng = random.Random(SEED)
            t0 = time.perf_counter()
            with cur.copy(f"COPY rental ({COLUMNS}) FROM STDIN") as copy:
                for row in make_rows(rng, inventory_ids, customer_ids, staff_ids):
                    copy.write_row(row)
 
            cur.execute(
                "SELECT setval(pg_get_serial_sequence('rental', 'rental_id'), "
                "(SELECT max(rental_id) FROM rental))"
            )
            conn.commit()
            elapsed = time.perf_counter() - t0
 
            inserted = cur.execute(
                "SELECT count(*) FROM rental WHERE rental_id BETWEEN %s AND %s",
                (FIRST_ID, LAST_ID),
            ).fetchone()[0]
 
    print(f"{dbname}: inserted {inserted} rows in {elapsed:.2f} s")
 
 
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python seed.py <database>")
    load(sys.argv[1])
 