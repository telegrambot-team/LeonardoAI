from aiogram.types import Message


def _extract_uid_from_reply(reply: Message) -> int | None:
    if not reply or not reply.caption:
        return None
    first_line = reply.caption.split("\n", 1)[0].strip()
    if not first_line.startswith("uid:"):
        return None
    try:
        return int(first_line.split(":", 1)[1])
    except Exception:
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
