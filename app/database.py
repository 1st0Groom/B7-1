from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.logging import event
from app.models import Base


class Database:
    def __init__(self, url):
        self.engine = create_async_engine(url)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_tables(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)


async def commit(session, *, phase, **fields):
    try:
        await session.commit()
        event("db_save_success", phase=phase, **fields)
    except SQLAlchemyError:
        await session.rollback()
        event("db_save_failed", phase=phase, **fields)
        raise
