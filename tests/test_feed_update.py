import typing
from datetime import datetime
from operator import index
from typing import Iterator

import pytest
import pytest_asyncio
from aiogram.methods import SendMessage

from bot.keyboards import start_kbd
from user_factory import TelegramUserFactory
from aiogram.types import Message, Update, Chat, User
from testcontainers.postgres import PostgresContainer
from database.database_connector import DatabaseConnector
from database.tables_helper import create_or_drop_db
from main import create_dispatcher
from config import Settings
from tests.moked_bot import MockedBot
from aiogram.types import User as TelegramUser

#message
#callback_query
#async def testsss(updates, TelegramMetods, RequestList):


@pytest.mark.asyncio
async def test_start_command(db: DatabaseConnector, telegram_user: TelegramUser, bot: MockedBot):
    settings = Settings(BOT_TOKEN="123", ADMIN=361557984, OPENAI_API_KEY="124", ASSISTANT_ID="125", CHAT_LOG_ID=1)
    dispatcher = create_dispatcher(settings=settings, db=db, ai_client=None)
    bot.add_result_for(SendMessage, ok=True)
    await dispatcher.feed_update(bot, create_message_update(message_id=1, text="/start", telegram_user=telegram_user))
    result = bot.get_request()
    result = typing.cast(SendMessage, result)
    assert result.reply_markup == start_kbd

    pass


def create_message_update(message_id: int, text: str, telegram_user: TelegramUser, chat_id: int = None):
    chat_id = chat_id or telegram_user.id
    return Update(
        update_id=message_id,
        message=Message(
            message_id=message_id,
            date=datetime.now(),
            chat=Chat(id=chat_id, type="private"),
            from_user=telegram_user,
            text=text,
        ),
    )


@pytest.fixture()
def bot():
    return MockedBot()


@pytest.fixture
def telegram_user() -> TelegramUser:
    return TelegramUserFactory.build()


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