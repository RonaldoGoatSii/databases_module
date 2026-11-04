"""
Rentals API. Each request uses its own session. Each rental is one transaction.
"""
from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import Customer, Film, Inventory, Rental

app = FastAPI(title="ex12 rentals API")

MAX_ATTEMPTS = 3


class RentalIn(BaseModel):
    customer_id: int
    film_id: int
    store_id: int
    staff_id: int


@app.post("/rentals", status_code=201)
def create_rental(body: RentalIn):
    for _attempt in range(MAX_ATTEMPTS):
        try:
            # One transaction per attempt: read the copy, lock it, insert the rental
            with SessionLocal() as session, session.begin():
                if session.get(Customer, body.customer_id) is None:
                    raise HTTPException(404, "customer not found")
                if session.get(Film, body.film_id) is None:
                    raise HTTPException(404, "film not found")

                has_open_rental = exists().where(
                    Rental.inventory_id == Inventory.inventory_id,
                    Rental.return_date.is_(None),
                )
                copy = session.scalars(
                    select(Inventory)
                    .where(
                        Inventory.film_id == body.film_id,
                        Inventory.store_id == body.store_id,
                        ~has_open_rental,
                    )
                    .order_by(Inventory.inventory_id)
                    .limit(1)
                    .with_for_update(skip_locked=True, of=Inventory)
                ).first()
                if copy is None:
                    raise HTTPException(409, "no copy available")

                rental = Rental(
                    rental_date=datetime.now(timezone.utc),
                    inventory_id=copy.inventory_id,
                    customer_id=body.customer_id,
                    staff_id=body.staff_id,
                )
                session.add(rental)
                session.flush()
                return {"rental_id": rental.rental_id, "inventory_id": copy.inventory_id}
        except IntegrityError:
            # Another request rented the same copy between our read and our insert: try again
            continue
    raise HTTPException(409, "could not rent a copy, try again")


@app.post("/rentals/{rental_id}/return")
def return_rental(rental_id: int):
    with SessionLocal() as session, session.begin():
        rental = session.scalar(select(Rental).where(Rental.rental_id == rental_id).with_for_update())
        if rental is None:
            raise HTTPException(404, "rental not found")
        if rental.return_date is not None:
            raise HTTPException(409, "already returned")
        rental.return_date = datetime.now(timezone.utc)
    return {"rental_id": rental_id, "return_date": rental.return_date.isoformat()}


@app.get("/rentals/overdue")
def overdue(as_of: date = Query(...)):
    # One query: rentals, copies, films and customers joined, so there is no N+1
    due = Rental.rental_date + func.make_interval(0, 0, 0, Film.rental_duration)
    stmt = (
        select(
            Rental.rental_id,
            Rental.rental_date,
            Film.rental_duration,
            Customer.customer_id,
            Customer.first_name,
            Customer.last_name,
            Film.film_id,
            Film.title,
        )
        .join(Inventory, Inventory.inventory_id == Rental.inventory_id)
        .join(Film, Film.film_id == Inventory.film_id)
        .join(Customer, Customer.customer_id == Rental.customer_id)
        .where(Rental.return_date.is_(None), due < as_of)
        .order_by(Rental.rental_date, Rental.rental_id)
    )
    with SessionLocal() as session:
        rows = session.execute(stmt).all()

    return [
        {
            "rental_id": r.rental_id,
            "rental_date": r.rental_date.isoformat(),
            "due_date": (r.rental_date + timedelta(days=r.rental_duration)).date().isoformat(),
            "customer": {
                "customer_id": r.customer_id,
                "first_name": r.first_name,
                "last_name": r.last_name,
            },
            "film": {"film_id": r.film_id, "title": r.title},
        }
        for r in rows
    ]