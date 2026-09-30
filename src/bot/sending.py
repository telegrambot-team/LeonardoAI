from typing import TYPE_CHECKING

import logging

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from bot.md_utils import clean, refactor_string

if TYPE_CHECKING:
    from aiogram.types import Message

logger = logging.getLogger(__name__)

# Telegram allows 4096 characters per message; leave room for MarkdownV2 formatting
MAX_CHUNK_LENGTH = 3800


def split_text(text: str, limit: int = MAX_CHUNK_LENGTH) -> list[str]:
    """Split text into chunks not longer than limit, preferring paragraph and line boundaries."""
    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        rest = line
        while len(rest) > limit:
            if current:
                chunks.append(current)
                current = ""
            cut = rest.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            chunks.append(rest[:cut])
            rest = rest[cut:].lstrip(" ")
        if len(current) + len(rest) > limit:
            chunks.append(current)
            current = ""
        current += rest
    if current:
        chunks.append(current)
    return [chunk.strip("\n") for chunk in chunks if chunk.strip()]


async def answer_ai_text(message: "Message", text: str) -> list["Message"]:
    """Send an AI answer as MarkdownV2 chunks, falling back to plain text on markup errors."""
    sent: list[Message] = []
    for chunk in split_text(clean(text)):
        try:
            sent.append(await message.answer(refactor_string(chunk), parse_mode=ParseMode.MARKDOWN_V2))
        except TelegramBadRequest as exc:
            logger.warning("Failed to send MarkdownV2 answer, falling back to plain text: %s", exc)
            sent.append(await message.answer(chunk, parse_mode=None))
    return sent
