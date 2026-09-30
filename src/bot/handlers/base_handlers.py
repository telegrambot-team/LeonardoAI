from typing import TYPE_CHECKING

import logging

from asyncio import sleep
from contextlib import suppress
from urllib.parse import urlencode

import openai

from aiogram import F, Router, html
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message
from aiogram.utils.chat_action import ChatActionSender

from bot.handlers.consts import IMGS, TEXTS
from bot.internal.enums import AfterSurgeryMenuBtns, MainMenuBtns, SurgeryMenuBtns
from bot.internal.lexicon import texts
from bot.keyboards import (
    AfterSurgeryMenuOption,
    MainMenuOption,
    SurgeryMenuOption,
    after_surgery_kbd,
    back_to_start_kbd,
    start_kbd,
)
from bot.sending import answer_ai_text
from bot.telegram_safe import safe_delete_message, safe_edit_media, safe_edit_text
from services.conversations import AIBadRequestError

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext

    from config import Settings
    from services.conversations import ConversationService
    from services.log_chat import LogChatService

logger = logging.getLogger(__name__)

router = Router()

BAD_OPENAI_REQUEST_MESSAGE = "Не получилось обработать запрос. Попробуйте ещё раз или переформулируйте вопрос."
OPENAI_UNAVAILABLE_MESSAGE = "Сервис временно недоступен. Пожалуйста, попробуйте чуть позже."
EMPTY_RESPONSE_MESSAGE = "Извините, я отвлекся, давайте начнём новый разговор 🙈"


@router.message(CommandStart())
async def start_message(message: Message, state: "FSMContext", conversation_service: "ConversationService") -> None:
    await state.clear()
    await conversation_service.forget(message.from_user.id)
    await message.answer(texts["start_text"], reply_markup=start_kbd)
    await sleep(1)
    await message.answer(texts["hello_text"])


@router.callback_query(MainMenuOption.filter(F.action == MainMenuBtns.SCHEDULE_CONSULTATION))
async def schedule_consultation_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    whatsapp_text = "Здравствуйте! Я хочу записаться к доктору Стайсупову Валерию Юрьевичу."
    link = "https://wa.me/79213713864?" + urlencode({"text": whatsapp_text})
    escaped_link = html.link("ссылке", link)
    await safe_edit_text(
        callback.message,
        f"Вы можете записаться к доктору в WhatsApp по {escaped_link}\n\n"
        "Или через личного администратора\n"
        "Whats App, Telegram: +7-931-330-88-33",
        reply_markup=back_to_start_kbd,
    )


@router.callback_query(SurgeryMenuOption.filter())
async def analyze_list_handler(callback: CallbackQuery, callback_data: SurgeryMenuOption) -> None:
    await callback.answer()
    match callback_data.action:
        case SurgeryMenuBtns.ANALYZE_LIST:
            fname = "data/Список Анализов.pdf"
            await callback.message.answer_document(FSInputFile(path=fname))
        case SurgeryMenuBtns.MEDICINE_AFTER:
            await safe_edit_text(callback.message, "Лекарства после операции", reply_markup=after_surgery_kbd)
        case SurgeryMenuBtns.BACK:
            await safe_edit_text(callback.message, texts["start_text"], reply_markup=start_kbd)


@router.callback_query(AfterSurgeryMenuOption.filter())
async def after_surgery_handler(callback: CallbackQuery, callback_data: AfterSurgeryMenuOption) -> None:
    await callback.answer()
    if callback_data.action == AfterSurgeryMenuBtns.BACK:
        await callback.message.answer(texts["start_text"], reply_markup=start_kbd)
        await safe_delete_message(callback.message)
        return

    try:
        photo = InputMediaPhoto(media=IMGS[callback_data.action], caption=TEXTS[callback_data.action])
        try:
            await safe_edit_media(callback.message, photo, reply_markup=after_surgery_kbd)
        except TelegramBadRequest:
            await callback.message.answer_photo(
                IMGS[callback_data.action], caption=TEXTS[callback_data.action], reply_markup=after_surgery_kbd
            )
    except TelegramBadRequest:
        pass


@router.message(
    lambda message, settings: message.chat.id == settings.CHAT_LOG_ID,
    lambda message, settings: message.from_user.id == settings.MODERATOR,
    F.reply_to_message,
)
async def moderator_reply_handler(message: Message, log_chat_service: "LogChatService") -> None:
    """Forward moderator replies from log chat to the original user."""
    logger.info("Processing moderator reply %s to %s", message.message_id, message.reply_to_message.message_id)

    user_id = await log_chat_service.find_user(message.reply_to_message.message_id)
    if user_id is None:
        logger.warning("No user_id found for log message %s", message.reply_to_message.message_id)
        return

    if message.text:
        await message.bot.send_message(chat_id=user_id, text=message.text)


async def _forward_to_log(message: Message, settings: "Settings", log_chat_service: "LogChatService") -> None:
    # Logging must never break the answer to the user
    try:
        forwarded = await message.forward(settings.CHAT_LOG_ID)
        await log_chat_service.remember([forwarded.message_id], message.from_user.id)
    except TelegramAPIError as exc:
        logger.warning("Failed to forward message %s to log chat: %s", message.message_id, exc)


@router.message(F.chat.type == ChatType.PRIVATE)
async def ai_leonardo_handler(
    message: Message,
    settings: "Settings",
    conversation_service: "ConversationService",
    log_chat_service: "LogChatService",
) -> None:
    logger.info("Processing user message %s from %s", message.message_id, message.from_user.id)
    if not message.text or not message.text.strip():
        await message.answer("Пожалуйста, отправьте текстовый вопрос.")
        return

    await _forward_to_log(message, settings, log_chat_service)

    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        try:
            response = await conversation_service.ask(message.from_user.id, message.text.strip())
        except AIBadRequestError:
            await message.answer(BAD_OPENAI_REQUEST_MESSAGE)
            return
        except openai.APIError:
            await message.answer(OPENAI_UNAVAILABLE_MESSAGE)
            raise

    if response is None:
        await message.answer(EMPTY_RESPONSE_MESSAGE)
        return

    for answer in await answer_ai_text(message, response):
        with suppress(TelegramAPIError):
            await answer.forward(settings.CHAT_LOG_ID)


@router.callback_query()
async def outdated_button_handler(callback: CallbackQuery) -> None:
    # Buttons of removed menus may still be present in old messages
    await callback.answer("Эта кнопка устарела. Нажмите /start", show_alert=True)
