# Session 07 exercise: query plans and indexes

## Files

- `setup.sql`: creates `big_rental` (2,000,000 rows, no indexes).
- `queries.sql`: the 5 queries, plus the rewrite of Q3 (`Q3b`).
- `indexes.sql`: the 3 indexes kept after measurement.
- `measure.py`: runs each query 3 times with `EXPLAIN (ANALYZE, BUFFERS)` and writes the median and the plans to `plans_before.txt` and `plans_after.txt`.

## Summary of medians

| Query | Before (ms) | After (ms) | Index used | Result |
|---|---|---|---|---|
| Q1 | 37.0 | 0.1 | partial index on `customer_id` WHERE `returned_at IS NULL` | faster |
| Q2 | 91.0 | 3.3 | `idx_rented_at` | faster |
| Q3 | 74.7 | 79.1 | none | no change (the index cannot be used as written) |
| Q3b | 43.0 | 3.1 | `idx_rented_at` | faster (rewrite of Q3) |
| Q4 | 106.9 | 102.6 | none | no change |
| Q5 | 49.6 | 0.9 | `idx_customer_rented` | faster |

The differences in Q3 and Q4 (about 4 ms and 4 ms) are measurement noise: the plan is the same before and after.

## Q1: open rentals of customer 42

**What it returns:** the number of rentals of customer 42 with no return date (`count(*)`).

**Plan before:**

```
->  Parallel Seq Scan on big_rental
      Filter: ((returned_at IS NULL) AND (customer_id = 42))
      Rows Removed by Filter: 666636
Execution Time: 29.963 ms
```

**Index:** `idx_q1_open_by_customer ON big_rental (customer_id) WHERE returned_at IS NULL`.

**Plan after:**

```
->  Index Only Scan using idx_q1_open_by_customer on big_rental
      Index Cond: (customer_id = 42)
      Heap Fetches: 0
Execution Time: 0.060 ms
```

**Median time:** 37.0 ms before, 0.1 ms after.

**Explanation:** the partial index contains only the open rentals (about 3% of the table), and `count(*)` needs no column from the table, so PostgreSQL answers from the index alone. `Heap Fetches: 0` confirms that no table row had to be read.

## Q2: rentals of the last day

**What it returns:** every rental made in the last 24 hours, ordered by `rented_at`.

**Plan before:**

```
Sort  (rows=738)
  Sort Key: rented_at
  ->  Parallel Seq Scan on big_rental
        Filter: (rented_at >= (now() - '1 day'::interval))
        Rows Removed by Filter: 666040
Execution Time: 90.985 ms
```

**Index:** `idx_rented_at ON big_rental (rented_at)`.

**Plan after:**

```
Sort  (rows=1879)
  Sort Key: rented_at
  ->  Bitmap Heap Scan on big_rental
        ->  Bitmap Index Scan on idx_rented_at
              Index Cond: (rented_at >= (now() - '1 day'::interval))
Execution Time: 3.318 ms
```

**Median time:** 91.0 ms before, 3.3 ms after.

**Explanation:** the index finds the 1,879 rows of the last day directly, instead of reading all 2,000,000. The `Sort` node is still there, because the bitmap scan does not return rows in index order, but sorting 1,879 rows is cheap.

## Q3: rentals of a given day (as written)

**What it returns:** every rental made on the date 10 days ago.

**Plan before:**

```
->  Parallel Seq Scan on big_rental
      Filter: ((rented_at)::date = (CURRENT_DATE - 10))
      Rows Removed by Filter: 666043
Execution Time: 74.697 ms
```

**Index:** none. The expression `rented_at::date` is a cast from `timestamptz` to `date`, and it depends on the session time zone, so PostgreSQL does not treat it as immutable. Trying to index it fails:

```
ERROR:  functions in index expression must be marked IMMUTABLE
```

**Plan after:** the same sequential scan (79.1 ms).

**Explanation:** no index can be used for this query as it is written, because the predicate is on the result of a non-immutable expression. The fix is to rewrite the query (Q3b).

## Q3b: the rewrite of Q3

**What it returns:** the same rows as Q3. Both return 1,872 rows.

**Rewrite:**

```sql
SELECT * FROM big_rental
WHERE rented_at >= current_date - 10
  AND rented_at <  current_date - 9;
```

**Plan before:**

```
->  Parallel Seq Scan on big_rental
      Filter: ((rented_at >= (CURRENT_DATE - 10)) AND (rented_at < (CURRENT_DATE - 9)))
      Rows Removed by Filter: 666043
Execution Time: 41.606 ms
```

**Index:** `idx_rented_at`, the same as Q2.

**Plan after:**

```
->  Bitmap Heap Scan on big_rental  (rows=1872)
      ->  Bitmap Index Scan on idx_rented_at
            Index Cond: ((rented_at >= (CURRENT_DATE - 10)) AND (rented_at < (CURRENT_DATE - 9)))
Execution Time: 2.816 ms
```

**Median time:** 43.0 ms before, 3.1 ms after.

**Explanation:** the rewrite compares the column itself with a range, so the B-tree can be used. The cast in Q3 hid the column from the index. The row counts match (1,872 in both queries), so the rewrite is equivalent.

## Q4: returned rentals per customer

**What it returns:** the number of returned rentals for each customer.

**Plan before:**

```
->  Parallel Seq Scan on big_rental  (rows=646640)
      Filter: (returned_at IS NOT NULL)
      Rows Removed by Filter: 20027
Execution Time: 104.752 ms
```

**Index:** none.

**Plan after:** the same plan (102.6 ms).

**Explanation:** about 97% of the rows match the filter, and every one of them is needed for the count. Reading an index and then the table for each row would cost more than one sequential pass, so PostgreSQL keeps the sequential scan. An index on `returned_at` would not change the plan.

## Q5: recent rentals of three customers

**What it returns:** the rentals of customers 7, 42 and 99 in the last 30 days, newest first.

**Plan before:**

```
Sort  (rows=98)
  Sort Key: rented_at DESC
  ->  Parallel Seq Scan on big_rental
        Filter: ((customer_id = ANY ('{7,42,99}')) AND (rented_at >= (now() - '30 days')))
        Rows Removed by Filter: 666568
Execution Time: 49.565 ms
```

**Index:** `idx_customer_rented ON big_rental (customer_id, rented_at DESC)`.

**Plan after:**

```
Sort  (rows=295)
  Sort Key: rented_at DESC
  ->  Bitmap Heap Scan on big_rental
        ->  Bitmap Index Scan on idx_customer_rented
              Index Cond: ((customer_id = ANY ('{7,42,99}')) AND (rented_at >= (now() - '30 days')))
Execution Time: 0.887 ms
```

**Median time:** 49.6 ms before, 0.9 ms after.

**Explanation:** the index narrows the search by the three customers and the 30-day range at once. The `Sort` node remains, because the `IN` list reads three separate ranges of the index, so the result is not in `rented_at` order across customers. Sorting 295 rows is cheap.

## Task 5: write cost

Insert 100,000 rows into the table without indexes, then into the table with the three indexes. The table is recreated with `setup.sql` between runs.

| Table | Insert time |
|---|---|
| No indexes | (not measured yet) |
| With 3 indexes | (not measured yet) |

**Explanation:** (fill in after measuring. Every inserted row must also update each index, so the table with indexes should take longer to write.)

## Output

The plans and times above come from `plans_before.txt` and `plans_after.txt`.