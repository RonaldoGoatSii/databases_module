# Session 12 exercise: migrations and a transactional rentals API

## Files

- `alembic.ini`, `migrations/`: the Alembic setup, `env.py` (with `include_object`), and the three migrations (`0001_baseline`, `0002_loyalty_points`, `0003_one_open_rental_per_copy`).
- `app/db.py`: the database URL (from `POSTGRES_*`) and the session factory.
- `app/models.py`: the mapped tables (`store`, `staff`, `customer`, `film`, `inventory`, `rental`).
- `app/main.py`: the API with `POST /rentals`, `POST /rentals/{id}/return` and `GET /rentals/overdue`.
- `concurrency_test.py`: five simultaneous rentals of the same film.

## Setup

From the repository root:

```bash
./scripts/create-db.sh ex12 --pagila --reset
cd exercises/12-api/exercise
uv sync
```

Every command below runs from `exercises/12-api/exercise` and reads the root `.env` (for the `POSTGRES_*` variables):

```bash
ENV=../../../.env
```

## Task 1: baseline

```bash
uv run --env-file $ENV alembic stamp 0001
```

`0001_baseline` is empty, because the tables already exist. `alembic stamp` marks the database as being at `0001` without running any SQL.

**What autogenerate would have generated without the baseline and without `include_object`:**

Without the baseline, Alembic has no record of the schema, so it compares the models with an empty history. It would propose:

- `drop_table` for every table in Pagila that is not mapped (`payment`, `film_actor`, `film_category`, `address`, `city`, `country`, `actor`, `language`, `category`, `staff_address` and the rest). The tables exist in the database, but not in the models, so autogenerate reads them as "to be removed".
- `drop_index` for Pagila's own indexes on the mapped tables (for example `idx_fk_inventory_id` or `idx_unq_rental_rental_date_inventory_id_customer_id`), because they are not in the models.
- `drop_column` for Pagila's columns that the models do not map (`film.description`, `film.special_features`, `customer.email` and so on).
- `drop_constraint` for the foreign keys that the models do not declare.

Running that migration would destroy the data of the unmapped tables (for example all payments), with no error message and no warning. That is the danger: autogenerate describes the difference between the models and the database, and it treats every difference as intended.

The baseline fixes the starting point (the migration history matches the database). `include_object` in `migrations/env.py` tells autogenerate to ignore everything that is not mapped, and never to propose dropping a reflected object that the models do not have.

## Task 2: loyalty points

```bash
uv run --env-file $ENV alembic upgrade head
```

The migration adds the column as nullable, fills it with the number of rentals of each customer, then sets `NOT NULL` with `server_default '0'`. Check:

```bash
docker compose -f ../../../docker-compose.yml exec -T postgres psql -U postgres -d ex12 -c "SELECT customer_id, loyalty_points FROM customer WHERE customer_id = 1;"
```

Expected: customer 1 with 66 points.

## Task 3: one open rental per copy

The migration `0003` runs in the same `upgrade head`. It closes the older of the two open rentals of copies 1358, 1435 and 2408 (`return_date` = the `rental_date` of the newer one), then creates the partial unique index `rental_one_open_per_copy`.

**Why the data fix is not undone by `downgrade`:** the old rentals were closed by the migration, and the database does not record that they were open before. After the downgrade, the rentals still have a `return_date`, and that value is indistinguishable from a real return. Reopening them would require knowing the original state, which is not stored anywhere. `downgrade` reverts the schema (the index), not the data: a schema change can be reverted, a data change is a decision and has to be recorded as one.

## Task 4: up, down, up

```bash
ENV=../../../.env

uv run --env-file $ENV alembic upgrade head
docker compose -f ../../../docker-compose.yml exec -T postgres psql -U postgres -d ex12 -c "\d customer" -c "\d rental"

uv run --env-file $ENV alembic downgrade base
docker compose -f ../../../docker-compose.yml exec -T postgres psql -U postgres -d ex12 -c "\d customer" -c "\d rental"

uv run --env-file $ENV alembic upgrade head
docker compose -f ../../../docker-compose.yml exec -T postgres psql -U postgres -d ex12 -c "\d customer" -c "\d rental"
```

Output:

