# Session 09 exercise: least privilege and injection-safe writes

## Files

- `roles.sql`: the three login roles, the owner of the database, the grants and the default privileges (task 1).
- `proofs.sql`: the four proofs of task 2, each run as a restricted role with `SET ROLE`.
- `api/main.py`: the API with the three endpoints of task 3 (FastAPI, psycopg, pymongo, redis).
- `api/.env.example`: the variables the API needs. Copy it to `api/.env` and fill in the passwords.
- `api/pyproject.toml`: the uv project.

**Assumption about Mongo and Redis users.** The exercise text refers to "the users of tasks 1 and 3", but it does not define the MongoDB and Redis users. I used `ex09_app` in both, with the smallest rights that the endpoints need: `readWrite` on the database `ex09` in MongoDB, and only `INCR` on keys `counter:*` in Redis.

## 1. Set up the database and the roles

```bash
./scripts/create-db.sh ex09 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex09 -v ON_ERROR_STOP=1 < exercises/09-security/exercise/roles.sql
```

Set the passwords interactively, so that they are not in a file or in the shell history:

```bash
docker compose exec postgres psql -U postgres -d ex09
# inside psql:
\password ex09_migrations
\password ex09_app
\password ex09_readonly
\q
```

## 2. Proofs

```bash
docker compose exec -T postgres psql -U postgres -d ex09 < exercises/09-security/exercise/proofs.sql
```

Output:

```
SET
ERROR:  must be owner of table film
RESET
SET
INSERT 0 1
RESET
SET
 count
-------
  1000
(1 row)

RESET
SET
ERROR:  permission denied for table actor
RESET
```

All four proofs match the expected outcome: `ex09_app` cannot drop `film` but can insert into `actor`, and `ex09_readonly` can count rows in `film` but cannot insert into `actor`.

## 3. Users for MongoDB and Redis

MongoDB (create the user in the database `ex09`, with the root user of the compose file):

```bash
docker compose exec mongo mongosh -u "$MONGO_ROOT_USER" -p "$MONGO_ROOT_PASSWORD" --authenticationDatabase admin --eval '
  db.getSiblingDB("ex09").createUser({
    user: "ex09_app",
    pwd: passwordPrompt(),
    roles: [{ role: "readWrite", db: "ex09" }]
  })'
```

Redis (an ACL user that can only run `INCR` on keys `counter:*`):

```bash
read -rs -p "Password for ex09_app: " EX09_REDIS_PW; echo
docker compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning \
  ACL SETUSER ex09_app on ">$EX09_REDIS_PW" "~counter:*" "+incr"
unset EX09_REDIS_PW
```

**Keeping the Redis ACL after a restart.** `ACL SETUSER` changes exist only in memory, so they are lost when Redis restarts. To keep them, configure an ACL file: start Redis with `--aclfile /data/users.acl` (in `docker-compose.yml`, in the `command` of the `redis` service), and run `ACL SAVE` after creating the user. The file is in the `redis_data` volume, so it survives restarts.

## 4. Run the API

```bash
cd exercises/09-security/exercise/api
cp .env.example .env          # then fill in the passwords
set -a; source .env; set +a
uv sync
uv run uvicorn main:app --port 8000
```

Keep this terminal open and use another terminal for the requests.

## 5. Requests and responses

The three endpoints, each on its own engine.

**Normal use:**

```bash
curl -s -X POST http://127.0.0.1:8000/actors -H 'Content-Type: application/json' \
     -d '{"first_name": "Ada", "last_name": "Lovelace"}' -w '\nHTTP %{http_code}\n'

curl -s -X POST http://127.0.0.1:8000/notes -H 'Content-Type: application/json' \
     -d '{"customer_id": 1, "text": "called back"}' -w '\nHTTP %{http_code}\n'

curl -s -X POST http://127.0.0.1:8000/counters/visits -w '\nHTTP %{http_code}\n'
```

Output:

```
{"actor_id":203}
HTTP 201

{"id":"6ae70a1441cb1226584109b1"}
HTTP 201

{"name":"visits","value":1}
HTTP 200
```

