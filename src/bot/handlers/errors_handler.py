from typing import TYPE_CHECKING

import asyncio
import logging
import time

from contextlib import suppress

from aiogram import Router, html
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError

if TYPE_CHECKING:
    from aiogram import Bot, Dispatcher
    from aiogram.types import Update
    from aiogram.types.error_event import ErrorEvent

    from config import Settings

logger = logging.getLogger(__name__)

REDIS_RECONNECT_ATTEMPTS = 3
REDIS_RECONNECT_BACKOFF_SECONDS = 0.2
MAX_ERROR_MESSAGE_LENGTH = 500
# The same error is reported to the admin at most once per this interval
ERROR_REPEAT_INTERVAL_SECONDS = 10 * 60

router = Router()

_last_reported: dict[tuple[str, str], float] = {}


async def _try_reconnect_redis(dispatcher: "Dispatcher | None") -> bool:
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


def _should_report(exception: Exception) -> bool:
    key = (type(exception).__name__, str(exception))
    now = time.monotonic()
    last = _last_reported.get(key)
    if last is not None and now - last < ERROR_REPEAT_INTERVAL_SECONDS:
        return False
    for stale_key in [k for k, ts in _last_reported.items() if now - ts >= ERROR_REPEAT_INTERVAL_SECONDS]:
        del _last_reported[stale_key]
    _last_reported[key] = now
    return True


def _describe_update(update: "Update") -> str:
    event = update.event
    user = getattr(event, "from_user", None)
    user_part = f", user {user.id}" if user else ""
    return f"{update.event_type}{user_part}"


def format_error_report(exception: Exception, update: "Update") -> str:
    message = str(exception)
    if len(message) > MAX_ERROR_MESSAGE_LENGTH:
        message = message[:MAX_ERROR_MESSAGE_LENGTH] + "…"
    return (
        f"🚨 <b>{html.quote(type(exception).__name__)}</b>\n"
        f"{html.quote(message)}\n\n"
        f"<i>{html.quote(_describe_update(update))}</i>"
    )


@router.errors()
async def error_handler(
    error_event: "ErrorEvent", bot: "Bot", settings: "Settings", dispatcher: "Dispatcher | None" = None
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

    logger.error("Unhandled exception", exc_info=exception)

    if not _should_report(exception):
        return
    with suppress(TelegramAPIError):
        await bot.send_message(
            settings.ADMIN, format_error_report(exception, error_event.update), disable_notification=True
        )
