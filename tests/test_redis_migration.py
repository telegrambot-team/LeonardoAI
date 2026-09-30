import json

from db.repositories import ConversationRepository, LogMessageRepository, MetaRepository
from services.redis_migration import migrate_from_redis

LOG_CHAT_ID = -100500


class FakeRedis:
    def __init__(self, data: dict[str, str]) -> None:
        self.data = data

    async def scan_iter(self, match: str, count: int):
        assert match == "fsm:*:data"
        for key in list(self.data):
            if key.startswith("fsm:") and key.endswith(":data"):
                yield key.encode()

    async def get(self, key: str) -> str | None:
        return self.data.get(key)


async def test_migrates_once_without_touching_redis(session_factory):
    data = {
        "fsm:0:0:data": json.dumps({"log_user_message_map": {"501": 1001, "502": 1002}}),
        "fsm:111:111:data": json.dumps({"ai_conversation_id": "conv_a", "ai_thread_id": None}),
        "fsm:222:222:data": json.dumps({"ai_conversation_id": None}),
        "fsm:333:333:data": "not json",
        "fsm:111:111:state": "StatesBot:IN_AI_DIALOG",
    }
    redis = FakeRedis(dict(data))
    meta = MetaRepository(session_factory)
    conversations = ConversationRepository(session_factory)
    log_messages = LogMessageRepository(session_factory)

    result = await migrate_from_redis(
        redis, log_chat_id=LOG_CHAT_ID, meta=meta, conversations=conversations, log_messages=log_messages
    )

    assert result.conversations == 1
    assert result.log_messages == 2
    assert await conversations.get(111) == "conv_a"
    assert await conversations.get(222) is None
    assert await log_messages.get_user_id(LOG_CHAT_ID, 502) == 1002
    assert redis.data == data

    await conversations.set(111, "conv_new")
    second = await migrate_from_redis(
        redis, log_chat_id=LOG_CHAT_ID, meta=meta, conversations=conversations, log_messages=log_messages
    )
    assert second is None
    assert await conversations.get(111) == "conv_new"
