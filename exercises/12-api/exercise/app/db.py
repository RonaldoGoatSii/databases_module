"""Database URL, engine and session factory. Credentials come from POSTGRES_* variables."""
import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = quote_plus(os.environ["POSTGRES_PASSWORD"])
    host = os.environ.get("POSTGRES_HOST", "127.0.0.1")
    port = os.environ.get("POSTGRES_PORT", "5432")
    database = os.environ.get("EX12_DB", "ex12")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


engine = create_engine(database_url(), echo=os.environ.get("SQL_ECHO") == "1", pool_size=10)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)