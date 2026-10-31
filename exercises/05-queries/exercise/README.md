# Session 05: queries on Pagila

## Files

- `queries.sql`: the 10 queries, each preceded by a comment with its number and the question.

## How to run

From the repository root, on a fresh copy of Pagila:

```bash
./scripts/create-db.sh ex05 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex05 -v ON_ERROR_STOP=1 < exercises/05-queries/exercise/queries.sql > /tmp/ex05_output.txt 2>&1
echo "exit: $?"
grep -c "ERROR" /tmp/ex05_output.txt
```

Expected: `exit: 0` and `0` lines with `ERROR`.

## Design decisions

- **Per-category questions count a film in each of its categories** (questions 1, 2 and 10), as the exercise says. A film with two categories adds to both.
- **Question 1 uses LEFT JOIN** so that categories with no films still appear, with `0`.
- **Question 2 filters `payment_date` with a half-open range** (`>= 2025-01-01` and `< 2026-01-01`), so that the whole of 31 December is included.
- **Question 3 uses `NOT EXISTS`** over the chain `inventory` → `rental`. A film with no copy and a film with copies that were never rented both appear.
- **Question 4 counts the ratings from `film`** instead of writing 5 by hand, so the query stays right if a rating is added.
- **Question 5 uses a self join** on `film_actor` with `actor_id > actor_id`. The `>` lists each pair once and avoids the pair (A, A).
- **Question 6 uses `COUNT(DISTINCT)`**, because the join with `payment` repeats each customer once per payment.
- **Question 7 uses CTEs**: one for each customer's total (with `COALESCE` so a customer with no payments counts as 0), and one for the average per country.
- **Question 8 uses a correlated subquery** with `MAX` per rating, so ties are kept.
- **Question 10 converts the interval to days** with `EXTRACT(EPOCH ...) / 86400`, so partial days count. If the result differs from the expected `5.30` for Sci-Fi, the other reading (whole days, `EXTRACT(DAY ...)`) is the one to check.

## Output of each query

All 10 queries ran with `exit: 0` and no `ERROR` lines. Every row count and every reference value in the exercise matches.

### 1. Films per category

Expected: 16 rows, Drama and Music first with 152 each. **Result: 16 rows, as expected.** First 5 rows:

```
  category   | films
-------------+-------
 Drama       |   152
 Music       |   152
 Travel      |   151
 Children    |   150
 Foreign     |   150
```

### 2. Revenue per category per month, 2025

Expected: 192 rows, Action in January 2025 = 314.94. **Result: 192 rows, Action in January 2025 = 314.94.** First 5 rows:

```
  category   |         month          | revenue
-------------+------------------------+---------
 Action      | 2025-01-01 00:00:00+00 |  314.94
 Animation   | 2025-01-01 00:00:00+00 |  408.78
 Children    | 2025-01-01 00:00:00+00 |  306.98
 Classics    | 2025-01-01 00:00:00+00 |  314.88
 Comedy      | 2025-01-01 00:00:00+00 |  239.14
```

### 3. Films never rented

Expected: 42 rows. **Result: 42 rows.** First 5 rows:

```
 film_id |         title
---------+------------------------
      14 | ALICE FANTASIA
      33 | APOLLO TEEN
      36 | ARGONAUTS TOWN
      38 | ARK RIDGEMONT
      41 | ARSENIC INDEPENDENCE
```

### 4. Customers who rented all 5 ratings

Expected: 908 rows. **Result: 908 rows.** First 5 rows:

```
 customer_id | first_name |  last_name
-------------+------------+--------------
         505 | RAFAEL     | ABNEY
         504 | NATHANIEL  | ADAM
         601 | EMILY      | ADAMS
         934 | HARUKI     | ADAMS
         924 | ISABELLA   | ADAMS
```

### 5. Actor pairs with more than 3 films together

Expected: 143 rows. **Result: 143 rows.** First 5 rows:

```
 actor1_id |       actor1        | actor2_id |       actor2       | films
-----------+---------------------+-----------+--------------------+-------
        27 | JULIA MCQUEEN       |        60 | HENRY BERRY        |     7
        83 | BEN WILLIS          |       161 | HARVEY HOPE        |     6
        15 | CUBA OLIVIER        |       198 | MARY KEITEL        |     6
        21 | KIRSTEN PALTROW     |       108 | WARREN NOLTE       |     6
       114 | MORGAN MCDORMAND    |       168 | WILL WILSON        |     6
```

### 6. Countries with more than 20 customers

Expected: 7 rows, Mexico first with 430 customers. **Result: 7 rows, Mexico first with 430 customers.** Rows:

```
      country       | customers | total_paid
--------------------+-----------+------------
 Mexico             |       430 |   35650.03
 India              |        60 |   14182.51
 China              |        53 |   12389.30
 United States      |        36 |    8618.76
 Japan              |        31 |    7287.91
 Brazil             |        28 |    6540.03
 Russian Federation |        28 |    6583.79
```

### 7. Customers above the average of their country

Expected: 449 rows. **Result: 449 rows.** First 5 rows:

```
 customer_id | total  |      avg_total
-------------+--------+----------------------
         526 | 358.12 | 239.4100000000000000
         468 | 344.06 | 236.3751666666666667
         380 | 324.04 | 233.2000000000000000
         368 | 323.17 | 246.9112500000000000
         295 | 322.12 | 235.1353571428571429
```

### 8. Longest films of each rating

Expected: 14 rows. **Result: 14 rows.** First 5 rows:

```
 rating | film_id |       title        | length
--------+---------+--------------------+--------
 G      |     182 | CONTROL ANTHEM     |    185
 G      |     212 | DARN FORRESTER     |    185
 G      |     609 | MUSCLE BRIGHT      |    185
 PG     |     991 | WORST BANGER       |    185
 PG-13  |     141 | CHICAGO NORTH      |    185
```

### 9. Customers with no rental since 2026-04-01

Expected: 49 rows. **Result: 49 rows.** First 5 rows:

```
 customer_id | first_name |  last_name
-------------+------------+-------------
         798 | MICHELLE   | ADAMS
         449 | OSCAR      | AQUINO
         978 | SOFIA      | BAKER
         134 | EMMA       | BOYD
         181 | ANA        | BRADLEY
```

### 10. Average days out per category

Expected: 16 rows, Sci-Fi first with 5.30. **Result: 16 rows, Sci-Fi first with 5.30.** First 5 rows:

```
  category   | avg_days_out
-------------+--------------
 Sci-Fi      |         5.30
 Music       |         5.27
 Sports      |         5.26
 Drama       |         5.18
 Children    |         5.17
```