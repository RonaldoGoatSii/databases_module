"""
Reads Pagila from PostgreSQL and writes three MongoDB collections: films, customers, rentals.
Idempotent: every document uses the Pagila id as _id, and is written with replace_one(upsert=True),
so running it twice leaves the same documents.
Run: uv run --env-file .env python load.py
"""
import os
from collections import defaultdict
from decimal import Decimal

import psycopg
from bson.decimal128 import Decimal128
from psycopg.rows import dict_row
from pymongo import MongoClient, ReplaceOne

RECENT_LIMIT = 10

FILMS_SQL = """
SELECT f.film_id, f.title, f.release_year, l.name AS language, f.rating::text AS rating,
       f.length, f.rental_duration, f.rental_rate,
       COALESCE((SELECT array_agg(c.name ORDER BY c.name)
                 FROM film_category fc JOIN category c ON c.category_id = fc.category_id
                 WHERE fc.film_id = f.film_id), '{}') AS categories,
       COALESCE((SELECT json_agg(json_build_object('actor_id', a.actor_id,
                                                   'name', a.first_name || ' ' || a.last_name)
                                 ORDER BY a.actor_id)
                 FROM film_actor fa JOIN actor a ON a.actor_id = fa.actor_id
                 WHERE fa.film_id = f.film_id), '[]'::json) AS actors
FROM film f JOIN language l ON l.language_id = f.language_id
ORDER BY f.film_id
"""

CUSTOMERS_SQL = """
SELECT c.customer_id, c.first_name, c.last_name, c.email, c.store_id, ci.city, co.country
FROM customer c
JOIN address a ON a.address_id = c.address_id
JOIN city ci ON ci.city_id = a.city_id
JOIN country co ON co.country_id = ci.country_id
ORDER BY c.customer_id
"""

RENTALS_SQL = """
SELECT r.rental_id, r.customer_id, f.film_id, f.title, i.store_id,
       r.rental_date, r.return_date, COALESCE(p.amount_total, 0) AS amount
FROM rental r
JOIN inventory i ON i.inventory_id = r.inventory_id
JOIN film f ON f.film_id = i.film_id
LEFT JOIN (SELECT rental_id, sum(amount) AS amount_total FROM payment GROUP BY rental_id) p
       ON p.rental_id = r.rental_id
ORDER BY r.rental_date DESC, r.rental_id DESC
"""


def money(value) -> Decimal128:
    return Decimal128(str(Decimal(value)))


def build_films(pg):
    films, categories_by_film = [], {}
    for r in pg.execute(FILMS_SQL).fetchall():
        categories_by_film[r["film_id"]] = list(r["categories"])
        films.append({
            "_id": r["film_id"],
            "title": r["title"],
            "release_year": r["release_year"],
            "language": r["language"],
            "rating": r["rating"],
            "length": r["length"],
            "rental_duration": r["rental_duration"],
            "rental_rate": money(r["rental_rate"]),
            "categories": list(r["categories"]),
            "actors": r["actors"],
        })
    return films, categories_by_film


def build_rentals(pg, categories_by_film):
    rentals = []
    for r in pg.execute(RENTALS_SQL).fetchall():
        rentals.append({
            "_id": r["rental_id"],
            "customer_id": r["customer_id"],
            "film_id": r["film_id"],
            "title": r["title"],
            "categories": categories_by_film.get(r["film_id"], []),
            "store_id": r["store_id"],
            "rental_date": r["rental_date"],
            "return_date": r["return_date"],
            "amount": money(r["amount"]),
        })
    return rentals


def build_customers(pg, rentals):
    # rentals are already sorted by rental_date desc, rental_id desc
    recent = defaultdict(list)
    counts = defaultdict(int)
    for r in rentals:
        counts[r["customer_id"]] += 1
        if len(recent[r["customer_id"]]) < RECENT_LIMIT:
            recent[r["customer_id"]].append({
                "rental_id": r["_id"],
                "film_id": r["film_id"],
                "title": r["title"],
                "rental_date": r["rental_date"],
                "return_date": r["return_date"],
            })
    customers = []
    for c in pg.execute(CUSTOMERS_SQL).fetchall():
        customers.append({
            "_id": c["customer_id"],
            "first_name": c["first_name"],
            "last_name": c["last_name"],
            "email": c["email"],
            "store_id": c["store_id"],
            "address": {"city": c["city"], "country": c["country"]},
            "rental_count": counts[c["customer_id"]],
            "recent_rentals": recent[c["customer_id"]],
        })
    return customers


def upsert_all(collection, docs):
    if docs:
        collection.bulk_write([ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs], ordered=False)


def main() -> None:
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as pg:
        films, categories_by_film = build_films(pg)
        rentals = build_rentals(pg, categories_by_film)
        customers = build_customers(pg, rentals)

    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ.get("MONGO_DB", "pagila_docs")]
    upsert_all(db.films, films)
    upsert_all(db.customers, customers)
    upsert_all(db.rentals, rentals)
    print(f"films: {db.films.count_documents({})}")
    print(f"customers: {db.customers.count_documents({})}")
    print(f"rentals: {db.rentals.count_documents({})}")


if __name__ == "__main__":
    main()