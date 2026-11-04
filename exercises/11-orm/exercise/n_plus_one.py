"""
Task 3: an N+1 on purpose, then the fix with eager loading.
Run: uv run --env-file ../../../.env python n_plus_one.py
"""
from sqlalchemy import event, select
from sqlalchemy.orm import Session, selectinload

from models import Film, make_engine


def count_statements(engine):
    counter = {"n": 0}

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)

    def stop():
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

    return counter, stop


def load_titles_with_actors(engine, eager: bool) -> int:
    counter, stop = count_statements(engine)
    stmt = select(Film).order_by(Film.film_id).limit(100)
    if eager:
        stmt = stmt.options(selectinload(Film.actors))
    with Session(engine) as session:  # a new session for each version
        films = session.scalars(stmt).all()
        for film in films:
            names = ", ".join(f"{a.first_name} {a.last_name}" for a in film.actors)
            if film.film_id <= 3:
                print(f"{film.title}: {names}")
    stop()
    return counter["n"]


def main() -> None:
    engine = make_engine(echo=False)
    naive = load_titles_with_actors(engine, eager=False)
    fixed = load_titles_with_actors(engine, eager=True)
    print(f"\nWithout eager loading: {naive} SELECT statements (expected 101)")
    print(f"With selectinload:     {fixed} SELECT statements (expected at most 2)")


if __name__ == "__main__":
    main()