from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ReasoningEffort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Verbosity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentSettings(BaseModel):
    """Current OpenAI agent configuration, stored on the application side."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    instructions: str
    model: str
    supported_efforts: tuple[ReasoningEffort, ...]
    reasoning_effort: ReasoningEffort | None
    verbosity: Verbosity
    updated_at: datetime
    updated_by: int | None = None


class ModelChangeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings: AgentSettings
    previous_effort: ReasoningEffort | None

    @property
    def effort_changed(self) -> bool:
        return self.previous_effort != self.settings.reasoning_effort


class RedisMigrationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    conversations: int
    log_messages: int
