# Session 06 challenge: gaps and islands

## Files

- `islands.sql`: the query. It returns the 10 customers with the longest island of consecutive months with rentals.

## How to run

From the repository root, on a fresh copy of Pagila:

```bash
./scripts/create-db.sh ch06 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ch06 -v ON_ERROR_STOP=1 < exercises/06-window/challenge/islands.sql > /tmp/ch06_output.txt 2>&1
echo "exit: $?"
grep -c "ERROR" /tmp/ch06_output.txt
```

Expected: `exit: 0` and `0` errors.

## Technique: grouping consecutive months

This is the classic "gaps and islands" trick, and it uses only window functions.

1. **One row per customer and month.** `rental_months` keeps each customer's active months (`DISTINCT` on the first day of the month).
2. **A month index.** `year * 12 + month` turns each month into a whole number, so that consecutive months differ by exactly 1 (for example, December 2023 is 2023·12+12 and January 2024 is 2024·12+1; the difference is 1).
3. **A row number per customer.** `ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY month)` numbers each customer's months 1, 2, 3, …
4. **The island id.** Inside one island, the month index and the row number both increase by 1 at each step, so `month_index - row_no` is constant. A gap in the months makes the index jump by more than 1 while the row number only moves by 1, so the difference changes. Grouping by this difference gives one group per island.
5. **Island statistics.** `MIN(month)`, `MAX(month)` and `COUNT(*)` give the first month, the last month and the length of each island.
6. **Longest island per customer.** A second `ROW_NUMBER()`, ordered by length descending and then by first month ascending, keeps the earliest island when two have the same length.
7. **Top 10.** The final `ORDER BY months DESC, customer_id LIMIT 10` gives the result.

## Result: the 10 customers with the longest islands

Expected: the first row is customer 70 with 19 months (2023-06 to 2024-12), and the tenth row is customer 556 with 16 months.

```
 customer_id | first_month | last_month | months
-------------+-------------+------------+--------
          70 | 2023-06     | 2024-12    |     19
         547 | 2022-05     | 2023-10    |     18
         567 | 2022-06     | 2023-11    |     18
          33 | 2023-07     | 2024-11    |     17
         158 | 2022-11     | 2024-03    |     17
         299 | 2022-05     | 2023-09    |     17
         443 | 2023-07     | 2024-11    |     17
         533 | 2023-04     | 2024-08    |     17
         740 | 2024-07     | 2025-11    |     17
         556 | 2023-09     | 2024-12    |     16
(10 rows)
```

The first row is customer 70 with 19 months (2023-06 to 2024-12), and the tenth row is customer 556 with 16 months, as expected. The ties are ordered by `customer_id`: among the 17-month islands, customers 33, 158, 299, 443, 533 and 740 appear in that order, and among the 18-month islands, 547 comes before 567.