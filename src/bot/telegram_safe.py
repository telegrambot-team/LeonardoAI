from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message


def _is_message_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


def _is_message_cant_be_deleted(exc: TelegramBadRequest) -> bool:
    text = str(exc).lower()
    return "message can't be deleted for everyone" in text or "message to delete not found" in text


async def safe_edit_text(message: Message, text: str, *, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if _is_message_not_modified(exc):
            return
        raise


async def safe_edit_media(
    message: Message, media: InputMediaPhoto, *, reply_markup: InlineKeyboardMarkup | None = None
) -> None:
    try:
        await message.edit_media(media, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if _is_message_not_modified(exc):
            return
        raise


async def safe_delete_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest as exc:
        if _is_message_cant_be_deleted(exc):
            return
        raise
