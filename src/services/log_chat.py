from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from db.repositories import LogMessageRepository


class LogChatService:
    """Remembers authors of messages forwarded to the log chat, so the moderator can reply."""

    def __init__(self, repository: "LogMessageRepository", log_chat_id: int) -> None:
        self._repository = repository
        self._log_chat_id = log_chat_id

    async def remember(self, message_ids: "Iterable[int]", telegram_id: int) -> None:
        await self._repository.add_missing(self._log_chat_id, ((msg_id, telegram_id) for msg_id in message_ids))

    async def find_user(self, message_id: int) -> int | None:
        return await self._repository.get_user_id(self._log_chat_id, message_id)
