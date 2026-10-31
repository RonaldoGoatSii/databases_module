# Session 05 challenge: degrees of separation

## Files

- `degrees.sql`: task 2 (actors within 3 degrees of actor 1, with the shortest distance) and task 3 (shortest path from actor 1 to actor 200, within 5 degrees).

## How to run

From the repository root, on a fresh copy of Pagila:

```bash
./scripts/create-db.sh ch05 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ch05 -v ON_ERROR_STOP=1 < exercises/05-queries/challenge/degrees.sql > /tmp/ch05_output.txt 2>&1
echo "exit: $?"
grep -c "ERROR" /tmp/ch05_output.txt
```

The file has two queries, so the output has two result tables. Expected: `exit: 0` and `0` errors.

## How the query is built

1. **Edges (task 1).** `pair_count` counts the films shared by each pair of actors, using `actor_id > actor_id` so each pair appears once, and keeps pairs with `HAVING COUNT(*) >= 3`. `edge` then lists each pair in both directions with `UNION ALL`, so a walk can go either way.
2. **Walk.** `walk` starts from actor 1 with one row per first step. Each row carries the current actor, the distance and the full path as an array (`ARRAY[1, ...]`). Each recursive step adds one edge.
3. **Shortest distance.** One actor can be reached by several paths. The final `MIN(distance)` keeps the shortest.

## How the query avoids running forever

Two conditions stop the recursion:

- **Depth limit.** `WHERE w.distance < 3` (task 2) or `< 5` (task 3). No row is extended past that depth, so the recursion is always bounded.
- **No revisits.** `NOT (e.other_actor_id = ANY (w.path))`. The path stores every actor visited on that route, so a walk never returns to an actor it has already passed through. Without this, A → B → A → B … would go on until the depth limit, multiplying the number of rows.

The depth limit is what makes the query finish. The path check is what keeps it from producing cycles that only repeat actors.

In task 3, the recursion also stops extending a path once it reaches actor 200 (`w.actor_id <> 200`), because a longer path through the target cannot be the shortest.

## Result of task 2: actors at each distance

Number of actors at each distance from actor 1 (filled in from the output):

| Distance | Actors |
|---|---|
| 1 | 3 (actors 4, 20, 64) |
| 2 | 23 |
| 3 | 115 |

First rows of the result (filled in from the output):

```
 actor_id | first_name  |  last_name   | distance
----------+-------------+--------------+----------
        4 | JENNIFER    | DAVIS        |        1
       20 | LUCILLE     | TRACY        |        1
       64 | RAY         | JOHANSSON    |        1
        7 | GRACE       | MOSTEL       |        2
       13 | UMA         | WOOD         |        2
(141 rows)
```

## Result of task 3: shortest path from actor 1 to actor 200

```
 step | actor_id | first_name | last_name
------+----------+------------+-----------
    1 |        1 | PENELOPE   | GUINESS
    2 |       20 | LUCILLE    | TRACY
    3 |      107 | GINA       | DEGENERES
    4 |       76 | ANGELINA   | ASTAIRE
    5 |      200 | THORA      | TEMPLE
(5 rows)
```

Actor 200 is not within 3 degrees (it is not in the task 2 result), so the shortest path has 4 connections. The path `1 → 20 → 107 → 76 → 200` has 4 connections, so it is a shortest path.

The result has one row per actor on the path, with `step` 1 for actor 1 and the last step for actor 200. The number of degrees is the last `step` minus 1.

## Checks that the result is correct

Run after the main query. They are not in `degrees.sql`.

**1. The edges are symmetric.** `edge` has exactly twice as many rows as `pair_count`. Result:

```
 edge_rows | expected_rows
-----------+---------------
      1650 |          1650
(1 row)
```

**2. Distance 1 matches the direct neighbours of actor 1.** Result: 3, the same 3 actors (4, 20, 64) that appear at distance 1 in task 2.

```
 neighbours_of_1
-----------------
               3
(1 row)
```

**3. The path in task 3 is valid.** Each consecutive pair of actors in the path shared at least 3 films: 1 → 20 → 107 → 76 → 200. Each step is an edge of `edge`.

**4. The path is shortest.** Actor 200 does not appear in task 2 (distance up to 3), so no path to it has fewer than 4 connections. The path found has 4, so it is shortest.