**Injection attempt in `/actors`.** The text must be stored as it is, and the table must still exist:

```bash
curl -s -X POST http://127.0.0.1:8000/actors -H 'Content-Type: application/json' \
     -d '{"first_name": "x'"'"'); DROP TABLE actor; --", "last_name": "y"}' -w '\nHTTP %{http_code}\n'

docker compose exec -T postgres psql -U postgres -d ex09 \
  -c "SELECT actor_id, first_name, last_name FROM actor WHERE last_name = 'y';" \
  -c "SELECT count(*) AS actor_rows FROM actor;"
```

Output:

```
 actor_id |        first_name         | last_name
----------+---------------------------+-----------
      204 | x'); DROP TABLE actor; -- | y
(1 row)

 actor_rows
------------
        202
(1 row)
```

The text was stored exactly as it was sent, and `actor` still exists with 202 rows. The injection was just text.

**Operator injection in `/notes`.** A dictionary as `text` must be rejected with `422`:

```bash
curl -s -X POST http://127.0.0.1:8000/notes -H 'Content-Type: application/json' \
     -d '{"customer_id": 1, "text": {"$ne": null}}' -w '\nHTTP %{http_code}\n'
```

Output:

```
{"detail":[{"type":"string_type","loc":["body","text"],"msg":"Input should be a valid string","input":{"$ne":null}}]}
HTTP 422
```

**Invalid counter names:**

```bash
curl -s -X POST 'http://127.0.0.1:8000/counters/a*' -w '\nHTTP %{http_code}\n'
curl -s -X POST 'http://127.0.0.1:8000/counters/x:y' -w '\nHTTP %{http_code}\n'
```

Output:

```
{"detail":[{"type":"string_pattern_mismatch","loc":["path","name"],"msg":"String should match pattern '^[a-z0-9_-]{1,32}$'","input":"a*","ctx":{"pattern":"^[a-z0-9_-]{1,32}$"}}]}
HTTP 422

{"detail":[{"type":"string_pattern_mismatch","loc":["path","name"],"msg":"String should match pattern '^[a-z0-9_-]{1,32}$'","input":"x:y","ctx":{"pattern":"^[a-z0-9_-]{1,32}$"}}]}
HTTP 422
```

## 6. What was stored

After the requests, check the Mongo document and the Redis key:

```bash
docker compose exec mongo mongosh -u ex09_app -p "$MONGO_PASSWORD" --authenticationDatabase ex09 ex09 --eval 'db.notes.find().toArray()'
docker compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning --user ex09_app GET counter:visits
```

Output:

```
[
  {
    _id: ObjectId('6ae70a1441cb1226584109b1'),
    customer_id: 1,
    text: 'called back',
    created_at: ISODate('2026-11-01T09:44:52.713Z')
  }
]

(error) NOPERM User ex09_app has no permissions to run the 'get' command
```

The note is stored in MongoDB. The `GET` is refused on purpose: `ex09_app` only has `INCR` on `counter:*`, so it cannot read counters. The value 1 was already returned by the API when the counter was incremented. To see the stored value with the administrative user, use the password from `REDIS_PASSWORD` in the root `.env`:

```bash
docker compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning GET counter:visits
```

## Why the API is safe

- **SQL:** the `INSERT` uses placeholders (`%s`) and the values are passed separately from the SQL text, so the driver never puts user input into the statement. The payload `'); DROP TABLE actor; --` is only a string.
- **NoSQL:** the note's `text` field must be a `StrictStr`, and `customer_id` a `StrictInt`. A dictionary such as `{"$ne": null}` is rejected by the validation before any query runs.
- **Redis:** the counter name must match `^[a-z0-9_-]{1,32}$` (checked by FastAPI as a path parameter, returning `422`). Characters such as `*` or `:` never reach the key. The key itself is built as `counter:` plus a name that has already been validated.
- **Credentials:** every password comes from an environment variable (`.env`, never committed); none is in the code.
- **Least privilege:** `ex09_app` can read and write the data, but not drop tables (proof 1). `ex09_readonly` can only read (proof 3 and 4). The Mongo and Redis users can only do what the endpoints need.