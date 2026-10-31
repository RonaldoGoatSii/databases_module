-- pagination.sql: OFFSET versus keyset pagination, and index-only scans with VACUUM (session 07 challenge)
-- Run on a database created with the setup of the exercise:
--   ./scripts/create-db.sh ch07 --reset
--   docker compose exec -T postgres psql -U postgres -d ch07 -v ON_ERROR_STOP=1 < exercises/07-indexes/challenge/pagination.sql
-- Note: \gset needs psql to read this file (use `<` or -f), not a pipe through a shell.

-- Setup: the big_rental table (same as the exercise). Run it first if the table does not exist:
--   exercises/07-indexes/exercise/setup.sql

-- ---------------------------------------------------------------
-- Task 1: an index that matches the sort order (rented_at DESC, id DESC)
-- ---------------------------------------------------------------
DROP INDEX IF EXISTS idx_page_key;
CREATE INDEX idx_page_key ON big_rental (rented_at DESC, id DESC);
ANALYZE big_rental;

-- ---------------------------------------------------------------
-- Task 2: page 5,000 with OFFSET (skip 99,980 rows, return 20)
-- ---------------------------------------------------------------
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id
FROM big_rental
ORDER BY rented_at DESC, id DESC
OFFSET 99980 LIMIT 20;

-- ---------------------------------------------------------------
-- Task 3: the same page with keyset pagination
-- First store the last row of page 4,999 in psql variables.
-- ---------------------------------------------------------------
SELECT rented_at AS last_rented_at, id AS last_id
FROM big_rental
ORDER BY rented_at DESC, id DESC
OFFSET 99979 LIMIT 1 \gset

-- The keyset query, using those variables
SELECT id, rented_at, customer_id
FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC
LIMIT 20;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id
FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC
LIMIT 20;

-- Check: the two methods return the same 20 rows (this must print t)
WITH by_offset AS (
    SELECT id, rented_at, customer_id
    FROM big_rental
    ORDER BY rented_at DESC, id DESC
    OFFSET 99980 LIMIT 20
),
by_keyset AS (
    SELECT id, rented_at, customer_id
    FROM big_rental
    WHERE (rented_at, id) < (:'last_rented_at', :last_id)
    ORDER BY rented_at DESC, id DESC
    LIMIT 20
)
SELECT (SELECT count(*) FROM by_offset) = 20
   AND (SELECT count(*) FROM (SELECT * FROM by_offset EXCEPT SELECT * FROM by_keyset) d) = 0
   AND (SELECT count(*) FROM (SELECT * FROM by_keyset EXCEPT SELECT * FROM by_offset) d) = 0
   AS same_rows;

-- ---------------------------------------------------------------
-- Task 4: recreate the index with INCLUDE (customer_id), so that the keyset query can be an Index Only Scan
-- The keyset query reads id, rented_at and customer_id, and all three are in the index.
-- ---------------------------------------------------------------
DROP INDEX IF EXISTS idx_page_key;
CREATE INDEX idx_page_key_incl ON big_rental (rented_at DESC, id DESC) INCLUDE (customer_id);
VACUUM ANALYZE big_rental;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id
FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC
LIMIT 20;

-- ---------------------------------------------------------------
-- Task 5: change some rows, then read the Heap Fetches line, then VACUUM and read it again
-- ---------------------------------------------------------------
UPDATE big_rental SET customer_id = customer_id WHERE id % 50 = 0;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id
FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC
LIMIT 20;

VACUUM big_rental;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id
FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC
LIMIT 20;