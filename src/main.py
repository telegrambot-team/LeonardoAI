import asyncio
import logging.config
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.types import BotCommand

from ai_client import AIClient
from bot.handlers.base_handlers import router as base_router
from bot.handlers.errors_handler import router as errors_router
from bot.internal.notify_admin import on_shutdown_notify, on_startup_notify
from bot.middlewares.auth_middleware import AuthMiddleware
from bot.middlewares.session_middleware import DBSessionMiddleware
from bot.middlewares.updates_dumper_middleware import UpdatesDumperMiddleware
from config import get_logging_config, settings
from database.database_connector import get_db
from database.tables_helper import create_or_drop_db


async def set_bot_commands(bot: Bot) -> None:
    default_commands = [BotCommand(command="/start", description="Главное меню")]
    await bot.set_my_commands(default_commands)


async def main():
    logs_directory = Path("logs")
    logs_directory.mkdir(parents=True, exist_ok=True)
    logging_config = get_logging_config(__name__)
    logging.config.dictConfig(logging_config)

    bot = Bot(token=settings.BOT_TOKEN.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    logging.info("bot started")
    storage = MemoryStorage()

    db = get_db(settings)

    await create_or_drop_db(db.engine)

    ai_client = AIClient(settings.OPENAI_API_KEY.get_secret_value(), settings.ASSISTANT_ID.get_secret_value())

    dispatcher = Dispatcher(
        storage=storage, events_isolation=SimpleEventIsolation(), ai_client=ai_client, settings=settings
    )
    db_session_middleware = DBSessionMiddleware(db)
    dispatcher.message.middleware(db_session_middleware)
    dispatcher.callback_query.middleware(db_session_middleware)
    dispatcher.message.middleware(AuthMiddleware())
    dispatcher.callback_query.middleware(AuthMiddleware())
    dispatcher.update.outer_middleware(UpdatesDumperMiddleware())
    dispatcher.startup.register(set_bot_commands)
    dispatcher.startup.register(on_startup_notify)
    dispatcher.shutdown.register(on_shutdown_notify)
    dispatcher.include_routers(base_router, errors_router)
    await dispatcher.start_polling(bot)


def run_main():
    asyncio.run(main())


if __name__ == "__main__":
    run_main()
