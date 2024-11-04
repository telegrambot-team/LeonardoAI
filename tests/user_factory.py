from aiogram.types import User as TelegramUser
from faker import Faker
from polyfactory.factories.pydantic_factory import ModelFactory


class TelegramUserFactory(ModelFactory[TelegramUser]):
    __faker__ = Faker(locale="ru_RU")
    __model__ = TelegramUser
    __set_as_default_factory_for_type__ = True

    @classmethod
    def first_name(cls) -> str:
        return cls.__faker__.first_name()

    @classmethod
    def last_name(cls) -> str:
        return cls.__faker__.last_name()

    @classmethod
    def username(cls) -> str:
        return cls.__faker__.user_name()

    @classmethod
    def language_code(cls) -> str:
        return cls.__faker__.language_code()
