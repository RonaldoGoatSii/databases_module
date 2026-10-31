-- queries.sql: the 5 queries of the exercise, plus the rewrite of Q3.
-- Each query starts with a label line "-- Qn" so that measure.py can find it.

-- Q1
SELECT count(*) FROM big_rental WHERE customer_id = 42 AND returned_at IS NULL;

-- Q2
SELECT * FROM big_rental WHERE rented_at >= now() - interval '1 day' ORDER BY rented_at;

-- Q3
SELECT * FROM big_rental WHERE rented_at::date = current_date - 10;

-- Q3b (rewrite of Q3: same rows, but the column is compared without a cast)
SELECT * FROM big_rental
WHERE rented_at >= current_date - 10
  AND rented_at <  current_date - 9;

-- Q4
SELECT customer_id, count(*) FROM big_rental WHERE returned_at IS NOT NULL GROUP BY customer_id;

-- Q5
SELECT * FROM big_rental
WHERE customer_id IN (7, 42, 99) AND rented_at >= now() - interval '30 days'
ORDER BY rented_at DESC;