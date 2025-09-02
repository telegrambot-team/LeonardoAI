from pathlib import Path

from aiogram.types import FSInputFile, InlineKeyboardMarkup, Message


def _extract_uid_from_reply(reply: Message) -> int | None:
    if not reply or not reply.caption:
        return None
    first_line = reply.caption.split("\n", 1)[0].strip()
    if not first_line.startswith("uid:"):
        return None
    try:
        return int(first_line.split(":", 1)[1])
    except (ValueError, IndexError):
        return None


async def moderator_reply_dispatch(message: Message, settings) -> bool:
    if message.from_user.id != settings.MODERATOR:
        return False

    reply = message.reply_to_message
    if not reply:
        return False

    target_chat_id = _extract_uid_from_reply(reply)
    if not target_chat_id:
        return False

    if message.photo:
        await message.bot.send_photo(chat_id=target_chat_id, photo=message.photo[-1].file_id, caption=message.caption)
        return True

    if message.document:
        await message.bot.send_document(
            chat_id=target_chat_id, document=message.document.file_id, caption=message.caption
        )
        return True

    if message.text:
        await message.bot.send_message(chat_id=target_chat_id, text=message.text)
        return True

    return False


async def answer_with_photo(
    message: Message, caption: str, file_name: str, markup: InlineKeyboardMarkup | None = None
):
    await message.answer_photo(
        photo=FSInputFile(str(Path(__file__).resolve().parents[1] / "internal" / file_name)),
        caption=caption,
        reply_markup=markup,
    )
