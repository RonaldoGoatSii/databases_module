# Session 06: window functions on Pagila

## Status

Tasks 1 to 5 are written in `queries.sql`. **Task 6 (the materialised view and the refresh steps) is not in the exercise text I received**, so it is not written yet. Send the text of task 6 and I will add it.

## How to run

```bash
./scripts/create-db.sh ex06 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex06 -v ON_ERROR_STOP=1 < exercises/06-window/exercise/queries.sql > /tmp/ex06_output.txt 2>&1
echo "exit: $?"
grep -c "ERROR" /tmp/ex06_output.txt
```

Expected: `exit: 0` and `0` lines with `ERROR`.

## Design decisions

- **Task 1 uses `DENSE_RANK()`** so tied films share a position without skipping the next one. With `RANK()`, a tie at position 2 pushes the next film to position 4, which is outside 1 to 3, and the query returned 50 rows instead of 56. With `DENSE_RANK()`, the filter `position <= 3` keeps the 3 highest distinct rental counts in each category, including ties.
- **Task 2 uses `SUM() OVER (ORDER BY day)`**, a running total over the days of the month.
- **Task 3 uses `LAG()`** to get the previous month, and computes the percentage over that previous value.
- **Task 4 counts customers with no payments as 0** with `LEFT JOIN` and `COALESCE`, and ranks them inside each store with `RANK()`, so ties share a position.
- **Task 5 uses `ROW_NUMBER()`** to get exactly 5 customers per store, breaking ties by `customer_id`.

## Output of each task

All five tasks ran with `exit: 0` and no `ERROR` lines. Row counts and reference values match the exercise.

### 1. Top 3 films per category

Expected 56 rows. **Result: 56 rows.** First 5 rows:

```
  category   |        title         | rentals | position
-------------+----------------------+---------+----------
 Action      | CAT CONEHEADS        |     123 |        1
 Action      | SEABISCUIT PUNK      |      96 |        2
 Action      | IDOLS SNATCHERS      |      92 |        3
 Animation   | GILMORE BOILED       |     102 |        1
 Animation   | GRIT CLOCKWORK       |     102 |        1
```

### 2. Revenue per day, July 2026

Expected 28 rows, last running total 2409.88. **Result: 28 rows, last running total 2409.88.** First 5 rows:

```
    day     | revenue | running_total
------------+---------+---------------
 2026-07-01 |   67.78 |         67.78
 2026-07-02 |   89.62 |        157.40
 2026-07-03 |   61.78 |        219.18
 2026-07-04 |   97.66 |        316.84
 2026-07-05 |   46.81 |        363.65
```

### 3. Monthly revenue and change

Expected 55 rows; July 2026 = 2409.88, previous month 2105.73, change 304.15 (14.4%). **Result: 55 rows, and all these values match.** First 5 rows:

```
  month  | revenue  |  change  | change_pct
---------+----------+----------+------------
 2022-01 |  3094.78 |          |
 2022-02 | 10164.97 |  7070.19 |      228.5
 2022-03 | 11413.86 |  1248.89 |       12.3
 2022-04 | 10759.52 |  -654.34 |       -5.7
 2022-05 | 11347.28 |   587.76 |        5.5
```

### 4. Customer position within store

Expected 999 rows; customer 468 first in store 1 (344.06), customer 526 first in store 2 (358.12). **Result: 999 rows, and both values match.** First 5 rows of store 1:

```
 customer_id | store_id | total_paid | position
-------------+----------+------------+----------
         468 |        1 |     344.06 |        1
         380 |        1 |     324.04 |        2
         368 |        1 |     323.17 |        3
         295 |        1 |     322.12 |        4
          22 |        1 |     320.17 |        5
```

### 5. Top 5 customers per store

Expected 10 rows. **Result: 10 rows.**

```
 store_id | position | customer_id | total_paid
----------+----------+-------------+------------
        1 |        1 |         468 |     344.06
        1 |        2 |         380 |     324.04
        1 |        3 |         368 |     323.17
        1 |        4 |         295 |     322.12
        1 |        5 |          22 |     320.17
```

## Task 6

Not written yet: the text of task 6 (the materialised view and the refresh steps) was not in the exercise I received.