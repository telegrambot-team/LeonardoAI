from typing import TYPE_CHECKING

from aiogram import html

from bot.internal.enums import SettingsAction
from bot.keyboards import (
    settings_back_kbd,
    settings_cancel_kbd,
    settings_clear_kbd,
    settings_effort_kbd,
    settings_main_kbd,
    settings_prompt_kbd,
    settings_verbosity_kbd,
)

if TYPE_CHECKING:
    from aiogram.types import InlineKeyboardMarkup

    from schemas import AgentSettings

type View = tuple[str, "InlineKeyboardMarkup"]

DATETIME_FORMAT = "%d.%m.%Y %H:%M UTC"


def chars_label(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        word = "символ"
    elif 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        word = "символа"
    else:
        word = "символов"
    return f"{count} {word}"


def _with_notice(text: str, notice: str | None) -> str:
    return f"{notice}\n\n{text}" if notice else text


def _effort_label(settings: "AgentSettings") -> str:
    return str(settings.reasoning_effort) if settings.reasoning_effort else "не поддерживается моделью"


def main_view(settings: "AgentSettings", notice: str | None = None) -> View:
    text = (
        "⚙️ <b>Настройки ассистента</b>\n\n"
        f"📝 Промпт: {chars_label(len(settings.instructions))}\n"
        f"🤖 Модель: <code>{html.quote(settings.model)}</code>\n"
        f"🧠 Reasoning effort: <code>{_effort_label(settings)}</code>\n"
        f"💬 Verbosity: <code>{settings.verbosity}</code>\n"
        f"🕓 Обновлено: {settings.updated_at.strftime(DATETIME_FORMAT)}\n\n"
        "Что поменять?"
    )
    return _with_notice(text, notice), settings_main_kbd(settings)


def prompt_view(settings: "AgentSettings", notice: str | None = None) -> View:
    text = (
        "📝 <b>Промпт</b>\n\n"
        f"Сейчас: {chars_label(len(settings.instructions))}, обновлён {settings.updated_at.strftime(DATETIME_FORMAT)}\n\n"
        "Скачайте текущий промпт файлом или загрузите новый."
    )
    return _with_notice(text, notice), settings_prompt_kbd()


def prompt_upload_view(notice: str | None = None) -> View:
    text = (
        "📤 <b>Загрузка промпта</b>\n\n"
        "Пришлите новый промпт файлом <code>.md</code> или <code>.txt</code> в кодировке UTF-8.\n"
        "Текущий промпт будет заменён целиком."
    )
    return _with_notice(text, notice), settings_cancel_kbd(SettingsAction.PROMPT)


def model_view(settings: "AgentSettings", notice: str | None = None) -> View:
    text = (
        "🤖 <b>Модель</b>\n\n"
        f"Сейчас: <code>{html.quote(settings.model)}</code>\n\n"
        "Пришлите название новой модели сообщением, например <code>gpt-6-luna</code>.\n"
        "Перед сохранением я проверю, что OpenAI принимает эту модель."
    )
    return _with_notice(text, notice), settings_cancel_kbd()


def model_checking_view(model: str) -> View:
    return f"⏳ Проверяю модель <code>{html.quote(model)}</code>…", settings_back_kbd()


def effort_view(settings: "AgentSettings", notice: str | None = None) -> View:
    supported = ", ".join(str(effort) for effort in settings.supported_efforts)
    text = (
        "🧠 <b>Reasoning effort</b>\n\n"
        f"Модель <code>{html.quote(settings.model)}</code> поддерживает: {supported}\n\n"
        "Выберите уровень:"
    )
    return _with_notice(text, notice), settings_effort_kbd(settings)


def verbosity_view(settings: "AgentSettings", notice: str | None = None) -> View:
    text = "💬 <b>Verbosity</b>\n\nНасколько развёрнуто отвечает модель. Выберите уровень:"
    return _with_notice(text, notice), settings_verbosity_kbd(settings)


def checking_view() -> View:
    return "⏳ Проверяю настройку в OpenAI…", settings_back_kbd()


def clear_view(conversations_count: int) -> View:
    text = (
        "🗑 <b>Очистить все диалоги?</b>\n\n"
        f"Сохранено диалогов: {conversations_count}.\n"
        "Все пользователи начнут разговор с ассистентом заново. Отменить это действие нельзя."
    )
    return text, settings_clear_kbd()
