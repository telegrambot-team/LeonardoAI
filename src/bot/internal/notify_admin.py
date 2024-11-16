from pathlib import Path

from aiogram import Bot

from config import Settings

folder = Path.cwd().name


async def on_startup_notify(bot: Bot, settings: Settings):
    await bot.send_message(settings.ADMIN, f"{folder} started\n\n/start", disable_notification=True)


async def on_shutdown_notify(bot: Bot, settings: Settings):
    await bot.send_message(settings.ADMIN, f"{folder} shutdown", disable_notification=True)
