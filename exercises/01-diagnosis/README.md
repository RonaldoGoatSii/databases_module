# Session 01: Database Engines and Diagnosis - Solutions

## 1. Environment Status (`docker compose ps`)
*A screenshot showing the three database engines (PostgreSQL, MongoDB, and Redis) running and in a healthy state.*

*(Insert your screenshot here, e.g., in an `img/` folder: `![Docker Compose Status](img/docker-compose-status.png)`)*

---

## Exercise 2: The Database Data Model (`s01_fastapi`)

### Table List and Attributes
The relational model centralized and generated via `app/clients.py` in PostgreSQL contains the following tables:

* **Table: `hello`**
  * `id` (`INTEGER`): Primary Key, automatically generated sequentially (`GENERATED ALWAYS AS IDENTITY PRIMARY KEY`).
  * `msg` (`TEXT`): Message or record content (`NOT NULL`).
  * `created_at` (`TIMESTAMPTZ`): Creation timestamp with a default value (`NOT NULL DEFAULT now()`).

* **Table: `items`**
  * `id` (`INTEGER`): Primary Key, automatically generated sequentially (`GENERATED ALWAYS AS IDENTITY PRIMARY KEY`).
  * `hello_id` (`INTEGER`): Foreign Key referencing `hello(id)` (`REFERENCES hello(id) ON DELETE CASCADE`).
  * `name` (`TEXT`): Name of the item (`NOT NULL`).
  * `price` (`NUMERIC(10, 2)`): Price of the item (`NOT NULL`).
  * `created_at` (`TIMESTAMPTZ`): Creation timestamp with a default value (`NOT NULL DEFAULT now()`).

### Relationships
* **`hello` 1 <───> `items` (One-to-Many):** One record in the `hello` table can have multiple associated `items`. The `items.hello_id` foreign key links each item back to its corresponding parent record in `hello`.

---