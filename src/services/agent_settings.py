from typing import TYPE_CHECKING

import asyncio
import logging

from datetime import UTC, datetime

from ai_client import UnsupportedReasoningEffortError
from schemas import AgentSettings, ModelChangeResult, ReasoningEffort, Verbosity

if TYPE_CHECKING:
    from pathlib import Path

    from ai_client import AIClient
    from db.repositories import AgentSettingsRepository

logger = logging.getLogger(__name__)

MAX_MODEL_NAME_LENGTH = 128


class AgentSettingsNotInitializedError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Agent settings are not initialized")


class InvalidSettingValueError(ValueError):
    pass


class AgentSettingsService:
    """Owns the current agent configuration: validation, persistence and in-memory cache."""

    def __init__(self, repository: "AgentSettingsRepository", ai_client: "AIClient") -> None:
        self._repository = repository
        self._ai_client = ai_client
        self._cache: AgentSettings | None = None

    async def get(self) -> AgentSettings:
        if self._cache is None:
            self._cache = await self._repository.get()
        if self._cache is None:
            raise AgentSettingsNotInitializedError
        return self._cache

    async def initialize(
        self, *, model: str, effort: ReasoningEffort, verbosity: Verbosity, prompt_path: "Path | None"
    ) -> AgentSettings:
        """Seed settings on the very first start; existing settings are never overwritten."""
        if existing := await self._repository.get():
            self._cache = existing
            return existing

        instructions = ""
        if prompt_path is not None:
            instructions = prompt_path.read_text(encoding="utf-8-sig").strip()
        else:
            logger.warning("INITIAL_PROMPT_PATH is not set, agent starts without instructions")

        try:
            supported = await self.detect_supported_efforts(model, verbosity)
        except Exception:
            # Seeding must not block the start: assume all efforts until the next model change
            logger.exception("Failed to detect supported efforts for %s", model)
            supported = tuple(ReasoningEffort)

        settings = AgentSettings(
            instructions=instructions,
            model=model,
            supported_efforts=supported,
            reasoning_effort=_pick_effort(effort, supported),
            verbosity=verbosity,
            updated_at=datetime.now(UTC),
        )
        return await self._save(settings)

    async def set_instructions(self, instructions: str, *, updated_by: int) -> AgentSettings:
        instructions = instructions.strip()
        if not instructions:
            msg = "Промпт пустой"
            raise InvalidSettingValueError(msg)
        return await self._update(instructions=instructions, updated_by=updated_by)

    async def set_model(self, model: str, *, updated_by: int) -> ModelChangeResult:
        model = model.strip()
        if not model or len(model) > MAX_MODEL_NAME_LENGTH or any(char.isspace() for char in model):
            msg = "Название модели должно быть одним словом без пробелов"
            raise InvalidSettingValueError(msg)

        current = await self.get()
        # Also validates the model itself: ModelCheckError propagates and nothing is saved
        supported = await self.detect_supported_efforts(model, current.verbosity)
        settings = await self._update(
            model=model,
            supported_efforts=supported,
            reasoning_effort=_pick_effort(current.reasoning_effort, supported),
            updated_by=updated_by,
        )
        return ModelChangeResult(settings=settings, previous_effort=current.reasoning_effort)

    async def set_effort(self, effort: ReasoningEffort, *, updated_by: int) -> AgentSettings:
        current = await self.get()
        if effort not in current.supported_efforts:
            msg = f"Модель {current.model} не поддерживает effort {effort}"
            raise InvalidSettingValueError(msg)
        return await self._update(reasoning_effort=effort, updated_by=updated_by)

    async def set_verbosity(self, verbosity: Verbosity, *, updated_by: int) -> AgentSettings:
        current = await self.get()
        await self._ai_client.probe(current.model, verbosity, current.reasoning_effort)
        return await self._update(verbosity=verbosity, updated_by=updated_by)

    async def detect_supported_efforts(self, model: str, verbosity: Verbosity) -> tuple[ReasoningEffort, ...]:
        # There is no API to list model capabilities, so probe the model once without reasoning
        # (validates the model name) and then once per effort level
        await self._ai_client.probe(model, verbosity)
        results = await asyncio.gather(
            *(self._ai_client.probe(model, verbosity, effort) for effort in ReasoningEffort), return_exceptions=True
        )
        supported: list[ReasoningEffort] = []
        for effort, result in zip(ReasoningEffort, results, strict=True):
            if isinstance(result, UnsupportedReasoningEffortError):
                logger.info("Model %s does not support effort %s: %s", model, effort, result)
                continue
            if isinstance(result, BaseException):
                raise result
            supported.append(effort)
        return tuple(supported)

    async def _update(self, *, updated_by: int, **changes: object) -> AgentSettings:
        current = await self.get()
        settings = current.model_copy(update={**changes, "updated_by": updated_by, "updated_at": datetime.now(UTC)})
        return await self._save(settings)

    async def _save(self, settings: AgentSettings) -> AgentSettings:
        self._cache = await self._repository.save(settings)
        return self._cache


def _pick_effort(preferred: ReasoningEffort | None, supported: tuple[ReasoningEffort, ...]) -> ReasoningEffort | None:
    if not supported:
        return None
    if preferred in supported:
        return preferred
    if ReasoningEffort.MEDIUM in supported:
        return ReasoningEffort.MEDIUM
    return supported[0]
