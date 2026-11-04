"""
SQLAlchemy 2.0 models for six Pagila tables: film, language, actor, film_actor, category, film_category.
The relationships are read-only (viewonly=True): this exercise only reads.
"""
import os
from urllib.parse import quote_plus

from sqlalchemy import ForeignKey, Integer, SmallInteger, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Language(Base):
    __tablename__ = "language"

    language_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(20))

    films: Mapped[list["Film"]] = relationship(back_populates="language", viewonly=True)


class Actor(Base):
    __tablename__ = "actor"

    actor_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(45))
    last_name: Mapped[str] = mapped_column(String(45))

    films: Mapped[list["Film"]] = relationship(
        secondary="film_actor", back_populates="actors", viewonly=True
    )


class Category(Base):
    __tablename__ = "category"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(25))

    films: Mapped[list["Film"]] = relationship(
        secondary="film_category", back_populates="categories", viewonly=True
    )


class Film(Base):
    __tablename__ = "film"

    film_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    length: Mapped[int | None] = mapped_column(SmallInteger)
    language_id: Mapped[int] = mapped_column(ForeignKey("language.language_id"))

    language: Mapped[Language] = relationship(back_populates="films", viewonly=True)
    actors: Mapped[list[Actor]] = relationship(
        secondary="film_actor", back_populates="films", viewonly=True
    )
    categories: Mapped[list[Category]] = relationship(
        secondary="film_category", back_populates="films", viewonly=True
    )


class FilmActor(Base):
    __tablename__ = "film_actor"

    actor_id: Mapped[int] = mapped_column(ForeignKey("actor.actor_id"), primary_key=True)
    film_id: Mapped[int] = mapped_column(ForeignKey("film.film_id"), primary_key=True)


class FilmCategory(Base):
    __tablename__ = "film_category"

    film_id: Mapped[int] = mapped_column(ForeignKey("film.film_id"), primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.category_id"), primary_key=True)


def make_engine(echo: bool = False):
    """Builds the engine from the POSTGRES_* variables (run with --env-file ../../../.env)."""
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = quote_plus(os.environ["POSTGRES_PASSWORD"])
    host = os.environ.get("POSTGRES_HOST", "127.0.0.1")
    port = os.environ.get("POSTGRES_PORT", "5432")
    database = os.environ.get("EX11_DB", "ex11")
    return create_engine(f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}", echo=echo)