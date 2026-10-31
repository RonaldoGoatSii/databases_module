-- setup.sql: creates the big_rental table of the session 07 tutorial (2,000,000 rows, no indexes).
-- Run on an empty database created with: ./scripts/create-db.sh ex07 --reset
--   docker compose exec -T postgres psql -U postgres -d ex07 -v ON_ERROR_STOP=1 < exercises/07-indexes/exercise/setup.sql

DROP TABLE IF EXISTS big_rental;

SELECT setseed(0.1);

CREATE TABLE big_rental AS
SELECT g AS id,
       (random() * 599 + 1)::int                          AS customer_id,
       now() - random() * interval '3 years'               AS rented_at,
       CASE WHEN random() < 0.03 THEN NULL ELSE now() END  AS returned_at
FROM generate_series(1, 2000000) AS g;

VACUUM ANALYZE big_rental;