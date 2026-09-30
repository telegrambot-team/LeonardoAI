import asyncio
import logging
import logging.config

from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from ai_client import AIClient
from bot.handlers.base_handlers import router as base_router
from bot.handlers.errors_handler import router as errors_router
from bot.handlers.settings_handlers import router as settings_router
from bot.internal.notify_admin import on_shutdown_notify, on_startup_notify
from bot.middlewares.updates_dumper_middleware import UpdatesDumperMiddleware
from config import Settings, get_logging_config
from db.engine import create_engine, create_session_factory, init_schema
from db.repositories import AgentSettingsRepository, ConversationRepository, LogMessageRepository, MetaRepository
from services.agent_settings import AgentSettingsService
from services.conversations import ConversationService
from services.log_chat import LogChatService
from services.redis_migration import migrate_from_redis

logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot, settings: Settings) -> None:
    start_command = BotCommand(command="start", description="Главное меню")
    await bot.set_my_commands([start_command], scope=BotCommandScopeDefault())
    await bot.set_my_commands(
        [start_command, BotCommand(command="settings", description="Настройки ассистента")],
        scope=BotCommandScopeChat(chat_id=settings.MODERATOR),
    )


def configure_logging(app_name: str) -> None:
    logs_directory = Path("logs")
    logs_directory.mkdir(parents=True, exist_ok=True)
    logging_config = get_logging_config(app_name)
    logging.config.dictConfig(logging_config)


def create_storage(settings: Settings) -> RedisStorage:
    return RedisStorage.from_url(
        settings.REDIS_URL.unicode_string(),
        connection_kwargs={
            "health_check_interval": 30,
            "retry": Retry(ExponentialBackoff(), retries=3),
            "retry_on_error": [RedisConnectionError, RedisTimeoutError],
            "retry_on_timeout": True,
            "socket_connect_timeout": 5,
            "socket_keepalive": True,
            "socket_timeout": 5,
        },
    )


async def main():
    settings = Settings()

    engine = create_engine(settings.DB_PATH)
    await init_schema(engine)
    session_factory = create_session_factory(engine)
    conversation_repository = ConversationRepository(session_factory)
    log_message_repository = LogMessageRepository(session_factory)

    storage = create_storage(settings)
    migration = await migrate_from_redis(
        storage.redis,
        log_chat_id=settings.CHAT_LOG_ID,
        meta=MetaRepository(session_factory),
        conversations=conversation_repository,
        log_messages=log_message_repository,
    )
    if migration:
        logger.info("Migrated from Redis: %s", migration)

    ai_client = AIClient(
        settings.OPENAI_API_KEY.get_secret_value(),
        settings.VECTOR_STORE_IDS,
        timeout=settings.OPENAI_TIMEOUT_SECONDS,
        max_retries=settings.OPENAI_MAX_RETRIES,
    )
    agent_settings_service = AgentSettingsService(AgentSettingsRepository(session_factory), ai_client)
    await agent_settings_service.initialize(
        model=settings.DEFAULT_MODEL,
        effort=settings.DEFAULT_EFFORT,
        verbosity=settings.DEFAULT_VERBOSITY,
        prompt_path=settings.INITIAL_PROMPT_PATH,
    )

    bot = Bot(token=settings.BOT_TOKEN.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher(
        storage=storage,
        events_isolation=SimpleEventIsolation(),
        settings=settings,
        agent_settings_service=agent_settings_service,
        conversation_service=ConversationService(conversation_repository, ai_client, agent_settings_service),
        log_chat_service=LogChatService(log_message_repository, settings.CHAT_LOG_ID),
    )
    dispatcher.update.outer_middleware(UpdatesDumperMiddleware())
    dispatcher.startup.register(set_bot_commands)
    dispatcher.startup.register(on_startup_notify)
    dispatcher.shutdown.register(on_shutdown_notify)
    # settings router goes first: it handles moderator input while the menu waits for it
    dispatcher.include_routers(settings_router, base_router, errors_router)

    logger.info("bot started")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await ai_client.close()
        await engine.dispose()


def run_main():
    configure_logging(__name__)
    asyncio.run(main())


if __name__ == "__main__":
    run_main()
