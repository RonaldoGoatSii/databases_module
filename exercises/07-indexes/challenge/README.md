# Session 07 challenge: OFFSET versus keyset pagination, and VACUUM

## Files

- `pagination.sql`: every statement, in order: the index, the OFFSET page, the keyset page, the check that both return the same rows, the index with `INCLUDE`, the update, and the two `VACUUM` steps.

## How to run

From the repository root:

```bash
./scripts/create-db.sh ch07 --reset
docker compose exec -T postgres psql -U postgres -d ch07 -v ON_ERROR_STOP=1 < exercises/07-indexes/exercise/setup.sql
docker compose exec -T postgres psql -U postgres -d ch07 -v ON_ERROR_STOP=1 < exercises/07-indexes/challenge/pagination.sql > /tmp/ch07_output.txt 2>&1
echo "exit: $?"
grep -c "ERROR" /tmp/ch07_output.txt
```

The file must be read by `psql` from a file (`<` or `-f`), because the `\gset` command stores the last page's values in psql variables that the next statements use.

## Results

Run with `exit: 0` and no `ERROR` lines.

### Task 1: index matching the sort order

`CREATE INDEX idx_page_key ON big_rental (rented_at DESC, id DESC)`.

### Task 2: page 5,000 with OFFSET

```
->  Index Scan using idx_page_key on big_rental (actual time=0.137..534.468 rows=100000.00 loops=1)
Execution Time: 538.625 ms
```

The index is used, but PostgreSQL reads 100,000 index entries (rows=100000) to skip the first 99,980 and return 20. Time: **538.6 ms**.

### Task 3: page 5,000 with keyset pagination

```
->  Index Scan using idx_page_key on big_rental (actual time=0.008..0.019 rows=20.00 loops=1)
Execution Time: 0.030 ms
```

The index goes straight to the position of the last row of page 4,999 and reads 20 rows. Time: **0.030 ms**.

**Same rows:** `same_rows` = `t`. Both queries return the same 20 rows.

**Comparison:** about 18,000 times faster for the same result. The OFFSET query reads 100,000 entries; the keyset query reads 20.

### Task 4: index with INCLUDE (customer_id)

`CREATE INDEX idx_page_key_incl ON big_rental (rented_at DESC, id DESC) INCLUDE (customer_id)`.

```
->  Index Only Scan using idx_page_key_incl on big_rental (actual time=0.026..0.028 rows=20.00 loops=1)
      Heap Fetches: 0
Execution Time: 0.042 ms
```

The plan is an `Index Only Scan`. `Heap Fetches: 0`, because the table was just vacuumed and every page is all-visible.

### Task 5: update, then VACUUM

After `UPDATE big_rental SET customer_id = customer_id WHERE id % 50 = 0`:

```
->  Index Only Scan using idx_page_key_incl on big_rental (actual time=0.031..0.153 rows=20.00 loops=1)
      Heap Fetches: 20
Execution Time: 0.168 ms
```

After `VACUUM big_rental`:

```
->  Index Only Scan using idx_page_key_incl on big_rental (actual time=0.015..0.017 rows=20.00 loops=1)
      Heap Fetches: 0
Execution Time: 0.030 ms
```

`Heap Fetches` goes from 20 after the update to 0 after `VACUUM`. The page was no longer all-visible after the update, so PostgreSQL had to read the table to check each of the 20 rows. `VACUUM` marked the page all-visible again. Autovacuum did not run before the manual `VACUUM`, because the first plan after the update still shows the heap fetches.

## Why OFFSET gets slower as the page grows

`OFFSET 99980` does not jump to row 99,981. PostgreSQL has to produce the first 99,980 rows in the sort order, count them, throw them away, and only then return the 20 that were asked for. The work grows with the offset: page 5,000 reads 100,000 entries to return 20, and page 50,000 would read a million. The time of the OFFSET query grows with the page number, although the result is the same size.

## Why keyset pagination does not depend on the page number

The keyset query carries the last row of the previous page (`rented_at`, `id`) and asks for the rows strictly before it: `WHERE (rented_at, id) < (:last_rented_at, :last_id)`. With the index on the same order, PostgreSQL goes straight to that position in the index and reads 20 rows from there. The position is found by a search in the tree, so the cost is about the same for page 2 and for page 5,000. The comparison `(rented_at, id)` is a row comparison, which includes `id` as the tie-breaker, so no row is skipped or repeated when several rows share the same `rented_at`.

## Why an index only scan needs VACUUM

An index contains the key columns and the `INCLUDE` columns, but not the visibility of each row version. PostgreSQL must know whether each row is visible to the current transaction. Visibility is stored in the heap (the table) and summarised per page in the **visibility map**. When every row on a page is visible to all transactions (the page is "all-visible"), an index only scan can return the values from the index without reading that page of the table.

- After an update, PostgreSQL writes a new version of each row in the heap and clears the all-visible bit of the page. From then on, the index only scan must read the table for each row of that page, to check its visibility. That is what `Heap Fetches` counts.
- `VACUUM` removes dead row versions and sets the all-visible bit again for pages where every row is visible. Then the index only scan skips the table for those pages, and `Heap Fetches` falls back to 0.

`ANALYZE` updates the statistics that the planner uses to choose plans, while `VACUUM` updates the visibility map.

### Extra check: keyset at different page numbers

The last row of the previous page is found with an OFFSET, and that lookup is not timed. In an application it comes from the previous response.

| Page | Execution time | Scan node | Rows read |
|---|---|---|---|
| 2 | 0.042 ms | Index Only Scan (idx_page_key_incl) | 20 |
| 5,000 | 0.026 ms | Index Only Scan (idx_page_key_incl) | 20 |
| 50,000 | 0.027 ms | Index Only Scan (idx_page_key_incl) | 20 |

The keyset query reads the same 20 rows whatever the page number, so its time does not grow with the page. The OFFSET query for page 5,000 took 538.6 ms for the same result size.