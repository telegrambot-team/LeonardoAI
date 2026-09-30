from typing import TYPE_CHECKING

import json
import logging

from schemas import RedisMigrationResult

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from db.repositories import ConversationRepository, LogMessageRepository, MetaRepository

logger = logging.getLogger(__name__)

MIGRATION_KEY = "redis_migrated"
# aiogram DefaultKeyBuilder layout: fsm:{chat_id}:{user_id}:data; fsm:0:0:data is the old global one
FSM_DATA_PATTERN = "fsm:*:data"
GLOBAL_DATA_KEY = "fsm:0:0:data"


async def migrate_from_redis(
    redis: "Redis",
    *,
    log_chat_id: int,
    meta: "MetaRepository",
    conversations: "ConversationRepository",
    log_messages: "LogMessageRepository",
) -> RedisMigrationResult | None:
    """Copy conversation ids and log-chat mapping from the old Redis FSM data into SQLite once.

    Redis is only read, never modified. Returns None if the migration has already been done.
    """
    if await meta.get(MIGRATION_KEY):
        return None

    user_conversations: dict[int, str] = {}
    log_mapping: list[tuple[int, int]] = []
    async for raw_key in redis.scan_iter(match=FSM_DATA_PATTERN, count=500):
        key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
        raw_data = await redis.get(key)
        if not raw_data:
            continue
        try:
            data = json.loads(raw_data)
        except ValueError:
            logger.warning("Skipping non-JSON FSM data under %s", key)
            continue

        if key == GLOBAL_DATA_KEY:
            log_mapping = _parse_log_mapping(data.get("log_user_message_map") or {})
            continue

        conversation_id = data.get("ai_conversation_id")
        user_id = key.split(":")[-2]
        if conversation_id and user_id.isdigit():
            user_conversations[int(user_id)] = conversation_id

    result = RedisMigrationResult(
        conversations=await conversations.add_missing(user_conversations.items()),
        log_messages=await log_messages.add_missing(log_chat_id, log_mapping),
    )
    await meta.set(MIGRATION_KEY, "1")
    logger.info("Redis migration done: %s", result)
    return result


def _parse_log_mapping(raw: dict[str, object]) -> list[tuple[int, int]]:
    mapping = []
    for message_id, user_id in raw.items():
        if message_id.isdigit() and isinstance(user_id, int):
            mapping.append((int(message_id), user_id))
    return mapping
