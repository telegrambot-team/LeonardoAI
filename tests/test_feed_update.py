from typing import Iterator

import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from database.database_connector import DatabaseConnector
from database.tables_helper import create_or_drop_db
from main import create_dispatcher
from config import Settings
from tests.moked_bot import MockedBot


def test_start_command(db: DatabaseConnector):
    settings = Settings(BOT_TOKEN="123", ADMIN=361557984, OPENAI_API_KEY="124", ASSISTANT_ID="125", CHAT_LOG_ID=1)
    dispatcher = create_dispatcher(settings=settings, db=db, ai_client=None)


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:16", driver="asyncpg") as postgres:
        yield postgres


@pytest_asyncio.fixture()
async def db(postgres_container: PostgresContainer) -> DatabaseConnector:
    dc = DatabaseConnector(postgres_container.get_connection_url(), echo=True)
    await create_or_drop_db(dc.engine)
    yield dc
    await dc.engine.dispose()