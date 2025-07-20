from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import BaseStorage, StorageKey


def get_global_context(bot: Bot, storage: BaseStorage) -> FSMContext:
    """Return FSM context for storing global bot data."""
    key = StorageKey(bot_id=bot.id, chat_id=0, user_id=0)
    return FSMContext(storage=storage, key=key)


async def init_global(storage: BaseStorage, bot: Bot) -> None:
    """Initialize global context with default values."""
    ctx = get_global_context(bot, storage)
    data = await ctx.get_data()
    if "log_user_message_map" not in data:
        await ctx.update_data(log_user_message_map={})
