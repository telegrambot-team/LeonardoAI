import logging

from asyncio import sleep
from contextlib import suppress
from urllib.parse import urlencode

import openai

from aiogram import Router, html
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)
from aiogram.utils.chat_action import ChatActionSender

from ai_client import AIClient
from bot.global_ctx import get_global_context
from bot.handlers.consts import IMGS, TEXTS
from bot.internal.enums import (
    AfterSurgeryMenuBtns,
    AIMenuBtns,
    MainMenuBtns,
    ModeratorMenuBtns,
    StatesBot,
    SurgeryMenuBtns,
)
from bot.internal.lexicon import texts
from bot.keyboards import (
    AfterSurgeryMenuOption,
    AIMenuOption,
    MainMenuOption,
    ModeratorMenuOption,
    SurgeryMenuOption,
    after_surgery_kbd,
    before_surgery_kbd,
    start_kbd,
    start_moderator_kbd,
)
from bot.md_utils import refactor_string
from bot.telegram_safe import safe_delete_message, safe_edit_media, safe_edit_text
from config import Settings

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def start_message(message: Message, state: FSMContext, settings) -> None:
    await state.set_state(StatesBot.IN_AI_DIALOG)
    kb = start_moderator_kbd if message.from_user.id == settings.MODERATOR else start_kbd
    await message.answer(texts["start_text"], reply_markup=kb)
    await sleep(1)
    await message.answer(texts["hello_text"])


@router.callback_query(MainMenuOption.filter())
async def main_menu_handler(callback: CallbackQuery, callback_data: MainMenuOption, state: FSMContext):
    await callback.answer()
    back_kbd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=SurgeryMenuOption(action=SurgeryMenuBtns.BACK).pack())]
        ]
    )
    match callback_data.action:
        case MainMenuBtns.BEFORE_SURGERY:
            await state.set_state(StatesBot.IN_AI_DIALOG)
            await safe_edit_text(
                callback.message, "Рекомендации перед и после операции", reply_markup=before_surgery_kbd
            )
        case MainMenuBtns.SCHEDULE_CONSULTATION:
            await state.set_state(StatesBot.IN_AI_DIALOG)
            whatsapp_text = "Здравствуйте! Я хочу записаться к доктору Стайсупову Валерию Юрьевичу."
            link = f"https://wa.me/79213713864?{urlencode({'text': whatsapp_text})}"
            escaped_link = html.link("ссылке", link)
            await safe_edit_text(
                callback.message,
                f"Вы можете записаться к доктору в WhatsApp по {escaped_link}\n\n"
                "Или через личного администратора\n"
                "Whats App, Telegram: +7-931-330-88-33",
                reply_markup=back_kbd,
            )


@router.callback_query(SurgeryMenuOption.filter())
async def analyze_list_handler(
    callback: CallbackQuery, callback_data: SurgeryMenuOption, settings, state: FSMContext
) -> None:
    await callback.answer()
    match callback_data.action:
        case SurgeryMenuBtns.ANALYZE_LIST:
            fname = "data/Список Анализов.pdf"
            await callback.message.answer_document(FSInputFile(path=fname))
        case SurgeryMenuBtns.MEDICINE_AFTER:
            await safe_edit_text(callback.message, "Лекарства после операции", reply_markup=after_surgery_kbd)
        case SurgeryMenuBtns.BACK:
            kb = start_moderator_kbd if callback.from_user.id == settings.MODERATOR else start_kbd
            await state.set_state(StatesBot.IN_AI_DIALOG)
            await safe_edit_text(callback.message, texts["start_text"], reply_markup=kb)


@router.callback_query(AfterSurgeryMenuOption.filter())
async def after_surgery_handler(
    callback: CallbackQuery, callback_data: AfterSurgeryMenuOption, state: FSMContext, settings: Settings
):
    await callback.answer()
    if callback_data.action == AfterSurgeryMenuBtns.BACK:
        await state.set_state(StatesBot.IN_AI_DIALOG)
        kb = start_moderator_kbd if callback.from_user.id == settings.MODERATOR else start_kbd
        await callback.message.answer(texts["start_text"], reply_markup=kb)
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


