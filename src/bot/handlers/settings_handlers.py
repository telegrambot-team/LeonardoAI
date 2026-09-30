from typing import TYPE_CHECKING

import logging

from contextlib import suppress

import openai

from aiogram import F, Router, html
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.callback_answer import CallbackAnswerMiddleware

from ai_client import ModelCheckError
from bot.filters import IsModerator
from bot.internal.enums import SettingsAction, SettingsStates
from bot.keyboards import SettingsOption
from bot.settings_views import (
    DATETIME_FORMAT,
    chars_label,
    checking_view,
    clear_view,
    effort_view,
    main_view,
    model_checking_view,
    model_view,
    prompt_upload_view,
    prompt_view,
    verbosity_view,
)
from bot.telegram_safe import safe_delete_message, safe_edit_text
from schemas import ReasoningEffort, Verbosity
from services.agent_settings import InvalidSettingValueError

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext

    from bot.settings_views import View
    from services.agent_settings import AgentSettingsService
    from services.conversations import ConversationService

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(IsModerator(), F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(IsModerator())
router.callback_query.middleware(CallbackAnswerMiddleware())

PROMPT_FILE_EXTENSIONS = (".md", ".txt")
MAX_PROMPT_FILE_BYTES = 200 * 1024
WINDOW_ID_KEY = "settings_window_id"
# Commands like /start must reach their handlers even while the menu waits for input
NOT_A_COMMAND = ~F.text.startswith("/")


async def _edit_window(callback: CallbackQuery, view: "View") -> None:
    text, markup = view
    await safe_edit_text(callback.message, text, reply_markup=markup)


async def _replace_window(message: Message, state: "FSMContext", view: "View") -> Message:
    """Send the settings window below the latest message and remove the previous one."""
    data = await state.get_data()
    if window_id := data.get(WINDOW_ID_KEY):
        with suppress(TelegramBadRequest):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=window_id)
    text, markup = view
    window = await message.answer(text, reply_markup=markup)
    await state.update_data({WINDOW_ID_KEY: window.message_id})
    return window


@router.message(Command("settings"))
async def settings_command(
    message: Message, state: "FSMContext", agent_settings_service: "AgentSettingsService"
) -> None:
    await state.set_state(None)
    await _replace_window(message, state, main_view(await agent_settings_service.get()))


def _on(action: SettingsAction):
    return router.callback_query(SettingsOption.filter(F.action == action))


async def _remember_window(callback: CallbackQuery, state: "FSMContext") -> None:
    await state.update_data({WINDOW_ID_KEY: callback.message.message_id})


@_on(SettingsAction.MAIN)
async def main_screen(callback: CallbackQuery, state: "FSMContext", agent_settings_service: "AgentSettingsService"):
    await state.set_state(None)
    await _edit_window(callback, main_view(await agent_settings_service.get()))


@_on(SettingsAction.CLOSE)
async def close_screen(callback: CallbackQuery, state: "FSMContext") -> None:
    await state.set_state(None)
    await safe_delete_message(callback.message)


@_on(SettingsAction.PROMPT)
async def prompt_screen(callback: CallbackQuery, state: "FSMContext", agent_settings_service: "AgentSettingsService"):
    await state.set_state(None)
    await _edit_window(callback, prompt_view(await agent_settings_service.get()))


@_on(SettingsAction.PROMPT_DOWNLOAD)
async def prompt_download(
    callback: CallbackQuery, state: "FSMContext", agent_settings_service: "AgentSettingsService"
) -> None:
    settings = await agent_settings_service.get()
    if not settings.instructions:
        await _edit_window(callback, prompt_view(settings, "ℹ️ Промпт пустой, скачивать нечего"))
        return
    file = BufferedInputFile(
        settings.instructions.encode("utf-8"), filename=f"prompt_{settings.updated_at:%Y-%m-%d_%H-%M}.md"
    )
    caption = f"Промпт от {settings.updated_at.strftime(DATETIME_FORMAT)}, {chars_label(len(settings.instructions))}"
    await callback.message.answer_document(file, caption=caption)
    await _remember_window(callback, state)
    await _replace_window(callback.message, state, prompt_view(settings, "📥 Текущий промпт — файл выше"))


@_on(SettingsAction.PROMPT_UPLOAD)
async def prompt_upload_screen(callback: CallbackQuery, state: "FSMContext") -> None:
    await state.set_state(SettingsStates.WAITING_PROMPT)
    await _remember_window(callback, state)
    await _edit_window(callback, prompt_upload_view())


@_on(SettingsAction.MODEL)
async def model_screen(callback: CallbackQuery, state: "FSMContext", agent_settings_service: "AgentSettingsService"):
    await state.set_state(SettingsStates.WAITING_MODEL)
    await _remember_window(callback, state)
    await _edit_window(callback, model_view(await agent_settings_service.get()))


@_on(SettingsAction.EFFORT)
async def effort_screen(callback: CallbackQuery, agent_settings_service: "AgentSettingsService") -> None:
    await _edit_window(callback, effort_view(await agent_settings_service.get()))


@_on(SettingsAction.SET_EFFORT)
async def set_effort(
    callback: CallbackQuery, callback_data: SettingsOption, agent_settings_service: "AgentSettingsService"
) -> None:
    try:
        effort = ReasoningEffort(callback_data.value)
        settings = await agent_settings_service.set_effort(effort, updated_by=callback.from_user.id)
    except (ValueError, InvalidSettingValueError) as exc:
        await _edit_window(callback, effort_view(await agent_settings_service.get(), f"❌ {html.quote(str(exc))}"))
        return
    await _edit_window(callback, effort_view(settings, f"✅ Reasoning effort: {settings.reasoning_effort}"))


