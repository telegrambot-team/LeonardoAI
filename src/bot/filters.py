from typing import TYPE_CHECKING

from aiogram.filters import Filter

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message

    from config import Settings


class IsModerator(Filter):
    async def __call__(self, event: "Message | CallbackQuery", settings: "Settings") -> bool:
        return event.from_user is not None and event.from_user.id == settings.MODERATOR
