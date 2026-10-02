from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.logging import event as log_event


class Database:
    def __init__(self, url):
        self.engine = create_async_engine(url)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

        @event.listens_for(self.engine.sync_engine, "connect")
        def pragmas(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()


async def commit(session, *, phase, **fields):
    from sqlalchemy.exc import SQLAlchemyError

    try:
        await session.commit()
        log_event("db_save_success", phase=phase, **fields)
    except SQLAlchemyError:
        await session.rollback()
        log_event("db_save_failed", phase=phase, **fields)
        raise
