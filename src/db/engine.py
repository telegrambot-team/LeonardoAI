from typing import TYPE_CHECKING

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from db.models import Base

if TYPE_CHECKING:
    from pathlib import Path
    from sqlite3 import Connection

    from sqlalchemy.pool import ConnectionPoolEntry


def _set_sqlite_pragmas(dbapi_connection: "Connection", _connection_record: "ConnectionPoolEntry") -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def create_engine(db_path: "Path") -> AsyncEngine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
