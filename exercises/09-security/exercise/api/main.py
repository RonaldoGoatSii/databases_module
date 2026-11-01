"""
API with three endpoints, one per engine. Every query is parameterised; no query is built
by joining user input into a string. Credentials come from environment variables.
"""
import os
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import quote_plus

import psycopg
import pymongo
import redis
from fastapi import FastAPI, Path
from pydantic import BaseModel, StrictInt, StrictStr

app = FastAPI(title="ex09 security API")

COUNTER_NAME = r"^[a-z0-9_-]{1,32}$"

_mongo = None
_redis = None


def pg_connect():
    return psycopg.connect(
        host=os.environ["PG_HOST"],
        port=os.environ["PG_PORT"],
        dbname=os.environ["PG_DATABASE"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
    )


def mongo_db():
    global _mongo
    if _mongo is None:
        user = quote_plus(os.environ["MONGO_USER"])
        password = quote_plus(os.environ["MONGO_PASSWORD"])
        db = os.environ["MONGO_DB"]
        uri = (f"mongodb://{user}:{password}@{os.environ['MONGO_HOST']}:"
               f"{os.environ['MONGO_PORT']}/?authSource={db}")
        _mongo = pymongo.MongoClient(uri)
    return _mongo[os.environ["MONGO_DB"]]


def redis_client():
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=os.environ["REDIS_HOST"],
            port=int(os.environ["REDIS_PORT"]),
            username=os.environ["REDIS_USER"],
            password=os.environ["REDIS_PASSWORD"],
            decode_responses=True,
        )
    return _redis


class ActorIn(BaseModel):
    first_name: StrictStr
    last_name: StrictStr


class NoteIn(BaseModel):
    customer_id: StrictInt
    text: StrictStr


@app.post("/actors", status_code=201)
def create_actor(body: ActorIn):
    with pg_connect() as conn:
        row = conn.execute(
            "INSERT INTO actor (first_name, last_name) VALUES (%s, %s) RETURNING actor_id",
            (body.first_name, body.last_name),
        ).fetchone()
    return {"actor_id": row[0]}


@app.post("/notes", status_code=201)
def create_note(body: NoteIn):
    result = mongo_db().notes.insert_one({
        "customer_id": body.customer_id,
        "text": body.text,
        "created_at": datetime.now(timezone.utc),
    })
    return {"id": str(result.inserted_id)}


@app.post("/counters/{name}")
def incr_counter(name: Annotated[str, Path(pattern=COUNTER_NAME)]):
    # execute_command sends exactly INCR, which is the only command the ACL user may run
    value = redis_client().execute_command("INCR", f"counter:{name}")
    return {"name": name, "value": value}