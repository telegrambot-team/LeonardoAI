from datetime import datetime

from sqlalchemy import BigInteger, MetaData, String, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    __abstract__ = True
    metadata = MetaData()
    __table_args__ = {"extend_existing": True}

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    full_name: Mapped[str]
    username: Mapped[str | None] = mapped_column(String(32))

    def __str__(self):
        return f"User(full_name={self.full_name}, telegram_id={self.telegram_id}, username={self.username}"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return (
            self.telegram_id == other.telegram_id
            and self.full_name == other.full_name
            and self.username == other.username
        )


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)

    label: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    file_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
