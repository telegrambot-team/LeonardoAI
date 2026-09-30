from typing import Annotated

import sys

from logging.handlers import RotatingFileHandler
from pathlib import Path

from pydantic import RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from schemas import ReasoningEffort, Verbosity


class Settings(BaseSettings):
    BOT_TOKEN: SecretStr
    ADMIN: int
    MODERATOR: int
    OPENAI_API_KEY: SecretStr
    CHAT_LOG_ID: int
    # Comma-separated ids of the OpenAI vector stores with the knowledge base
    VECTOR_STORE_IDS: Annotated[tuple[str, ...], NoDecode]
    REDIS_URL: RedisDsn = "redis://127.0.0.1:6379/0"

    DB_PATH: Path = Path("db/bot.db")
    INITIAL_PROMPT_PATH: Path | None = None
    DEFAULT_MODEL: str = "gpt-6-luna"
    DEFAULT_EFFORT: ReasoningEffort = ReasoningEffort.MEDIUM
    DEFAULT_VERBOSITY: Verbosity = Verbosity.MEDIUM
    OPENAI_TIMEOUT_SECONDS: float = 120.0
    OPENAI_MAX_RETRIES: int = 3

    # extra="ignore": obsolete variables (e.g. ASSISTANT_ID) left in .env must not break the start
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    @field_validator("VECTOR_STORE_IDS", mode="before")
    @classmethod
    def _split_vector_store_ids(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return value


def get_logging_config(app_name: str):
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "main": {
                "format": "%(asctime)s.%(msecs)03d [%(levelname)8s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s",
                "datefmt": "%d.%m.%Y %H:%M:%S%z",
            },
            "errors": {
                "format": "%(asctime)s.%(msecs)03d [%(levelname)8s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s",
                "datefmt": "%d.%m.%Y %H:%M:%S%z",
            },
        },
        "handlers": {
            "stdout": {"class": "logging.StreamHandler", "level": "DEBUG", "formatter": "main", "stream": sys.stdout},
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "WARNING",
                "formatter": "errors",
                "stream": sys.stderr,
            },
            "file_info": {
                "()": RotatingFileHandler,
                "level": "INFO",
                "formatter": "main",
                "filename": f"logs/{app_name}.log",
                "maxBytes": 5000000,
                "backupCount": 3,
                "encoding": "utf-8",
            },
            "file_debug": {
                "()": RotatingFileHandler,
                "level": "DEBUG",
                "formatter": "main",
                "filename": f"logs/{app_name}_debug.log",
                "maxBytes": 5000000,
                "backupCount": 3,
                "encoding": "utf-8",
            },
        },
        "loggers": {"root": {"level": "DEBUG", "handlers": ["stdout", "stderr", "file_info", "file_debug"]}},
    }
