from typing import TYPE_CHECKING

import hashlib
import logging

import openai

from openai import AsyncOpenAI, omit

if TYPE_CHECKING:
    from openai.types.responses import FileSearchToolParam

    from schemas import AgentSettings, ReasoningEffort, Verbosity

logger = logging.getLogger(__name__)

PROBE_INPUT = "ping"
PROBE_MAX_OUTPUT_TOKENS = 16


class ModelCheckError(RuntimeError):
    """OpenAI rejected a probe request, e.g. unknown model or unsupported parameter."""


class UnsupportedReasoningEffortError(ModelCheckError):
    pass


class AIClient:
    def __init__(self, api_key: str, vector_store_ids: tuple[str, ...], *, timeout: float, max_retries: int) -> None:
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=max_retries)
        self._tools: list[FileSearchToolParam] = (
            [{"type": "file_search", "vector_store_ids": list(vector_store_ids)}] if vector_store_ids else []
        )

    async def close(self) -> None:
        await self._client.close()

    async def new_conversation(self) -> str:
        conversation = await self._client.conversations.create()
        logger.debug("Created new conversation %s", conversation.id)
        return conversation.id

    async def get_response(
        self, conversation_id: str, text: str, agent: "AgentSettings", *, user_id: int
    ) -> str | None:
        response = await self._client.responses.create(
            conversation=conversation_id,
            model=agent.model,
            input=text,
            instructions=agent.instructions or omit,
            tools=self._tools or omit,
            reasoning={"effort": agent.reasoning_effort} if agent.reasoning_effort else omit,
            text={"verbosity": agent.verbosity},
            store=True,
            safety_identifier=_safety_identifier(user_id),
        )
        return response.output_text or None

    async def probe(self, model: str, verbosity: "Verbosity", effort: "ReasoningEffort | None" = None) -> None:
        """Send a minimal request to check that OpenAI accepts the given model parameters."""
        try:
            await self._client.responses.create(
                model=model,
                input=PROBE_INPUT,
                reasoning={"effort": effort} if effort else omit,
                text={"verbosity": verbosity},
                max_output_tokens=PROBE_MAX_OUTPUT_TOKENS,
                store=False,
            )
        except openai.BadRequestError as exc:
            if effort and _is_reasoning_error(exc):
                raise UnsupportedReasoningEffortError(exc.message) from exc
            raise ModelCheckError(exc.message) from exc
        except openai.APIStatusError as exc:
            raise ModelCheckError(exc.message) from exc


def _is_reasoning_error(exc: openai.BadRequestError) -> bool:
    return (exc.param or "").startswith("reasoning") or "reasoning" in exc.message.lower()


def _safety_identifier(user_id: int) -> str:
    # OpenAI recommends passing a stable hash instead of the raw user identifier
    return hashlib.sha256(f"telegram:{user_id}".encode()).hexdigest()
