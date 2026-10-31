-- indexes.sql: the indexes kept after measurement.
-- Each one is justified in README.md with the plan before and after.
-- Apply with: docker compose exec -T postgres psql -U postgres -d ex07 -v ON_ERROR_STOP=1 < exercises/07-indexes/exercise/indexes.sql

-- Q1: partial index. Only ~3% of rows have returned_at IS NULL, so the index stays small.
CREATE INDEX idx_q1_open_by_customer ON big_rental (customer_id) WHERE returned_at IS NULL;

-- Q2 and Q3b: B-tree on rented_at (range search and ORDER BY rented_at).
CREATE INDEX idx_rented_at ON big_rental (rented_at);

-- Q5: composite index, customer first (equality), then rented_at descending (range and ORDER BY).
CREATE INDEX idx_customer_rented ON big_rental (customer_id, rented_at DESC);

-- No index for Q3 as written: rented_at::date is not an immutable expression, so it cannot be indexed.
-- No index for Q4: the query reads about 97% of the table, so a sequential scan is cheaper.