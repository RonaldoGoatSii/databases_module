WITH film_rentals AS (
    SELECT c.category_id,
           c.name AS category,
           f.film_id,
           f.title,
           COUNT(r.rental_id) AS rentals
    FROM category c
    JOIN film_category fc ON fc.category_id = c.category_id
    JOIN film f           ON f.film_id = fc.film_id
    LEFT JOIN inventory i ON i.film_id = f.film_id
    LEFT JOIN rental r    ON r.inventory_id = i.inventory_id
    GROUP BY c.category_id, c.name, f.film_id, f.title
),
ranked AS (
    SELECT category, title, rentals,
           DENSE_RANK() OVER (PARTITION BY category_id ORDER BY rentals DESC) AS position
    FROM film_rentals
)
SELECT category, title, rentals, position
FROM ranked
WHERE position <= 3
ORDER BY category, position, title;
 
-- 2. Revenue per day in July 2026, with the running total for the month.
--    (expected 28 rows; the last running_total is 2409.88)
WITH daily AS (
    SELECT payment_date::date AS day,
           SUM(amount)        AS revenue
    FROM payment
    WHERE payment_date >= '2026-07-01'
      AND payment_date <  '2026-08-01'
    GROUP BY payment_date::date
)
SELECT day,
       revenue,
       SUM(revenue) OVER (ORDER BY day) AS running_total
FROM daily
ORDER BY day;
 
-- 3. Revenue per month for the whole data set, with the change from the previous month
--    in value and in percentage (1 decimal). (expected 55 rows; July 2026 = 2409.88,
--    previous month = 2105.73, change 304.15, 14.4%)
WITH monthly AS (
    SELECT date_trunc('month', payment_date) AS month,
           SUM(amount)                       AS revenue
    FROM payment
    GROUP BY date_trunc('month', payment_date)
),
with_previous AS (
    SELECT month,
           revenue,
           LAG(revenue) OVER (ORDER BY month) AS previous_revenue
    FROM monthly
)
SELECT to_char(month, 'YYYY-MM') AS month,
       revenue,
       revenue - previous_revenue AS change,
       ROUND(100.0 * (revenue - previous_revenue) / previous_revenue, 1) AS change_pct
FROM with_previous
ORDER BY month;
 
-- 4. Each customer's position in the ranking of their store by total paid.
--    Customers with no payments count as 0, and tied customers share a position (RANK).
--    (expected 999 rows; customer 468 first in store 1 with 344.06; customer 526 first in store 2 with 358.12)
WITH totals AS (
    SELECT c.customer_id,
           c.store_id,
           COALESCE(SUM(p.amount), 0) AS total_paid
    FROM customer c
    LEFT JOIN payment p ON p.customer_id = c.customer_id
    GROUP BY c.customer_id, c.store_id
)
SELECT customer_id,
       store_id,
       total_paid,
       RANK() OVER (PARTITION BY store_id ORDER BY total_paid DESC) AS position
FROM totals
ORDER BY store_id, position, customer_id;
 
-- 5. The top 5 customers of each store by total paid. (expected 10 rows)
--    ROW_NUMBER gives exactly 5 per store, with customer_id as the tie-breaker.
WITH totals AS (
    SELECT c.customer_id,
           c.store_id,
           COALESCE(SUM(p.amount), 0) AS total_paid
    FROM customer c
    LEFT JOIN payment p ON p.customer_id = c.customer_id
    GROUP BY c.customer_id, c.store_id
),
numbered AS (
    SELECT customer_id,
           store_id,
           total_paid,
           ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY total_paid DESC, customer_id) AS row_no
    FROM totals
)
SELECT store_id, row_no AS position, customer_id, total_paid
FROM numbered
WHERE row_no <= 5
ORDER BY store_id, row_no;
 