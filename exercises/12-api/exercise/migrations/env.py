"""
Alembic environment. Autogenerate only looks at the tables mapped in app.models.
Anything that exists in the database but is not mapped (the rest of Pagila) is ignored,
so autogenerate can never propose dropping it.
"""
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models  # noqa: E402,F401  (registers the mapped tables in Base.metadata)
from app.db import Base, database_url  # noqa: E402

config = context.config
config.set_main_option("sqlalchemy.url", database_url().replace("%", "%%"))

target_metadata = Base.metadata
MAPPED_TABLES = set(target_metadata.tables)


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in MAPPED_TABLES
    if reflected and compare_to is None:
        # The database has it and the models do not: never generate a drop for it
        return False
    table = getattr(obj, "table", None)
    if table is not None and table.name not in MAPPED_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()