-- proofs.sql: each statement is run as a restricted role with SET ROLE, and then RESET ROLE.
-- Run as postgres, WITHOUT ON_ERROR_STOP, so that the expected errors do not stop the script:
--   docker compose exec -T postgres psql -U postgres -d ex09 < exercises/09-security/exercise/proofs.sql

-- Expected: ERROR:  must be owner of table film   (ex09_app cannot drop tables)
SET ROLE ex09_app;
DROP TABLE film;
RESET ROLE;

-- Expected: INSERT 0 1   (ex09_app can insert rows)
SET ROLE ex09_app;
INSERT INTO actor (first_name, last_name) VALUES ('X', 'Y');
RESET ROLE;

-- Expected: a count of rows   (ex09_readonly can read)
SET ROLE ex09_readonly;
SELECT count(*) FROM film;
RESET ROLE;

-- Expected: ERROR:  permission denied for table actor   (ex09_readonly cannot insert)
SET ROLE ex09_readonly;
INSERT INTO actor (first_name, last_name) VALUES ('X', 'Y');
RESET ROLE;