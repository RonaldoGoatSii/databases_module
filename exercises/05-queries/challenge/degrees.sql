WITH RECURSIVE
pair_count AS (
    SELECT fa1.actor_id AS a1,
           fa2.actor_id AS a2,
           COUNT(*)     AS films
    FROM film_actor fa1
    JOIN film_actor fa2 ON fa2.film_id = fa1.film_id
                       AND fa2.actor_id > fa1.actor_id     -- each pair once here...
    GROUP BY fa1.actor_id, fa2.actor_id
    HAVING COUNT(*) >= 3
),
edge(actor_id, other_actor_id) AS (
    SELECT a1, a2 FROM pair_count
    UNION ALL
    SELECT a2, a1 FROM pair_count                          -- ...and both directions here
),
-- Walks from actor 1. Each row is one path: the current actor, its distance and the full path.
walk AS (
    SELECT e.other_actor_id AS actor_id,
           1               AS distance,
           ARRAY[1, e.other_actor_id] AS path
    FROM edge e
    WHERE e.actor_id = 1
 
    UNION ALL
 
    SELECT e.other_actor_id,
           w.distance + 1,
           w.path || e.other_actor_id
    FROM walk w
    JOIN edge e ON e.actor_id = w.actor_id
    WHERE w.distance < 3                                    -- depth limit: stops at 3 degrees
      AND NOT (e.other_actor_id = ANY (w.path))             -- never revisit an actor on the same path
)
SELECT a.actor_id,
       a.first_name,
       a.last_name,
       MIN(w.distance) AS distance                          -- shortest among all paths found
FROM walk w
JOIN actor a ON a.actor_id = w.actor_id
WHERE w.actor_id <> 1                                       -- actor 1 is not in the result
GROUP BY a.actor_id, a.first_name, a.last_name
ORDER BY distance, a.actor_id;
 
-- ---------------------------------------------------------------
-- Task 3: shortest path from actor 1 to actor 200, as a list of actor names,
--         within 5 degrees. Empty result if there is no such path.
-- ---------------------------------------------------------------
WITH RECURSIVE
pair_count AS (
    SELECT fa1.actor_id AS a1,
           fa2.actor_id AS a2,
           COUNT(*)     AS films
    FROM film_actor fa1
    JOIN film_actor fa2 ON fa2.film_id = fa1.film_id
                       AND fa2.actor_id > fa1.actor_id
    GROUP BY fa1.actor_id, fa2.actor_id
    HAVING COUNT(*) >= 3
),
edge(actor_id, other_actor_id) AS (
    SELECT a1, a2 FROM pair_count
    UNION ALL
    SELECT a2, a1 FROM pair_count
),
walk AS (
    SELECT e.other_actor_id AS actor_id,
           1               AS distance,
           ARRAY[1, e.other_actor_id] AS path
    FROM edge e
    WHERE e.actor_id = 1
 
    UNION ALL
 
    SELECT e.other_actor_id,
           w.distance + 1,
           w.path || e.other_actor_id
    FROM walk w
    JOIN edge e ON e.actor_id = w.actor_id
    WHERE w.distance < 5
      AND w.actor_id <> 200                                 -- do not extend paths that already reached the target
      AND NOT (e.other_actor_id = ANY (w.path))
),
target AS (
    SELECT path
    FROM walk
    WHERE actor_id = 200
    ORDER BY distance, path                                 -- shortest first; ties resolved by path
    LIMIT 1
)
SELECT p.pos       AS step,                                 -- 1 = actor 1, last = actor 200
       a.actor_id,
       a.first_name,
       a.last_name
FROM target t
CROSS JOIN LATERAL unnest(t.path) WITH ORDINALITY AS p(actor_id, pos)
JOIN actor a ON a.actor_id = p.actor_id
ORDER BY p.pos;
 