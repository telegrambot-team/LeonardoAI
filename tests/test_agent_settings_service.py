import openai
import pytest

from ai_client import ModelCheckError, UnsupportedReasoningEffortError
from db.repositories import AgentSettingsRepository
from schemas import ReasoningEffort, Verbosity
from services.agent_settings import AgentSettingsService, InvalidSettingValueError
from tests.conftest import make_settings, openai_error


class FakeAIClient:
    def __init__(self, *, unsupported: dict[str, set[ReasoningEffort]] | None = None, unknown: set[str] = frozenset()):
        self.unsupported = unsupported or {}
        self.unknown = unknown
        self.probes: list[tuple[str, Verbosity, ReasoningEffort | None]] = []

    async def probe(self, model: str, verbosity: Verbosity, effort: ReasoningEffort | None = None) -> None:
        self.probes.append((model, verbosity, effort))
        if model in self.unknown:
            msg = f"The requested model '{model}' does not exist."
            raise ModelCheckError(msg)
        if effort in self.unsupported.get(model, set()):
            msg = f"Unsupported value: {effort}"
            raise UnsupportedReasoningEffortError(msg)


@pytest.fixture
async def repository(session_factory):
    return AgentSettingsRepository(session_factory)


async def _service(repository, ai_client, **overrides) -> AgentSettingsService:
    await repository.save(make_settings(**overrides))
    return AgentSettingsService(repository, ai_client)


async def test_initialize_seeds_from_prompt_file(repository, tmp_path):
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("﻿## Роль\nТы ассистент\n", encoding="utf-8")
    ai_client = FakeAIClient(unsupported={"gpt-6-luna": {ReasoningEffort.LOW}})
    service = AgentSettingsService(repository, ai_client)

    settings = await service.initialize(
        model="gpt-6-luna", effort=ReasoningEffort.MEDIUM, verbosity=Verbosity.LOW, prompt_path=prompt_path
    )

    assert settings.instructions == "## Роль\nТы ассистент"
    assert settings.supported_efforts == (ReasoningEffort.MEDIUM, ReasoningEffort.HIGH)
    assert settings.reasoning_effort == ReasoningEffort.MEDIUM
    assert settings.verbosity == Verbosity.LOW
    assert await repository.get() == settings


async def test_initialize_keeps_existing_settings(repository, tmp_path):
    existing = make_settings(model="gpt-6-astra")
    await repository.save(existing)
    service = AgentSettingsService(repository, FakeAIClient())

    settings = await service.initialize(
        model="gpt-6-luna", effort=ReasoningEffort.LOW, verbosity=Verbosity.LOW, prompt_path=tmp_path / "missing.md"
    )

    assert settings == existing


async def test_initialize_survives_openai_failure(repository):
    service = AgentSettingsService(repository, FakeAIClient(unknown={"gpt-6-luna"}))

    settings = await service.initialize(
        model="gpt-6-luna", effort=ReasoningEffort.HIGH, verbosity=Verbosity.MEDIUM, prompt_path=None
    )

    assert settings.instructions == ""
    assert settings.supported_efforts == tuple(ReasoningEffort)
    assert settings.reasoning_effort == ReasoningEffort.HIGH


async def test_set_model_detects_efforts_and_adjusts_current(repository):
    ai_client = FakeAIClient(unsupported={"gpt-6.1-sol": {ReasoningEffort.LOW}})
    service = await _service(repository, ai_client, reasoning_effort=ReasoningEffort.LOW)

    result = await service.set_model("  gpt-6.1-sol \n", updated_by=42)

    assert result.settings.model == "gpt-6.1-sol"
    assert result.settings.supported_efforts == (ReasoningEffort.MEDIUM, ReasoningEffort.HIGH)
    assert result.settings.reasoning_effort == ReasoningEffort.MEDIUM
    assert result.settings.updated_by == 42
    assert result.previous_effort == ReasoningEffort.LOW
    assert result.effort_changed
    assert (await repository.get()).model == "gpt-6.1-sol"


async def test_set_model_without_reasoning(repository):
    ai_client = FakeAIClient(unsupported={"gpt-4.1": set(ReasoningEffort)})
    service = await _service(repository, ai_client)

    result = await service.set_model("gpt-4.1", updated_by=42)

    assert result.settings.supported_efforts == ()
    assert result.settings.reasoning_effort is None


async def test_set_model_rejected_by_openai_is_not_saved(repository):
    service = await _service(repository, FakeAIClient(unknown={"gpt-unknown"}))

    with pytest.raises(ModelCheckError):
        await service.set_model("gpt-unknown", updated_by=42)

    assert (await service.get()).model == "gpt-6-luna"
    assert (await repository.get()).model == "gpt-6-luna"


@pytest.mark.parametrize("model", ["", "   ", "gpt 6", "x" * 200])
async def test_set_model_validates_name(repository, model):
    ai_client = FakeAIClient()
    service = await _service(repository, ai_client)

    with pytest.raises(InvalidSettingValueError):
        await service.set_model(model, updated_by=42)
    assert ai_client.probes == []


async def test_set_effort_requires_supported_value(repository):
    service = await _service(repository, FakeAIClient(), supported_efforts=(ReasoningEffort.MEDIUM,))

    with pytest.raises(InvalidSettingValueError):
        await service.set_effort(ReasoningEffort.HIGH, updated_by=42)

    settings = await service.set_effort(ReasoningEffort.MEDIUM, updated_by=42)
    assert settings.reasoning_effort == ReasoningEffort.MEDIUM


async def test_set_verbosity_probes_model(repository):
    ai_client = FakeAIClient()
    service = await _service(repository, ai_client)

    settings = await service.set_verbosity(Verbosity.HIGH, updated_by=42)

    assert settings.verbosity == Verbosity.HIGH
    assert ai_client.probes == [("gpt-6-luna", Verbosity.HIGH, ReasoningEffort.MEDIUM)]


async def test_set_instructions(repository):
    service = await _service(repository, FakeAIClient())

    with pytest.raises(InvalidSettingValueError):
        await service.set_instructions(" \n ", updated_by=42)

    settings = await service.set_instructions("  Новый промпт\n", updated_by=42)
    assert settings.instructions == "Новый промпт"
    assert (await repository.get()).instructions == "Новый промпт"


async def test_real_client_classifies_effort_errors():
    from ai_client import AIClient  # noqa: PLC0415

    client = AIClient("sk-test", (), timeout=1, max_retries=0)

    async def create(**_kwargs):
        raise openai_error(openai.BadRequestError, 400, param="reasoning.effort")

    client._client.responses.create = create  # noqa: SLF001
    with pytest.raises(UnsupportedReasoningEffortError):
        await client.probe("gpt-6-luna", Verbosity.MEDIUM, ReasoningEffort.LOW)
    with pytest.raises(ModelCheckError) as exc_info:
        await client.probe("gpt-6-luna", Verbosity.MEDIUM)
    assert not isinstance(exc_info.value, UnsupportedReasoningEffortError)
    await client.close()
