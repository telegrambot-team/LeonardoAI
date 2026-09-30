from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class AgentSettingsRow(Base):
    """Single-row table with the current agent configuration (id is always 1)."""

    __tablename__ = "agent_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    instructions: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(128))
    supported_efforts: Mapped[list[str]] = mapped_column(JSON)
    reasoning_effort: Mapped[str | None] = mapped_column(String(16))
    verbosity: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_by: Mapped[int | None] = mapped_column(BigInteger)


class UserConversationRow(Base):
    __tablename__ = "user_conversations"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    conversation_id: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LogMessageRow(Base):
    """Maps a message forwarded to the log chat to the user who sent the original."""

    __tablename__ = "log_messages"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MetaRow(Base):
    __tablename__ = "meta"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
