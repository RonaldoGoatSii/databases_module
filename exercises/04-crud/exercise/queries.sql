-- queries.sql: session 04, CRUD on Pagila
-- Run on a fresh copy:
--   ./scripts/create-db.sh ex04 --pagila --reset
--   docker compose exec -T postgres psql -U postgres -d ex04 -v ON_ERROR_STOP=1 < exercises/04-crud/exercise/queries.sql

-- 1. Films rated PG-13 and longer than 120 minutes, sorted by title (expected 118 rows)
SELECT film_id, title, rating, length
FROM film
WHERE rating = 'PG-13' AND length > 120
ORDER BY title;

-- 2. Actors whose last name contains "son", in any case (expected 9 rows)
SELECT actor_id, first_name, last_name
FROM actor
WHERE last_name ILIKE '%son%'
ORDER BY last_name, first_name;

-- 3. Rentals not yet returned (expected 241 rows)
SELECT rental_id, rental_date, inventory_id, customer_id
FROM rental
WHERE return_date IS NULL
ORDER BY rental_date;

-- 4. Distinct rental_duration values in film, ascending (expected 5 rows, from 3 to 7)
SELECT DISTINCT rental_duration
FROM film
ORDER BY rental_duration;

-- 5. Third page of films by title, 10 per page (expected 10 rows, from AMERICAN CIRCUS to ANYTHING SAVANNAH)
--    Page n uses OFFSET (n - 1) * 10, so page 3 uses OFFSET 20.
SELECT film_id, title
FROM film
ORDER BY title
LIMIT 10 OFFSET 20;

-- 6a. Rentals made in January 2026, with BETWEEN (expected 746 rows)
--     This is NOT the correct count. BETWEEN '2026-01-01' AND '2026-01-31' compares with
--     '2026-01-31 00:00', so every rental made during the day of 31 January is left out.
SELECT count(*) AS january_between
FROM rental
WHERE rental_date BETWEEN '2026-01-01' AND '2026-01-31';

-- 6b. Rentals made in January 2026, with a half-open interval (expected 781 rows)
--     This is the correct count. The start is included, the end (1 February) is excluded,
--     so the whole of 31 January is counted.
SELECT count(*) AS january_range
FROM rental
WHERE rental_date >= '2026-01-01' AND rental_date < '2026-02-01';

-- 7. Insert ADA LOVELACE and get the generated actor_id back (expected 1 row, actor_id 201)
INSERT INTO actor (first_name, last_name)
VALUES ('ADA', 'LOVELACE')
RETURNING actor_id;

-- 8. In a transaction, raise rental_rate by 0.50 for NC-17 films shorter than 60 minutes
--    (expected 21 rows in both the count and the UPDATE)
BEGIN;

SELECT count(*) AS films_to_update
FROM film
WHERE rating = 'NC-17' AND length < 60;

UPDATE film
SET rental_rate = rental_rate + 0.50
WHERE rating = 'NC-17' AND length < 60
RETURNING film_id, title, rental_rate;

COMMIT;

-- 9. Create the award table, then upsert one award for actor 1.
--    Run the upsert twice. The result must be 2.
CREATE TABLE actor_award (
    actor_id integer PRIMARY KEY REFERENCES actor,
    awards   integer NOT NULL DEFAULT 0
);

INSERT INTO actor_award (actor_id, awards)
VALUES (1, 1)
ON CONFLICT (actor_id)
DO UPDATE SET awards = actor_award.awards + EXCLUDED.awards;

INSERT INTO actor_award (actor_id, awards)
VALUES (1, 1)
ON CONFLICT (actor_id)
DO UPDATE SET awards = actor_award.awards + EXCLUDED.awards;

SELECT actor_id, awards FROM actor_award WHERE actor_id = 1;

-- 10. Insert actor 2 with 5 awards, ignoring it if it already exists.
--     Run twice: the first run inserts 1 row (INSERT 0 1), the second inserts 0 (INSERT 0 0).
INSERT INTO actor_award (actor_id, awards)
VALUES (2, 5)
ON CONFLICT (actor_id) DO NOTHING;

INSERT INTO actor_award (actor_id, awards)
VALUES (2, 5)
ON CONFLICT (actor_id) DO NOTHING;

-- 11. Insert 3 test payments and return their payment_id (expected 3 rows)
INSERT INTO payment (customer_id, staff_id, rental_id, amount, payment_date)
VALUES
    (1, 2, 76, 0.01, '2026-07-30 12:00+00'),
    (1, 2, 76, 0.01, '2026-07-30 12:00+00'),
    (1, 2, 76, 0.01, '2026-07-30 12:00+00')
RETURNING payment_id;

-- 12. Delete the 3 test payments, inside a transaction (expected 3 rows in both the count and the DELETE)
BEGIN;

SELECT count(*) AS test_payments
FROM payment
WHERE payment_date = '2026-07-30 12:00+00'
  AND amount = 0.01
  AND customer_id = 1
  AND staff_id = 2
  AND rental_id = 76;

DELETE FROM payment
WHERE payment_date = '2026-07-30 12:00+00'
  AND amount = 0.01
  AND customer_id = 1
  AND staff_id = 2
  AND rental_id = 76
RETURNING payment_id;

COMMIT;