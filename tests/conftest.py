from datetime import UTC, datetime

import httpx2
import openai
import pytest

from db.engine import create_engine, create_session_factory, init_schema
from schemas import AgentSettings, ReasoningEffort, Verbosity


@pytest.fixture
async def session_factory(tmp_path):
    engine = create_engine(tmp_path / "db" / "test.db")
    await init_schema(engine)
    yield create_session_factory(engine)
    await engine.dispose()


def make_settings(**overrides: object) -> AgentSettings:
    values: dict[str, object] = {
        "instructions": "Ты ассистент",
        "model": "gpt-6-luna",
        "supported_efforts": tuple(ReasoningEffort),
        "reasoning_effort": ReasoningEffort.MEDIUM,
        "verbosity": Verbosity.MEDIUM,
        "updated_at": datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return AgentSettings(**values)


def openai_error(error_cls: type[openai.APIStatusError], status: int, *, param: str | None = None):
    response = httpx2.Response(status, request=httpx2.Request("POST", "https://api.openai.com/v1/responses"))
    return error_cls("error from openai", response=response, body={"message": "error", "param": param})
