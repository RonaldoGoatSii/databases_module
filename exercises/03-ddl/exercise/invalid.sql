-- invalid.sql: each statement below must fail.
-- Run without ON_ERROR_STOP so every error is printed:
--   psql -U postgres -d ex03 -f invalid.sql

-- ---------------------------------------------------------------
-- Setup: rows that must be inserted successfully, so that each
-- failing statement below fails only for the constraint it names.
-- ---------------------------------------------------------------
INSERT INTO publisher (name, country) VALUES ('Porto Editora', 'Portugal');

INSERT INTO book (isbn13, title, publication_year, publisher_id)
VALUES ('9789720000001', 'Example Book', 2000,
        (SELECT publisher_id FROM publisher WHERE name = 'Porto Editora'));

INSERT INTO author (name) VALUES ('Author One');

INSERT INTO book_author (isbn13, author_id, author_order)
VALUES ('9789720000001', (SELECT author_id FROM author WHERE name = 'Author One'), 1);

INSERT INTO copy (barcode, isbn13, acquisition_date, condition)
VALUES ('C-0001', '9789720000001', '2020-01-10', 'good');

INSERT INTO reader (card_number, name, email)
VALUES ('R-0001', 'Ana Silva', 'ana@library.example');

INSERT INTO loan (barcode, card_number, loan_date)
VALUES ('C-0001', 'R-0001', '2026-10-01');

-- ---------------------------------------------------------------
-- The 5 statements that must fail
-- ---------------------------------------------------------------

-- 1. Constraint: reader_email_key (UNIQUE on reader.email)
INSERT INTO reader (card_number, name, email)
VALUES ('R-0002', 'Bruno Costa', 'ana@library.example');

-- 2. Constraint: copy_condition_check (CHECK on copy.condition)
INSERT INTO copy (barcode, isbn13, acquisition_date, condition)
VALUES ('C-0002', '9789720000001', '2021-03-05', 'brand_new');

-- 3. Constraint: loan_one_open_per_copy (partial unique index: one open loan per copy)
INSERT INTO loan (barcode, card_number, loan_date)
VALUES ('C-0001', 'R-0001', '2026-10-02');

-- 4. Constraint: book_author_author_fk (ON DELETE RESTRICT: author still has books)
DELETE FROM author
WHERE name = 'Author One';

-- 5. Constraint: fine_amount_nonneg (CHECK on fine.amount)
INSERT INTO fine (loan_id, amount)
VALUES ((SELECT loan_id FROM loan WHERE card_number = 'R-0001'), -1.00);