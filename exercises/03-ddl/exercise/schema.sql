CREATE TABLE publisher (
    publisher_id  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          text NOT NULL,
    country       text NOT NULL,
    CONSTRAINT publisher_name_key UNIQUE (name)
);
 
CREATE TABLE author (
    author_id     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          text NOT NULL
);
 
CREATE TABLE book (
    isbn13            text PRIMARY KEY,
    title             text NOT NULL,
    publication_year  integer NOT NULL CHECK (publication_year BETWEEN 1450 AND 2100),
    publisher_id      integer NOT NULL REFERENCES publisher ON DELETE RESTRICT,
    available_copies  integer NOT NULL DEFAULT 0,
    CONSTRAINT book_isbn13_format CHECK (isbn13 ~ '^[0-9]{13}$'),
    CONSTRAINT book_available_copies_nonneg CHECK (available_copies >= 0)
);
 
CREATE TABLE book_author (
    isbn13        text    NOT NULL,
    author_id     integer NOT NULL,
    author_order  integer NOT NULL CHECK (author_order >= 1),
    PRIMARY KEY (isbn13, author_id),
    -- Composite UNIQUE: two authors cannot take the same position on one book
    CONSTRAINT book_author_order_key UNIQUE (isbn13, author_order),
    -- CASCADE: the author order of a book means nothing without the book
    CONSTRAINT book_author_book_fk FOREIGN KEY (isbn13) REFERENCES book ON DELETE CASCADE,
    -- RESTRICT: an author with books cannot be deleted by accident
    CONSTRAINT book_author_author_fk FOREIGN KEY (author_id) REFERENCES author ON DELETE RESTRICT
);
 
CREATE TABLE copy (
    barcode            text PRIMARY KEY,
    isbn13             text NOT NULL REFERENCES book ON DELETE RESTRICT,
    acquisition_date   date NOT NULL,
    condition          text NOT NULL,
    CONSTRAINT copy_condition_check CHECK (condition IN ('new', 'good', 'worn', 'damaged'))
);
 
CREATE TABLE reader (
    card_number        text PRIMARY KEY,
    name               text NOT NULL,
    email              text NOT NULL,
    phone              text,
    address            text,
    registration_date  date NOT NULL DEFAULT current_date,
    CONSTRAINT reader_email_key UNIQUE (email)
);
 
CREATE TABLE loan (
    loan_id      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    barcode      text NOT NULL REFERENCES copy ON DELETE RESTRICT,
    card_number  text NOT NULL REFERENCES reader ON DELETE RESTRICT,
    loan_date    date NOT NULL DEFAULT current_date,
    due_date     date GENERATED ALWAYS AS (loan_date + 14) STORED,
    return_date  date,
    CONSTRAINT loan_return_after_loan CHECK (return_date IS NULL OR return_date >= loan_date)
);
 
-- A copy can be in at most one open loan at a time
CREATE UNIQUE INDEX loan_one_open_per_copy ON loan (barcode) WHERE return_date IS NULL;
 
CREATE TABLE reservation (
    reservation_id  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    card_number     text NOT NULL REFERENCES reader ON DELETE RESTRICT,
    isbn13          text NOT NULL REFERENCES book ON DELETE RESTRICT,
    created_at      timestamptz NOT NULL DEFAULT now(),
    status          text NOT NULL DEFAULT 'active',
    CONSTRAINT reservation_status_check CHECK (status IN ('active', 'fulfilled', 'cancelled'))
);
 
CREATE TABLE fine (
    fine_id    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    loan_id    integer NOT NULL REFERENCES loan ON DELETE RESTRICT,
    amount     numeric(6,2) NOT NULL,
    paid_date  date,
    CONSTRAINT fine_amount_nonneg CHECK (amount >= 0)
);
 