@_on(SettingsAction.VERBOSITY)
async def verbosity_screen(callback: CallbackQuery, agent_settings_service: "AgentSettingsService") -> None:
    await _edit_window(callback, verbosity_view(await agent_settings_service.get()))


@_on(SettingsAction.SET_VERBOSITY)
async def set_verbosity(
    callback: CallbackQuery, callback_data: SettingsOption, agent_settings_service: "AgentSettingsService"
) -> None:
    await _edit_window(callback, checking_view())
    try:
        verbosity = Verbosity(callback_data.value)
        settings = await agent_settings_service.set_verbosity(verbosity, updated_by=callback.from_user.id)
    except (ValueError, ModelCheckError, openai.APIError) as exc:
        notice = f"❌ OpenAI не принял настройку: {html.quote(str(exc))}"
        await _edit_window(callback, verbosity_view(await agent_settings_service.get(), notice))
        return
    await _edit_window(callback, verbosity_view(settings, f"✅ Verbosity: {settings.verbosity}"))


@_on(SettingsAction.CLEAR)
async def clear_screen(callback: CallbackQuery, conversation_service: "ConversationService") -> None:
    await _edit_window(callback, clear_view(await conversation_service.count()))


@_on(SettingsAction.CLEAR_CONFIRM)
async def clear_confirm(
    callback: CallbackQuery,
    agent_settings_service: "AgentSettingsService",
    conversation_service: "ConversationService",
) -> None:
    cleared = await conversation_service.forget_all()
    logger.info("Moderator %s cleared %s conversations", callback.from_user.id, cleared)
    view = main_view(await agent_settings_service.get(), f"✅ Очищено диалогов: {cleared}")
    await _edit_window(callback, view)


@router.message(StateFilter(SettingsStates.WAITING_PROMPT), F.document)
async def prompt_file_handler(
    message: Message, state: "FSMContext", agent_settings_service: "AgentSettingsService"
) -> None:
    document = message.document
    file_name = (document.file_name or "").lower()
    if not file_name.endswith(PROMPT_FILE_EXTENSIONS):
        await _replace_window(message, state, prompt_upload_view("❌ Нужен файл .md или .txt"))
        return
    if document.file_size and document.file_size > MAX_PROMPT_FILE_BYTES:
        await _replace_window(message, state, prompt_upload_view("❌ Файл слишком большой, максимум 200 КБ"))
        return

    content = await message.bot.download(document)
    try:
        text = content.read().decode("utf-8-sig")
        settings = await agent_settings_service.set_instructions(text, updated_by=message.from_user.id)
    except UnicodeDecodeError:
        await _replace_window(message, state, prompt_upload_view("❌ Файл должен быть в кодировке UTF-8"))
        return
    except InvalidSettingValueError as exc:
        await _replace_window(message, state, prompt_upload_view(f"❌ {html.quote(str(exc))}"))
        return

    logger.info("Moderator %s updated the prompt (%s chars)", message.from_user.id, len(settings.instructions))
    await state.set_state(None)
    notice = f"✅ Промпт обновлён: {chars_label(len(settings.instructions))}"
    await _replace_window(message, state, prompt_view(settings, notice))


@router.message(StateFilter(SettingsStates.WAITING_PROMPT), NOT_A_COMMAND)
async def prompt_wrong_input_handler(message: Message, state: "FSMContext") -> None:
    await _replace_window(message, state, prompt_upload_view("❌ Пришлите промпт файлом .md или .txt"))


@router.message(StateFilter(SettingsStates.WAITING_MODEL), F.text, NOT_A_COMMAND)
async def model_input_handler(
    message: Message, state: "FSMContext", agent_settings_service: "AgentSettingsService"
) -> None:
    model = message.text.strip()
    window = await _replace_window(message, state, model_checking_view(model))
    try:
        result = await agent_settings_service.set_model(model, updated_by=message.from_user.id)
    except (InvalidSettingValueError, ModelCheckError, openai.APIError) as exc:
        notice = f"❌ Модель не сохранена: {html.quote(str(exc))}"
        text, markup = model_view(await agent_settings_service.get(), notice)
        await safe_edit_text(window, text, reply_markup=markup)
        return

    settings = result.settings
    logger.info("Moderator %s set model %s", message.from_user.id, settings.model)
    notice = f"✅ Модель: {html.quote(settings.model)}"
    if not settings.supported_efforts:
        notice += "\nℹ️ Модель не поддерживает reasoning effort"
    elif result.effort_changed and result.previous_effort is None:
        notice += f"\nℹ️ Reasoning effort: {settings.reasoning_effort}"
    elif result.effort_changed:
        notice += (
            f"\nℹ️ Reasoning effort изменён: {result.previous_effort} → {settings.reasoning_effort}, "
            "прежний уровень модель не поддерживает"
        )
    await state.set_state(None)
    text, markup = main_view(settings, notice)
    await safe_edit_text(window, text, reply_markup=markup)


@router.message(StateFilter(SettingsStates.WAITING_MODEL), NOT_A_COMMAND)
async def model_wrong_input_handler(
    message: Message, state: "FSMContext", agent_settings_service: "AgentSettingsService"
) -> None:
    view = model_view(await agent_settings_service.get(), "❌ Пришлите название модели текстом")
    await _replace_window(message, state, view)