@router.callback_query(AIMenuOption.filter())
async def ai_menu_handler(
    callback: CallbackQuery, ai_client: AIClient, state: FSMContext, callback_data: AIMenuOption, settings
) -> None:
    await callback.answer()
    if callback_data.action == AIMenuBtns.BACK:
        await state.set_state()
        kb = start_moderator_kbd if callback.from_user.id == settings.MODERATOR else start_kbd
        await safe_edit_text(callback.message, texts["start_text"], reply_markup=kb)
        return

    data = await state.get_data()

    if conversation_id := data.get("ai_conversation_id"):
        try:
            await ai_client.delete_conversation(conversation_id)
        except openai.NotFoundError:
            logger.warning("Conversation %s not found", conversation_id)

    new_conversation_id = await ai_client.new_conversation()
    await state.update_data(ai_conversation_id=new_conversation_id, ai_thread_id=None)
    await callback.message.answer("Чем я могу помочь?")


@router.callback_query(ModeratorMenuOption.filter())
async def moderator_menu_handler(
    callback: CallbackQuery, callback_data: ModeratorMenuOption, state: FSMContext, settings
) -> None:
    await callback.answer()
    if callback.from_user.id != settings.MODERATOR:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    if callback_data.action == ModeratorMenuBtns.CLEAR_CONTEXTS:
        await state.storage.redis.flushdb()
        await state.set_state()
        await safe_edit_text(
            callback.message, "Контекст всех пользователей очищен.", reply_markup=start_moderator_kbd
        )


@router.message(StateFilter(StatesBot.IN_AI_DIALOG))
async def ai_leonardo_handler(message: Message, ai_client: AIClient, settings, state: FSMContext):
    logger.info("Processing user message %s from %s", message.message_id, message.from_user.id)
    data = await state.get_data()
    conversation_id = data.get("ai_conversation_id")
    if not conversation_id:
        conversation_id = await ai_client.new_conversation()
        await state.update_data(ai_conversation_id=conversation_id, ai_thread_id=None)
    if not message.text or not message.text.strip():
        await message.answer("Пожалуйста, отправьте текстовый вопрос.")
        return
    user_text = message.text.strip()
    forwarded = await message.forward(settings.CHAT_LOG_ID)
    messages_to_handle = forwarded if isinstance(forwarded, list) else [forwarded]
    global_ctx = get_global_context(message.bot, state.storage)
    global_data = await global_ctx.get_data()
    log_user_message_map = global_data.get("log_user_message_map", {})
    for msg in messages_to_handle:
        log_user_message_map[msg.message_id] = message.from_user.id
    await global_ctx.update_data(log_user_message_map=log_user_message_map)
    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        try:
            response = await ai_client.get_response(conversation_id, user_text, user_id=str(message.from_user.id))
        except openai.NotFoundError:
            logger.warning("Conversation %s not found", conversation_id)
            conversation_id = await ai_client.new_conversation()
            await state.update_data(ai_conversation_id=conversation_id, ai_thread_id=None)
            response = await ai_client.get_response(conversation_id, user_text, user_id=str(message.from_user.id))
        except openai.BadRequestError as exc:
            logger.warning("OpenAI BadRequestError for user %s: %s", message.from_user.id, exc)
            conversation_id = await ai_client.new_conversation()
            await state.update_data(ai_conversation_id=conversation_id, ai_thread_id=None)
            await message.answer("Не получилось обработать запрос. Попробуйте ещё раз или переформулируйте вопрос.")
            return

        if response is None:
            await message.answer("Извините, я отвлекся, давайте начнём новый разговор 🙈")
            return
        cleaned_response = refactor_string(response)
        msg_answer = await message.answer(cleaned_response, parse_mode=ParseMode.MARKDOWN_V2)
        with suppress(TelegramBadRequest):
            await msg_answer.forward(settings.CHAT_LOG_ID)


@router.message(
    lambda message, settings: message.chat.id == settings.CHAT_LOG_ID,
    lambda message, settings: message.from_user.id == settings.MODERATOR,
    lambda message: bool(message.reply_to_message),
)
async def moderator_reply_handler(message: Message, state: FSMContext) -> None:
    """Forward moderator replies from log chat to the original user."""
    logger.info("Processing moderator reply %s to %s", message.message_id, message.reply_to_message.message_id)

    global_ctx = get_global_context(message.bot, state.storage)
    data = await global_ctx.get_data()
    log_user_message_map: dict[str, int] = data.get("log_user_message_map", {})

    user_id = log_user_message_map.get(str(message.reply_to_message.message_id))
    if user_id is None:
        logger.warning("No user_id found for log message %s", message.reply_to_message.message_id)
        return

    if message.text:
        await message.bot.send_message(chat_id=user_id, text=message.text)
