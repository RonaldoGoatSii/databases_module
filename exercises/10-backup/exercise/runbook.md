# Runbook: restore after an accidental delete on `ex10`

## When to use it

Use this runbook when rows were deleted by mistake from `ex10` (or the production equivalent) and the data must come back, without dropping or recreating the database.

## Prerequisites

- The database is running: `docker compose ps` shows `postgres` as `healthy`.
- A custom-format backup exists in `backups/` and was taken before the incident (its file name and time are recorded in the table in section "Times and counts").
- The restore is done into a scratch database (`ex10_restore`), so that the live database is never dropped.
- Disk space for the scratch database (about the size of the backup).

## Commands, in order

All commands are run from the **repository root** unless stated otherwise.

### Step 1: row counts before the backup

```bash
for t in payment film_actor film_category; do
  docker compose exec -T postgres psql -U postgres -d ex10 -tAc "SELECT '$t', count(*) FROM $t;"
done
```

### Step 2: backup (record the time)

```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
time docker compose exec -T postgres pg_dump -U postgres -d ex10 -Fc > exercises/10-backup/exercise/backups/ex10_before_incident.dump
ls -lh exercises/10-backup/exercise/backups/
```

### Step 3: normal activity, then the incident

```bash
docker compose exec -T postgres psql -U postgres -d ex10 -v ON_ERROR_STOP=1 < exercises/10-backup/exercise/activity.sql
docker compose exec -T postgres psql -U postgres -d ex10 -v ON_ERROR_STOP=1 < exercises/10-backup/exercise/disaster.sql
```

Row counts after the incident, and the payments created by `activity.sql` that are now gone:

```bash
for t in payment film_actor film_category; do
  docker compose exec -T postgres psql -U postgres -d ex10 -tAc "SELECT '$t', count(*) FROM $t;"
done
```

### Step 4: restore into a scratch database (time the whole restore)

```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
time (
  docker compose exec -T postgres createdb -U postgres ex10_restore
  docker compose exec -T postgres pg_restore -U postgres -d ex10_restore --no-owner < exercises/10-backup/exercise/backups/ex10_before_incident.dump
)
```

### Step 5: copy back the deleted rows into `ex10`

Each command copies, from the scratch database, exactly the rows that the incident deleted. Because all those rows are gone from `ex10`, nothing is duplicated.

```bash
docker compose exec -T postgres psql -U postgres -d ex10_restore -c "\copy (SELECT * FROM payment WHERE payment_date >= '2026-01-01') TO STDOUT" \
  | docker compose exec -T postgres psql -U postgres -d ex10 -c "\copy payment FROM STDIN"

docker compose exec -T postgres psql -U postgres -d ex10_restore -c "\copy (SELECT * FROM film_actor WHERE actor_id <= 50) TO STDOUT" \
  | docker compose exec -T postgres psql -U postgres -d ex10 -c "\copy film_actor FROM STDIN"

docker compose exec -T postgres psql -U postgres -d ex10_restore -c "\copy (SELECT * FROM film_category WHERE category_id = 1) TO STDOUT" \
  | docker compose exec -T postgres psql -U postgres -d ex10 -c "\copy film_category FROM STDIN"
```

Remove the scratch database:

```bash
docker compose exec -T postgres dropdb -U postgres ex10_restore
```

## Verify the restore

1. The three counts must equal the counts of Step 1 (before the backup).

```bash
for t in payment film_actor film_category; do
  docker compose exec -T postgres psql -U postgres -d ex10 -tAc "SELECT '$t', count(*) FROM $t;"
done
```

2. The payments of `activity.sql` are the only ones still lost (they were created after the backup):

```sql
SELECT count(*) AS lost_payments
FROM payment
WHERE payment_date = timestamptz '2026-07-30 12:00+00' AND amount = 1.99;
```

Expected: `0` (the 5 payments are not in the backup and not in `ex10`).

## Times and counts

| Item | Value |
|---|---|
| Backup file | `backups/ex10_before_incident.dump` (4.4 MB) |
| Backup time (UTC) | file written at 10:34 (local container time, dump took 0.7 s) |
| Row counts before backup (payment, film_actor, film_category) | 51061, 5462, 2367 (derived: counts after the incident plus the rows the incident deleted; the step 1 count was not recorded) |
| Row counts after the incident | 45780, 4135, 2218 |
| Rows deleted by the incident | 5286 payments (5281 from the backup plus the 5 from `activity.sql`), 1327 film_actor, 149 film_category |
| Row counts after restore | 51061, 5462, 2367 (equal to the counts before the backup) |
| Restore time, real RTO (Step 4 + Step 5) | 4.25 s (from 2026-11-02T10:41:01Z to 10:41:05Z, `real` of `time`) |
| Data lost between backup and incident, real RPO | 5 payments created by `activity.sql` (amount 1.99, 2026-07-30 12:00+00). Query: `SELECT count(*) FROM payment WHERE payment_date = timestamptz '2026-07-30 12:00+00' AND amount = 1.99;` returned 5 before the incident and 0 after the restore |

**Verification result:** the three tables have the same counts as before the backup, and the five payments of `activity.sql` are still lost, as expected, because they were created after the backup.

## What to change to lose less

- **More frequent backups** (for example hourly), so the window of lost work is smaller.
- **Point-in-time recovery**: keep WAL archives with `archive_mode`, so the database can be restored to the second before the `DELETE`, not only to the last backup.
- **Guard against accidental deletes**: run destructive changes in transactions with a review step, and restrict `DELETE` to the roles that need it (see session 09).
- **Test the restore regularly**, as in this runbook, so that the restore time (RTO) is known and not guessed.