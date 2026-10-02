import asyncio
import os

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.models import Base

load_dotenv()
config = context.config
url = (
    config.attributes.get("database_url")
    or os.getenv("DATABASE_URL")
    or config.get_main_option("sqlalchemy.url")
)


def migrate(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def online():
    engine = create_async_engine(url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        await connection.exec_driver_sql("PRAGMA journal_mode=WAL")
        await connection.commit()
        await connection.run_sync(migrate)
        await connection.commit()
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(online())
