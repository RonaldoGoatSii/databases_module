"""
Task 2: three queries written with the ORM, run with echo=True, and compared with the handwritten SQL.
Run: uv run --env-file ../../../.env python queries.py
"""
from sqlalchemy import desc, func, select, text
from sqlalchemy.orm import Session

from models import Actor, Category, Film, FilmActor, FilmCategory, make_engine

HANDWRITTEN = {
    "Q1": """
        SELECT c.name, count(*) AS films
        FROM category c JOIN film_category fc ON fc.category_id = c.category_id
        GROUP BY c.category_id, c.name
        ORDER BY films DESC, c.name
    """,
    "Q2": """
        SELECT f.film_id, f.title, f.length
        FROM film f
        WHERE f.length > (SELECT avg(length) FROM film)
        ORDER BY f.length DESC, f.film_id
    """,
    "Q3": """
        SELECT a.actor_id, a.first_name, a.last_name, count(*) AS films
        FROM actor a JOIN film_actor fa ON fa.actor_id = a.actor_id
        GROUP BY a.actor_id
        ORDER BY films DESC, a.actor_id
        LIMIT 10
    """,
}


def orm_q1():
    # The join starts from category and uses film_category only, like the handwritten query.
    return (
        select(Category.name, func.count().label("films"))
        .select_from(Category)
        .join(FilmCategory, FilmCategory.category_id == Category.category_id)
        .group_by(Category.category_id, Category.name)
        .order_by(desc("films"), Category.name)
    )


def orm_q2():
    avg_length = select(func.avg(Film.length)).scalar_subquery()
    return (
        select(Film.film_id, Film.title, Film.length)
        .where(Film.length > avg_length)
        .order_by(Film.length.desc(), Film.film_id)
    )


def orm_q3():
    return (
        select(Actor.actor_id, Actor.first_name, Actor.last_name, func.count(FilmActor.film_id).label("films"))
        .join(FilmActor, FilmActor.actor_id == Actor.actor_id)
        .group_by(Actor.actor_id)
        .order_by(desc("films"), Actor.actor_id)
        .limit(10)
    )


ORM = {"Q1": orm_q1, "Q2": orm_q2, "Q3": orm_q3}


def main() -> None:
    engine = make_engine(echo=True)  # echo=True prints the SQL the ORM generates
    for name, build in ORM.items():
        print(f"\n===== {name} (ORM) =====")
        with Session(engine) as session:
            orm_rows = [tuple(r) for r in session.execute(build()).all()]
        print(f"===== {name} (handwritten) =====")
        with engine.connect() as conn:
            hand_rows = [tuple(r) for r in conn.execute(text(HANDWRITTEN[name])).all()]
        same = orm_rows == hand_rows
        print(f"{name}: {len(orm_rows)} rows, same rows as handwritten SQL: {same}")


if __name__ == "__main__":
    main()