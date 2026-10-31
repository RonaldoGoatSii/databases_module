# Session 04: CRUD on Pagila

## Files

- `queries.sql`: the 12 operations, numbered with a comment. Operations 6, 8, 9, 10 and 12 contain more than one statement.

## How to run

From the repository root, on a fresh copy of Pagila:

```bash
./scripts/create-db.sh ex04 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex04 -v ON_ERROR_STOP=1 < exercises/04-crud/exercise/queries.sql
```

Run the file with `ON_ERROR_STOP=1`. If it stops, the error message shows which operation failed.

## Design decisions

- **Operation 6: two counts.** `BETWEEN '2026-01-01' AND '2026-01-31'` only includes rentals up to midnight at the start of 31 January, so it misses the rest of that day. The half-open interval `>= '2026-01-01' AND < '2026-02-01'` is the correct one. The difference of 781 − 746 = 35 rentals is what happened on 31 January after midnight.
- **Operation 8: transaction.** The count and the update run inside `BEGIN ... COMMIT`, so both see the same data.
- **Operation 9: upsert.** `ON CONFLICT (actor_id) DO UPDATE` adds 1 to the existing row, so running it twice gives 2.
- **Operation 10: `DO NOTHING`.** The second run skips the row, which is why it reports `INSERT 0 0`.
- **Operation 12: the delete targets only the test rows.** The `WHERE` uses the same fields as the insert, so no other payments are removed.

## Output of each operation

All 12 operations ran from top to bottom with `ON_ERROR_STOP=1`. The command exited with code `0` and no `ERROR` lines. Every result matches the expected value in the exercise.

### 1. PG-13 films longer than 120 minutes

Expected 118 rows, from APOLLO TEEN to WRONG BEHAVIOR. Result: **118 rows**.

```
 film_id |            title            | rating | length
---------+-----------------------------+--------+--------
      33 | APOLLO TEEN                 | PG-13  |    153
      35 | ARACHNOPHOBIA ROLLERCOASTER | PG-13  |    147
      36 | ARGONAUTS TOWN              | PG-13  |    127
  ...    (114 rows not shown)
     990 | WORLD LEATHERNECKS          | PG-13  |    171
     993 | WRONG BEHAVIOR              | PG-13  |    178
(118 rows)
```

### 2. Actors whose last name contains "son"

Expected 9 rows. Result: **9 rows**.

```
 actor_id | first_name | last_name
----------+------------+-----------
      154 | MERYL      | GIBSON
       65 | ANGELA     | HUDSON
      146 | ALBERT     | JOHANSSON
        8 | MATTHEW    | JOHANSSON
       64 | RAY        | JOHANSSON
       61 | CHRISTIAN  | NEESON
       62 | JAYNE      | NEESON
        6 | BETTE      | NICHOLSON
      168 | WILL       | WILSON
(9 rows)
```

### 3. Rentals not yet returned

Expected 241 rows. Result: **241 rows**. First and last rows shown.

```
 rental_id |          rental_date          | inventory_id | customer_id
-----------+-------------------------------+--------------+-------------
     12938 | 2022-02-14 15:16:03+00        |         3987 |          28
     11541 | 2022-02-14 15:16:03+00        |         2026 |         335
  ...    (237 rows not shown)
     87523 | 2026-07-27 18:19:13.640597+00 |           46 |         420
     87512 | 2026-07-27 21:22:13.614736+00 |         2763 |         511
(241 rows)
```

### 4. Distinct rental_duration values

Expected 5 rows, from 3 to 7. Result: **5 rows**.

```
 rental_duration
-----------------
               3
               4
               5
               6
               7
(5 rows)
```

### 5. Third page of films

Expected 10 rows, from AMERICAN CIRCUS to ANYTHING SAVANNAH. Result: **10 rows**, as expected.

```
 film_id |        title
---------+----------------------
      21 | AMERICAN CIRCUS
      22 | AMISTAD MIDSUMMER
      23 | ANACONDA CONFESSIONS
      24 | ANALYZE HOOSIERS
      25 | ANGELS LIFE
      26 | ANNIE IDENTITY
      27 | ANONYMOUS HUMAN
      28 | ANTHEM LUKE
      29 | ANTITRUST TOMATOES
      30 | ANYTHING SAVANNAH
(10 rows)
```

### 6a. January rentals, BETWEEN

Expected 746. Result: **746**. This is the incorrect count: the BETWEEN bound `'2026-01-31'` is midnight, so the rentals made on 31 January after 00:00 are not counted.

```
 january_between
-----------------
             746
(1 row)
```

### 6b. January rentals, half-open interval

Expected 781. Result: **781**. This is the correct count. The difference (781 − 746 = 35) is the rentals made on 31 January.

```
 january_range
---------------
           781
(1 row)
```

### 7. Insert ADA LOVELACE

Expected 1 row, actor_id 201. Result: **actor_id 201**.

```
 actor_id
----------
      201
(1 row)
```

### 8. NC-17 films under 60 minutes, transaction

Expected 21 rows in both the count and the UPDATE. Result: **21** in the count and **21 rows** in the UPDATE, then `COMMIT`.

```
 films_to_update
-----------------
              21
(1 row)

 film_id |        title        | rental_rate
---------+---------------------+-------------
       3 | ADAPTATION HOLES    |        3.49
      15 | ALIEN CENTER        |        3.49
      66 | BENEATH RUSH        |        1.49
  ...    (16 rows not shown)
     981 | WOLVES DESIRE       |        1.49
    1000 | ZORRO ARK           |        5.49
(21 rows)

UPDATE 21
COMMIT
```

### 9. Award upsert, run twice, then SELECT

Expected awards = 2. Result: **awards = 2**.

```
CREATE TABLE
INSERT 0 1
INSERT 0 1
 actor_id | awards
----------+--------
        1 |      2
(1 row)
```

### 10. Insert actor 2 with DO NOTHING, run twice

Expected: first run inserts 1 row, second run inserts 0. Result: **INSERT 0 1** then **INSERT 0 0**.

```
INSERT 0 1
INSERT 0 0
```

### 11. Insert 3 test payments

Expected 3 rows. Result: **3 rows**, payment_id 102095 to 102097.

```
 payment_id
------------
     102095
     102096
     102097
(3 rows)

INSERT 0 3
```

### 12. Delete the test payments, transaction

Expected 3 rows in both the count and the DELETE. Result: **3** in the count and **DELETE 3**, then `COMMIT`.

```
BEGIN
 test_payments
---------------
             3
(1 row)

 payment_id
------------
     102095
     102096
     102097
(3 rows)

DELETE 3
COMMIT
```