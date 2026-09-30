import openai
import pytest

from db.repositories import ConversationRepository
from services.conversations import AIBadRequestError, ConversationService
from tests.conftest import make_settings, openai_error


class FakeSettingsService:
    async def get(self):
        return make_settings()


class FakeAIClient:
    def __init__(self, errors: list[Exception] | None = None) -> None:
        self.errors = errors or []
        self.created = 0
        self.requests: list[str] = []

    async def new_conversation(self) -> str:
        self.created += 1
        return f"conv_{self.created}"

    async def get_response(self, conversation_id, text, agent, *, user_id):
        self.requests.append(conversation_id)
        if self.errors:
            raise self.errors.pop(0)
        return f"answer to {text}"


@pytest.fixture
def repository(session_factory):
    return ConversationRepository(session_factory)


async def test_ask_reuses_conversation(repository):
    ai_client = FakeAIClient()
    service = ConversationService(repository, ai_client, FakeSettingsService())

    assert await service.ask(1, "hi") == "answer to hi"
    assert await service.ask(1, "again") == "answer to again"

    assert ai_client.requests == ["conv_1", "conv_1"]
    assert await repository.get(1) == "conv_1"


async def test_ask_recovers_from_missing_conversation(repository):
    await repository.set(1, "conv_deleted")
    ai_client = FakeAIClient([openai_error(openai.NotFoundError, 404)])
    service = ConversationService(repository, ai_client, FakeSettingsService())

    assert await service.ask(1, "hi") == "answer to hi"

    assert ai_client.requests == ["conv_deleted", "conv_1"]
    assert await repository.get(1) == "conv_1"


async def test_ask_bad_request_resets_conversation(repository):
    ai_client = FakeAIClient([openai_error(openai.BadRequestError, 400)])
    service = ConversationService(repository, ai_client, FakeSettingsService())

    with pytest.raises(AIBadRequestError):
        await service.ask(1, "hi")

    assert await repository.get(1) is None


async def test_forget_all(repository):
    service = ConversationService(repository, FakeAIClient(), FakeSettingsService())
    await service.ask(1, "hi")
    await service.ask(2, "hi")

    assert await service.count() == 2
    assert await service.forget_all() == 2
    assert await service.count() == 0
