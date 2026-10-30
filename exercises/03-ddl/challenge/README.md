# Session 03 challenge: ISBN-13 domain

## Files

- `isbn.sql`: the validation function `is_valid_isbn13`, the domain `isbn13`, the `book` table and the 7 test inserts (3 valid, 4 invalid).

## Design decisions

- **Function in SQL, not PL/pgSQL.** A short `LANGUAGE sql` function is easier to read and is inlined by the planner.
- **Format check with a regex.** `^[0-9](-?[0-9]){12}$` allows exactly 13 digits, with at most one hyphen between two consecutive digits. This rejects a leading hyphen, a trailing hyphen and two hyphens in a row, without extra code.
- **`CASE` before the arithmetic.** The check digit is only computed when the format is right. This matters because `::int` on a non-digit raises an error, and SQL does not guarantee that `AND` stops early.
- **The domain** wraps the function, so any column declared as `isbn13` is validated automatically. The `book` table does not repeat the rule.
- **The hyphens are stored as typed.** `978-0-306-40615-7` and `9780306406157` are the same book but are different strings, so `UNIQUE` on `isbn` does not catch a duplicate written in the other format. To solve this, normalise the value (remove hyphens) before storing it, for example with a trigger, or accept it as a known limitation.

## Output of `isbn.sql`

How to run, from the repository root:

```bash
./scripts/create-db.sh ch03
docker compose exec -T postgres psql -U postgres -d ch03 < exercises/03-ddl/challenge/isbn.sql
```

```
CREATE FUNCTION
CREATE DOMAIN
CREATE TABLE
     proname     | volatility_i_means_immutable 
-----------------+------------------------------
 is_valid_isbn13 | i
(1 row)

INSERT 0 1
INSERT 0 1
INSERT 0 1
ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
 book_id |       isbn        |         title          
---------+-------------------+------------------------
       1 | 978-0-306-40615-7 | Valid with hyphens (1)
       2 | 9781402894626     | Valid without hyphens
       3 | 978-3-16-148410-0 | Valid with hyphens (2)
(3 rows)
```

The function reports `i` (immutable), the 3 valid values were inserted, the 4 invalid values failed with the domain check error, and the final `SELECT` lists only the 3 valid books.

## Why the function must be IMMUTABLE

`IMMUTABLE` tells PostgreSQL that the function always returns the same result for the same input, and that it does not read anything from the database (tables, settings, the current time).

This matters because:

1. **The database can evaluate the check at any time.** It runs when a row is inserted or updated, and it can also run again when the constraint is added to a table that already has data. If the function depended on something that could change, a value could be valid today and invalid tomorrow, and the data would no longer match the rule.
2. **PostgreSQL only allows some uses of a function if it is immutable.** For example, a generated column or an index expression that uses the function is refused unless the function is `IMMUTABLE`. Making the domain index-friendly depends on this too.
3. **The planner can optimise with it.** An immutable function can be evaluated once, at planning time, when its input is a constant. A function that might change could not be.

In this function, the result depends only on the text it receives. It does not query any table and does not use `now()`, which is why the `IMMUTABLE` label is correct. If someone later changed it to read a table of allowed ISBN prefixes, it would have to become `STABLE` (or `VOLATILE`), and the label would be wrong.