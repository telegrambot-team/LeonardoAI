from typing import TYPE_CHECKING

import logging

import openai

if TYPE_CHECKING:
    from ai_client import AIClient
    from db.repositories import ConversationRepository
    from schemas import AgentSettings
    from services.agent_settings import AgentSettingsService

logger = logging.getLogger(__name__)


class AIBadRequestError(RuntimeError):
    """OpenAI rejected the request; the user's conversation was reset."""


class ConversationService:
    def __init__(
        self,
        repository: "ConversationRepository",
        ai_client: "AIClient",
        agent_settings_service: "AgentSettingsService",
    ) -> None:
        self._repository = repository
        self._ai_client = ai_client
        self._agent_settings_service = agent_settings_service

    async def ask(self, telegram_id: int, text: str) -> str | None:
        agent = await self._agent_settings_service.get()
        conversation_id = await self._repository.get(telegram_id) or await self._start_new(telegram_id)
        try:
            return await self._request(telegram_id, conversation_id, text, agent)
        except openai.NotFoundError:
            logger.warning("Conversation %s not found, starting a new one", conversation_id)

        conversation_id = await self._start_new(telegram_id)
        return await self._request(telegram_id, conversation_id, text, agent)

    async def forget(self, telegram_id: int) -> None:
        """Drop the link to the user's conversation; a new one is created on the next message."""
        await self._repository.delete(telegram_id)

    async def forget_all(self) -> int:
        return await self._repository.delete_all()

    async def count(self) -> int:
        return await self._repository.count()

    async def _request(self, telegram_id: int, conversation_id: str, text: str, agent: "AgentSettings") -> str | None:
        try:
            return await self._ai_client.get_response(conversation_id, text, agent, user_id=telegram_id)
        except openai.BadRequestError as exc:
            logger.warning("OpenAI BadRequestError for user %s: %s", telegram_id, exc)
            await self.forget(telegram_id)
            raise AIBadRequestError(str(exc)) from exc

    async def _start_new(self, telegram_id: int) -> str:
        conversation_id = await self._ai_client.new_conversation()
        await self._repository.set(telegram_id, conversation_id)
        return conversation_id