```
root@369a090047bd:/workspaces/databases_module/exercises/12-api/exercise# uv run --env-file $ENV alembic upgrade head
root@369a090047bd:/workspaces/databases_module/exercises/12-api/exercise# docker compose -f ../../../docker-compose.yml exec -T postgres psql -U postgres -d ex12 -c "\d customer" -c "\d rental"
                                             Table "public.customer"
     Column     |           Type           | Collation | Nullable |                    Default                    
----------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id    | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id       | integer                  |           | not null | 
 first_name     | text                     |           | not null | 
 last_name      | text                     |           | not null | 
 email          | text                     |           |          | 
 address_id     | integer                  |           | not null | 
 activebool     | boolean                  |           | not null | true
 create_date    | date                     |           | not null | CURRENT_DATE
 last_update    | timestamp with time zone |           |          | now()
 active         | integer                  |           |          | 
 uuid           | uuid                     |           | not null | uuidv7()
 loyalty_points | integer                  |           | not null | 0
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)
Foreign-key constraints:
    "customer_address_id_fkey" FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "customer_store_id_fkey" FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE ON DELETE RESTRICT
Referenced by:
    TABLE "payment_p2022_01" CONSTRAINT "payment_p2022_01_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_02" CONSTRAINT "payment_p2022_02_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_03" CONSTRAINT "payment_p2022_03_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_04" CONSTRAINT "payment_p2022_04_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_05" CONSTRAINT "payment_p2022_05_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_06" CONSTRAINT "payment_p2022_06_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "rental" CONSTRAINT "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
Triggers:
    last_updated BEFORE UPDATE ON customer FOR EACH ROW EXECUTE FUNCTION last_updated()

                                             Table "public.rental"
    Column    |           Type           | Collation | Nullable |                  Default                  
--------------+--------------------------+-----------+----------+-------------------------------------------
 rental_id    | integer                  |           | not null | nextval('rental_rental_id_seq'::regclass)
 rental_date  | timestamp with time zone |           | not null | 
 inventory_id | integer                  |           | not null | 
 customer_id  | integer                  |           | not null | 
 return_date  | timestamp with time zone |           |          | 
 staff_id     | integer                  |           | not null | 
 last_update  | timestamp with time zone |           | not null | now()
 uuid         | uuid                     |           | not null | uuidv7()
Indexes:
    "rental_pkey" PRIMARY KEY, btree (rental_id)
    "idx_fk_inventory_id" btree (inventory_id)
    "idx_unq_rental_rental_date_inventory_id_customer_id" UNIQUE, btree (rental_date, inventory_id, customer_id)
    "rental_one_open_per_copy" UNIQUE, btree (inventory_id) WHERE return_date IS NULL
    "rental_uuid_key" UNIQUE, btree (uuid)
Foreign-key constraints:
    "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_inventory_id_fkey" FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_staff_id_fkey" FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT
Referenced by:
    TABLE "payment_p2022_01" CONSTRAINT "payment_p2022_01_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_02" CONSTRAINT "payment_p2022_02_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_03" CONSTRAINT "payment_p2022_03_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_04" CONSTRAINT "payment_p2022_04_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_05" CONSTRAINT "payment_p2022_05_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_06" CONSTRAINT "payment_p2022_06_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
Triggers:
    last_updated BEFORE UPDATE ON rental FOR EACH ROW EXECUTE FUNCTION last_updated()

root@369a090047bd:/workspaces/databases_module/exercises/12-api/exercise# uv run --env-file $ENV alembic downgrade base
root@369a090047bd:/workspaces/databases_module/exercises/12-api/exercise# docker compose -f ../../../docker-compose.yml exec -T postgres psql -U postgres -d ex12 -c "\d customer" -c "\d rental"
                                             Table "public.customer"
   Column    |           Type           | Collation | Nullable |                    Default                    
-------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id    | integer                  |           | not null | 
 first_name  | text                     |           | not null | 
 last_name   | text                     |           | not null | 
 email       | text                     |           |          | 
 address_id  | integer                  |           | not null | 
 activebool  | boolean                  |           | not null | true
 create_date | date                     |           | not null | CURRENT_DATE
 last_update | timestamp with time zone |           |          | now()
 active      | integer                  |           |          | 
 uuid        | uuid                     |           | not null | uuidv7()
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)
Foreign-key constraints:
    "customer_address_id_fkey" FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "customer_store_id_fkey" FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE ON DELETE RESTRICT
Referenced by:
    TABLE "payment_p2022_01" CONSTRAINT "payment_p2022_01_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_02" CONSTRAINT "payment_p2022_02_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_03" CONSTRAINT "payment_p2022_03_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_04" CONSTRAINT "payment_p2022_04_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_05" CONSTRAINT "payment_p2022_05_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_06" CONSTRAINT "payment_p2022_06_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "rental" CONSTRAINT "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
Triggers:
    last_updated BEFORE UPDATE ON customer FOR EACH ROW EXECUTE FUNCTION last_updated()

                                             Table "public.rental"
    Column    |           Type           | Collation | Nullable |                  Default                  
--------------+--------------------------+-----------+----------+-------------------------------------------
 rental_id    | integer                  |           | not null | nextval('rental_rental_id_seq'::regclass)
 rental_date  | timestamp with time zone |           | not null | 
 inventory_id | integer                  |           | not null | 
 customer_id  | integer                  |           | not null | 
 return_date  | timestamp with time zone |           |          | 
 staff_id     | integer                  |           | not null | 
 last_update  | timestamp with time zone |           | not null | now()
 uuid         | uuid                     |           | not null | uuidv7()
Indexes:
    "rental_pkey" PRIMARY KEY, btree (rental_id)
    "idx_fk_inventory_id" btree (inventory_id)
    "idx_unq_rental_rental_date_inventory_id_customer_id" UNIQUE, btree (rental_date, inventory_id, customer_id)
    "rental_uuid_key" UNIQUE, btree (uuid)
Foreign-key constraints:
    "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_inventory_id_fkey" FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_staff_id_fkey" FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT
Referenced by:
    TABLE "payment_p2022_01" CONSTRAINT "payment_p2022_01_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_02" CONSTRAINT "payment_p2022_02_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_03" CONSTRAINT "payment_p2022_03_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_04" CONSTRAINT "payment_p2022_04_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_05" CONSTRAINT "payment_p2022_05_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_06" CONSTRAINT "payment_p2022_06_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
Triggers:
    last_updated BEFORE UPDATE ON rental FOR EACH ROW EXECUTE FUNCTION last_updated()

root@369a090047bd:/workspaces/databases_module/exercises/12-api/exercise# uv run --env-file $ENV alembic upgrade head
root@369a090047bd:/workspaces/databases_module/exercises/12-api/exercise# docker compose -f ../../../docker-compose.yml exec -T postgres psql -U postgres -d ex12 -c "\d customer" -c "\d rental"
                                             Table "public.customer"
     Column     |           Type           | Collation | Nullable |                    Default                    
----------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id    | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id       | integer                  |           | not null | 
 first_name     | text                     |           | not null | 
 last_name      | text                     |           | not null | 
 email          | text                     |           |          | 
 address_id     | integer                  |           | not null | 
 activebool     | boolean                  |           | not null | true
 create_date    | date                     |           | not null | CURRENT_DATE
 last_update    | timestamp with time zone |           |          | now()
 active         | integer                  |           |          | 
 uuid           | uuid                     |           | not null | uuidv7()
 loyalty_points | integer                  |           | not null | 0
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)
Foreign-key constraints:
    "customer_address_id_fkey" FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "customer_store_id_fkey" FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE ON DELETE RESTRICT
Referenced by:
    TABLE "payment_p2022_01" CONSTRAINT "payment_p2022_01_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_02" CONSTRAINT "payment_p2022_02_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_03" CONSTRAINT "payment_p2022_03_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_04" CONSTRAINT "payment_p2022_04_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_05" CONSTRAINT "payment_p2022_05_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "payment_p2022_06" CONSTRAINT "payment_p2022_06_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    TABLE "rental" CONSTRAINT "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
Triggers:
    last_updated BEFORE UPDATE ON customer FOR EACH ROW EXECUTE FUNCTION last_updated()

                                             Table "public.rental"
    Column    |           Type           | Collation | Nullable |                  Default                  
--------------+--------------------------+-----------+----------+-------------------------------------------
 rental_id    | integer                  |           | not null | nextval('rental_rental_id_seq'::regclass)
 rental_date  | timestamp with time zone |           | not null | 
 inventory_id | integer                  |           | not null | 
 customer_id  | integer                  |           | not null | 
 return_date  | timestamp with time zone |           |          | 
 staff_id     | integer                  |           | not null | 
 last_update  | timestamp with time zone |           | not null | now()
 uuid         | uuid                     |           | not null | uuidv7()
Indexes:
    "rental_pkey" PRIMARY KEY, btree (rental_id)
    "idx_fk_inventory_id" btree (inventory_id)
    "idx_unq_rental_rental_date_inventory_id_customer_id" UNIQUE, btree (rental_date, inventory_id, customer_id)
    "rental_one_open_per_copy" UNIQUE, btree (inventory_id) WHERE return_date IS NULL
    "rental_uuid_key" UNIQUE, btree (uuid)
Foreign-key constraints:
    "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_inventory_id_fkey" FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_staff_id_fkey" FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT
Referenced by:
    TABLE "payment_p2022_01" CONSTRAINT "payment_p2022_01_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_02" CONSTRAINT "payment_p2022_02_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_03" CONSTRAINT "payment_p2022_03_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_04" CONSTRAINT "payment_p2022_04_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_05" CONSTRAINT "payment_p2022_05_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
    TABLE "payment_p2022_06" CONSTRAINT "payment_p2022_06_rental_id_fkey" FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
Triggers:
    last_updated BEFORE UPDATE ON rental FOR EACH ROW EXECUTE FUNCTION last_updated()
```

