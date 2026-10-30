# Session 03: Municipal library, DDL and constraints

## Files

- `schema.sql`: creates every table of the library model (session 02), with data types and constraints.
- `invalid.sql`: a short setup block that inserts valid rows, followed by 5 statements that must fail. Each one is rejected by the constraint named in its comment.

## Design decisions

- **Identity columns** for surrogate keys (`GENERATED ALWAYS AS IDENTITY`).
- **`numeric(6,2)`** for fine amounts, never `float`.
- **`timestamptz`** for `created_at` in reservations. `date` for loan, return and payment dates.
- **`due_date`** is a generated column (`loan_date + 14`), so it cannot disagree with the loan date.
- **One open loan per copy** is a partial unique index: `WHERE return_date IS NULL`.
- **`ON DELETE RESTRICT`** on `book_author.author_id`: deleting an author who has books would lose history, so the database refuses it.
- **`ON DELETE CASCADE`** on `book_author.isbn13`: the author order of a book has no meaning without the book, so deleting a book removes its author rows.

## Rules that are not in the schema

Some rules from session 02 cannot be expressed as a single constraint in this schema, so they belong to the application or to a trigger in a later session:

- A book has at least one author and at least one copy.
- A reader has at most 5 open loans (needs a trigger or a check in the application, with a lock on the reader row).
- A reservation is only created when no copy is available.
- The fine of 0.50 per late day is calculated at return time.

## How to run

From the repository root, create the database and run the schema on it:

```bash
./scripts/create-db.sh ex03
docker compose exec -T postgres psql -U postgres -d ex03 -v ON_ERROR_STOP=1 < exercises/03-ddl/exercise/schema.sql
```

Then run the invalid statements. Without `ON_ERROR_STOP`, every error is printed:

```bash
docker compose exec -T postgres psql -U postgres -d ex03 < exercises/03-ddl/exercise/invalid.sql
```

## Output of `invalid.sql`

The first 7 `INSERT` lines are the setup rows. The last 5 lines of errors are the statements that must fail.

```
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
ERROR:  duplicate key value violates unique constraint "reader_email_key"
DETAIL:  Key (email)=(ana@library.example) already exists.
ERROR:  new row for relation "copy" violates check constraint "copy_condition_check"
DETAIL:  Failing row contains (C-0002, 9789720000001, 2021-03-05, brand_new).
ERROR:  duplicate key value violates unique constraint "loan_one_open_per_copy"
DETAIL:  Key (barcode)=(C-0001) already exists.
ERROR:  update or delete on table "author" violates RESTRICT setting of foreign key constraint "book_author_author_fk" on table "book_author"
DETAIL:  Key (author_id)=(1) is referenced from table "book_author".
ERROR:  new row for relation "fine" violates check constraint "fine_amount_nonneg"
DETAIL:  Failing row contains (1, 1, -1.00, null).
```

Each of the 5 statements must show an error that names its constraint:

| # | Statement | Expected constraint |
|---|---|---|
| 1 | duplicate reader email | `reader_email_key` |
| 2 | copy condition `brand_new` | `copy_condition_check` |
| 3 | second open loan for copy `C-0001` | `loan_one_open_per_copy` |
| 4 | delete an author who has books | `book_author_author_fk` |
| 5 | fine with a negative amount | `fine_amount_nonneg` |