import asyncio

from sqlalchemy.ext.asyncio import AsyncEngine

from config import Settings
from database.database_connector import DatabaseConnector
from database.models import Base


async def create_or_drop_db(engine: AsyncEngine, create: bool = True):
    async with engine.begin() as conn:
        if create:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        else:
            await conn.run_sync(Base.metadata.drop_all)


def main():
    db = DatabaseConnector(url=Settings().postgres_db_url, echo=True)
    asyncio.run(create_or_drop_db(db.engine))


if __name__ == "__main__":
    main()