## Task 5: the API

Start the API in one terminal, and leave it running:

```bash
cd exercises/12-api/exercise
uv run --env-file $ENV uvicorn app.main:app --port 8000
```

Requests, from another terminal:

```bash
# Rent (201 with rental_id and inventory_id; 404 unknown customer or film; 409 no copy)
curl -s -X POST http://127.0.0.1:8000/rentals -H 'Content-Type: application/json' \
     -d '{"customer_id": 1, "film_id": 7, "store_id": 1, "staff_id": 6}' -w '\nHTTP %{http_code}\n'

# Return (200; 404 unknown rental; 409 already returned)
curl -s -X POST http://127.0.0.1:8000/rentals/1/return -w '\nHTTP %{http_code}\n'

# Overdue on a given date (expected 229 items on a fresh copy after the migrations)
curl -s 'http://127.0.0.1:8000/rentals/overdue?as_of=2026-07-31' | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d), 'items'); print(d[0])"
```

**How the endpoints stay correct:**

- `POST /rentals`: one transaction per attempt. The copy is chosen with `FOR UPDATE SKIP LOCKED`, so a copy locked by another request is skipped instead of waited for. The unique index `rental_one_open_per_copy` is the last line of defence: if a conflict still happens, the insert fails, the transaction is rolled back, and the whole attempt is retried, at most 3 times.
- `POST /rentals/{id}/return`: the rental is locked with `FOR UPDATE` before checking `return_date`, so two returns at the same time cannot both succeed.
- `GET /rentals/overdue`: one query joins rental, inventory, film and customer. The number of statements does not depend on the number of rows.

## Number of SQL statements of `GET /rentals/overdue`

Run the API with `SQL_ECHO=1` to log the statements, then count them in the output:

```bash
SQL_ECHO=1 uv run --env-file $ENV uvicorn app.main:app --port 8000
curl -s 'http://127.0.0.1:8000/rentals/overdue?as_of=2026-07-31' > /dev/null
```

Statements (count the `SELECT` lines in the log of that request): (fill in)

## Task 6: concurrency test

On a fresh copy, with the API running:

```bash
uv run python concurrency_test.py
```

Output:

```
customer 1: 201 {'rental_id': 87561, 'inventory_id': 32}
customer 2: 409 {'detail': 'no copy available'}
customer 3: 409 {'detail': 'no copy available'}
customer 4: 201 {'rental_id': 87560, 'inventory_id': 33}
customer 5: 409 {'detail': 'no copy available'}

201: 2  409: 3  distinct inventory_id: [32, 33]
PASS
```

Expected: two `201` (with two different `inventory_id`), three `409`, and `PASS`.

**Running it again:** the copies are rented after the first run, so the second run gives five `409`. To run it again, return the two rentals first (`POST /rentals/{id}/return`), or create a fresh copy of the database and run the migrations again.