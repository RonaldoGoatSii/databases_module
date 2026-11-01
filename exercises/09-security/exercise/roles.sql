-- roles.sql: least-privilege roles for ex09 (run as postgres, on the ex09 database)
--   docker compose exec -T postgres psql -U postgres -d ex09 -v ON_ERROR_STOP=1 < exercises/09-security/exercise/roles.sql
-- Passwords are not set here. Set them afterwards, interactively, so that they never appear in a file:
--   docker compose exec postgres psql -U postgres -d ex09
--   \password ex09_migrations
--   \password ex09_app
--   \password ex09_readonly

-- Login roles (the prefix ex09_ avoids clashes with other exercises; roles are server-wide)
CREATE ROLE ex09_migrations LOGIN;
CREATE ROLE ex09_app LOGIN;
CREATE ROLE ex09_readonly LOGIN;

-- The migrations role owns the database and the schema objects it creates
ALTER DATABASE ex09 OWNER TO ex09_migrations;
GRANT CREATE, USAGE ON SCHEMA public TO ex09_migrations;

-- Nobody but the owners can create objects in public
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- Connect and use the schema
GRANT CONNECT ON DATABASE ex09 TO ex09_app, ex09_readonly;
GRANT USAGE ON SCHEMA public TO ex09_app, ex09_readonly;

-- ex09_app: read and write the data, no DDL
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ex09_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO ex09_app;

-- ex09_readonly: read only
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ex09_readonly;

-- Tables and sequences created later by ex09_migrations get the same grants
ALTER DEFAULT PRIVILEGES FOR ROLE ex09_migrations IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ex09_app;
ALTER DEFAULT PRIVILEGES FOR ROLE ex09_migrations IN SCHEMA public
    GRANT USAGE ON SEQUENCES TO ex09_app;
ALTER DEFAULT PRIVILEGES FOR ROLE ex09_migrations IN SCHEMA public
    GRANT SELECT ON TABLES TO ex09_readonly;