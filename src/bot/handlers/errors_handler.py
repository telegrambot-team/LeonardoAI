import typing

import logging
import traceback

import aiogram

from aiogram import Router, html

from config import Settings

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from aiogram.types.error_event import ErrorEvent

router = Router()


@router.errors()
async def error_handler(error_event: "ErrorEvent", bot: aiogram.Bot, settings: Settings) -> None:
    exception = error_event.exception
    exc_traceback = "".join(traceback.format_exception(None, exception, exception.__traceback__))

    tb = html.quote(exc_traceback[-3500:])
    exc_name = html.quote(type(exception).__name__)
    exc_message = html.quote(str(exception))

    error_message = (
        f"🚨 <b>An error occurred</b> 🚨\n\n"
        f"<b>Type:</b> {exc_name}\n<b>Message:</b> {exc_message}\n\n<b>Traceback:</b>\n<code>{tb}</code>"
    )
    logger.exception("Unhandled exception", exc_info=exception)

    await bot.send_message(settings.ADMIN, error_message, disable_notification=True)
