CREATE OR REPLACE FUNCTION is_valid_isbn13(v text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT CASE
        WHEN v !~ '^[0-9](-?[0-9]){12}$' THEN false
        ELSE (
            SELECT (10 - (SUM(substr(replace(v, '-', ''), g.i, 1)::int
                              * CASE WHEN g.i % 2 = 1 THEN 1 ELSE 3 END) % 10)) % 10
                   = substr(replace(v, '-', ''), 13, 1)::int
            FROM generate_series(1, 12) AS g(i)
        )
    END
$$;
 
-- ---------------------------------------------------------------
-- 2. Domain and table
-- ---------------------------------------------------------------
CREATE DOMAIN isbn13 AS text CHECK (is_valid_isbn13(VALUE));
 
CREATE TABLE book (
    book_id  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn     isbn13 NOT NULL UNIQUE,
    title    text NOT NULL
);
 
-- Confirm the function is marked IMMUTABLE ('i' in pg_proc.provolatile)
SELECT proname, provolatile AS volatility_i_means_immutable
FROM pg_proc
WHERE proname = 'is_valid_isbn13';
 
-- ---------------------------------------------------------------
-- 3. Valid values (must succeed)
-- ---------------------------------------------------------------
INSERT INTO book (isbn, title) VALUES ('978-0-306-40615-7', 'Valid with hyphens (1)');
INSERT INTO book (isbn, title) VALUES ('9781402894626', 'Valid without hyphens');
INSERT INTO book (isbn, title) VALUES ('978-3-16-148410-0', 'Valid with hyphens (2)');
 
-- ---------------------------------------------------------------
-- 3. Invalid values (must fail with the domain check error)
-- ---------------------------------------------------------------
 
-- Wrong check digit (last digit should be 7)
INSERT INTO book (isbn, title) VALUES ('978-0-306-40615-8', 'Invalid: wrong check digit');
 
-- Too short (12 digits)
INSERT INTO book (isbn, title) VALUES ('978-0-306-4061', 'Invalid: too short');
 
-- Leading hyphen
INSERT INTO book (isbn, title) VALUES ('-9780306406157', 'Invalid: leading hyphen');
 
-- Two hyphens in a row
INSERT INTO book (isbn, title) VALUES ('978--0306406157', 'Invalid: double hyphen');
 
-- Final state: only the 3 valid rows
SELECT book_id, isbn, title FROM book ORDER BY book_id;
 