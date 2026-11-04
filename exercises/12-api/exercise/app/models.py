"""Models of the mapped tables. Only these tables are managed by Alembic autogenerate."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Store(Base):
    __tablename__ = "store"

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True)


class Staff(Base):
    __tablename__ = "staff"

    staff_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(45))
    last_name: Mapped[str] = mapped_column(String(45))
    store_id: Mapped[int] = mapped_column(ForeignKey("store.store_id"))


class Customer(Base):
    __tablename__ = "customer"

    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("store.store_id"))
    first_name: Mapped[str] = mapped_column(String(45))
    last_name: Mapped[str] = mapped_column(String(45))
    # Added by migration 0002
    loyalty_points: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class Film(Base):
    __tablename__ = "film"

    film_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    rental_duration: Mapped[int] = mapped_column(SmallInteger)


class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    film_id: Mapped[int] = mapped_column(ForeignKey("film.film_id"))
    store_id: Mapped[int] = mapped_column(ForeignKey("store.store_id"))


class Rental(Base):
    __tablename__ = "rental"

    rental_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rental_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventory.inventory_id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.customer_id"))
    return_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.staff_id"))

    # Added by migration 0003: one open rental per copy
    __table_args__ = (
        Index(
            "rental_one_open_per_copy",
            "inventory_id",
            unique=True,
            postgresql_where=text("return_date IS NULL"),
        ),
    )
    