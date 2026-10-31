WITH
-- One row per customer and month with at least one rental.
rental_months AS (
    SELECT DISTINCT r.customer_id,
           date_trunc('month', r.rental_date)::date AS month
    FROM rental r
),
-- Give each month a consecutive number (year * 12 + month), and a row number per customer.
-- Inside one island, both numbers go up by 1 together, so their difference stays the same.
numbered AS (
    SELECT customer_id,
           month,
           EXTRACT(YEAR FROM month) * 12 + EXTRACT(MONTH FROM month) AS month_index,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY month) AS row_no
    FROM rental_months
),
-- The difference (month_index - row_no) is the island id: equal for all months of one island.
islands AS (
    SELECT customer_id,
           MIN(month) AS first_month,
           MAX(month) AS last_month,
           COUNT(*)   AS months
    FROM numbered
    GROUP BY customer_id, month_index - row_no
),
-- Longest island per customer. Ties in length keep the earliest one.
longest AS (
    SELECT customer_id,
           first_month,
           last_month,
           months,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY months DESC, first_month) AS rn
    FROM islands
)
SELECT customer_id,
       to_char(first_month, 'YYYY-MM') AS first_month,
       to_char(last_month,  'YYYY-MM') AS last_month,
       months
FROM longest
WHERE rn = 1
ORDER BY months DESC, customer_id
LIMIT 10;
 