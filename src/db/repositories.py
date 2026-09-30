from typing import TYPE_CHECKING

from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert

from db.models import AgentSettingsRow, Base, LogMessageRow, MetaRow, UserConversationRow
from schemas import AgentSettings

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

AGENT_SETTINGS_ROW_ID = 1
# keeps a single INSERT well below SQLite's limit on bound parameters
INSERT_BATCH_SIZE = 500


def _as_utc(value: datetime) -> datetime:
    # SQLite does not keep tzinfo, values are always written in UTC
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


async def _insert_missing(
    session_factory: "async_sessionmaker[AsyncSession]", model: type[Base], values: list[dict[str, object]]
) -> int:
    inserted = 0
    async with session_factory() as session, session.begin():
        for start in range(0, len(values), INSERT_BATCH_SIZE):
            batch = values[start : start + INSERT_BATCH_SIZE]
            result = await session.execute(insert(model).values(batch).on_conflict_do_nothing())
            inserted += result.rowcount
    return inserted


class AgentSettingsRepository:
    def __init__(self, session_factory: "async_sessionmaker[AsyncSession]") -> None:
        self._session_factory = session_factory

    async def get(self) -> AgentSettings | None:
        async with self._session_factory() as session:
            row = await session.get(AgentSettingsRow, AGENT_SETTINGS_ROW_ID)
            if row is None:
                return None
            return AgentSettings(
                instructions=row.instructions,
                model=row.model,
                supported_efforts=tuple(row.supported_efforts),
                reasoning_effort=row.reasoning_effort,
                verbosity=row.verbosity,
                updated_at=_as_utc(row.updated_at),
                updated_by=row.updated_by,
            )

    async def save(self, settings: AgentSettings) -> AgentSettings:
        async with self._session_factory() as session, session.begin():
            await session.merge(
                AgentSettingsRow(
                    id=AGENT_SETTINGS_ROW_ID,
                    instructions=settings.instructions,
                    model=settings.model,
                    supported_efforts=[str(effort) for effort in settings.supported_efforts],
                    reasoning_effort=settings.reasoning_effort,
                    verbosity=settings.verbosity,
                    updated_at=settings.updated_at,
                    updated_by=settings.updated_by,
                )
            )
        return settings


class ConversationRepository:
    def __init__(self, session_factory: "async_sessionmaker[AsyncSession]") -> None:
        self._session_factory = session_factory

    async def get(self, telegram_id: int) -> str | None:
        async with self._session_factory() as session:
            row = await session.get(UserConversationRow, telegram_id)
            return row.conversation_id if row else None

    async def set(self, telegram_id: int, conversation_id: str) -> None:
        async with self._session_factory() as session, session.begin():
            await session.merge(UserConversationRow(telegram_id=telegram_id, conversation_id=conversation_id))

    async def add_missing(self, conversations: "Iterable[tuple[int, str]]") -> int:
        """Insert conversations for users without one; return the number of inserted rows."""
        values = [{"telegram_id": tg_id, "conversation_id": conv_id} for tg_id, conv_id in conversations]
        return await _insert_missing(self._session_factory, UserConversationRow, values)

    async def delete(self, telegram_id: int) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(delete(UserConversationRow).where(UserConversationRow.telegram_id == telegram_id))

    async def delete_all(self) -> int:
        async with self._session_factory() as session, session.begin():
            result = await session.execute(delete(UserConversationRow))
            return result.rowcount

    async def count(self) -> int:
        async with self._session_factory() as session:
            return await session.scalar(select(func.count()).select_from(UserConversationRow)) or 0


class LogMessageRepository:
    def __init__(self, session_factory: "async_sessionmaker[AsyncSession]") -> None:
        self._session_factory = session_factory

    async def add_missing(self, chat_id: int, mapping: "Iterable[tuple[int, int]]") -> int:
        """Insert unknown (message_id, telegram_id) pairs; return the number of inserted rows."""
        values = [{"chat_id": chat_id, "message_id": msg_id, "telegram_id": tg_id} for msg_id, tg_id in mapping]
        return await _insert_missing(self._session_factory, LogMessageRow, values)

    async def get_user_id(self, chat_id: int, message_id: int) -> int | None:
        async with self._session_factory() as session:
            row = await session.get(LogMessageRow, (chat_id, message_id))
            return row.telegram_id if row else None


class MetaRepository:
    def __init__(self, session_factory: "async_sessionmaker[AsyncSession]") -> None:
        self._session_factory = session_factory

    async def get(self, key: str) -> str | None:
        async with self._session_factory() as session:
            row = await session.get(MetaRow, key)
            return row.value if row else None

    async def set(self, key: str, value: str) -> None:
        async with self._session_factory() as session, session.begin():
            await session.merge(MetaRow(key=key, value=value))
