from db.repositories import AgentSettingsRepository, ConversationRepository, LogMessageRepository, MetaRepository
from tests.conftest import make_settings


async def test_agent_settings_roundtrip(session_factory):
    repository = AgentSettingsRepository(session_factory)
    assert await repository.get() is None

    settings = make_settings()
    await repository.save(settings)
    assert await repository.get() == settings

    updated = settings.model_copy(update={"model": "gpt-6-astra", "reasoning_effort": None, "supported_efforts": ()})
    await repository.save(updated)
    assert await repository.get() == updated


async def test_conversations(session_factory):
    repository = ConversationRepository(session_factory)
    assert await repository.get(1) is None

    await repository.set(1, "conv_1")
    await repository.set(1, "conv_2")
    assert await repository.get(1) == "conv_2"

    inserted = await repository.add_missing([(1, "conv_old"), (2, "conv_3")])
    assert inserted == 1
    assert await repository.get(1) == "conv_2"
    assert await repository.count() == 2

    await repository.delete(1)
    assert await repository.get(1) is None
    assert await repository.delete_all() == 1
    assert await repository.count() == 0


async def test_log_messages_batches(session_factory):
    repository = LogMessageRepository(session_factory)
    mapping = [(message_id, 1000 + message_id) for message_id in range(1200)]
    assert await repository.add_missing(-100, mapping) == 1200
    assert await repository.add_missing(-100, mapping[:10]) == 0
    assert await repository.get_user_id(-100, 5) == 1005
    assert await repository.get_user_id(-200, 5) is None


async def test_meta(session_factory):
    repository = MetaRepository(session_factory)
    assert await repository.get("key") is None
    await repository.set("key", "1")
    assert await repository.get("key") == "1"
