from __future__ import annotations

from typing import TYPE_CHECKING

import asyncio
import logging
import traceback

from contextlib import suppress

from aiogram import Bot, Dispatcher, Router, html
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from redis.exceptions import ConnectionError as RedisConnectionError, RedisError, TimeoutError as RedisTimeoutError

from config import Settings

logger = logging.getLogger(__name__)

REDIS_RECONNECT_ATTEMPTS = 3
REDIS_RECONNECT_BACKOFF_SECONDS = 0.2

if TYPE_CHECKING:
    from aiogram.types.error_event import ErrorEvent

router = Router()


async def _try_reconnect_redis(dispatcher: Dispatcher | None) -> bool:
    if dispatcher is None:
        return False

    storage = getattr(dispatcher, "storage", None)
    redis = getattr(storage, "redis", None)
    if redis is None:
        return False

    for attempt in range(1, REDIS_RECONNECT_ATTEMPTS + 1):
        with suppress(RedisError, OSError):
            await redis.connection_pool.disconnect(inuse_connections=True)

        try:
            await redis.ping()
        except (RedisError, OSError) as exc:
            logger.debug("Redis reconnect attempt %s failed: %s", attempt, exc)
            if attempt >= REDIS_RECONNECT_ATTEMPTS:
                return False
            await asyncio.sleep(REDIS_RECONNECT_BACKOFF_SECONDS * attempt)
        else:
            return True

    return False


@router.errors()
async def error_handler(
    error_event: ErrorEvent, bot: Bot, settings: Settings, dispatcher: Dispatcher | None = None
) -> None:
    exception = error_event.exception

    if isinstance(exception, TelegramBadRequest):
        text = str(exception).lower()
        if (
            "message is not modified" in text
            or "message can't be deleted for everyone" in text
            or "message to delete not found" in text
        ):
            logger.debug("Ignoring TelegramBadRequest: %s", exception)
            return

    if isinstance(exception, RedisConnectionError | RedisTimeoutError):
        with suppress(TelegramAPIError):
            if error_event.update.callback_query:
                await error_event.update.callback_query.answer()

        if await _try_reconnect_redis(dispatcher):
            logger.debug("Redis error recovered after reconnect: %s", exception)
            return

    exc_traceback = "".join(traceback.format_exception(None, exception, exception.__traceback__))

    tb = html.quote(exc_traceback[-3500:])
    exc_name = html.quote(type(exception).__name__)
    exc_message = html.quote(str(exception))

    error_message = (
        f"🚨 <b>An error occurred</b> 🚨\n\n"
        f"<b>Type:</b> {exc_name}\n<b>Message:</b> {exc_message}\n\n<b>Traceback:</b>\n<code>{tb}</code>"
    )
    logger.exception("Unhandled exception", exc_info=(type(exception), exception, exception.__traceback__))

    await bot.send_message(settings.ADMIN, error_message, disable_notification=True)
