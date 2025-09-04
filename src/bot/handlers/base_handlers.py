import logging
from contextlib import suppress
from urllib.parse import urlencode

import aiogram.utils.formatting
import openai

from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from aiogram.utils.chat_action import ChatActionSender

from ai_client import AIClient
from bot.global_ctx import get_global_context
from bot.handlers.consts import IMGS, TEXTS
from bot.internal.enums import AfterSurgeryMenuBtns, AIMenuBtns, MainMenuBtns, ModeratorMenuBtns, SurgeryMenuBtns
from bot.internal.lexicon import texts
from bot.keyboards import (
    AfterSurgeryMenuOption,
    AIMenuOption,
    MainMenuOption,
    ModeratorMenuOption,
    SurgeryMenuOption,
    after_surgery_kbd,
    ai_kbd,
    before_surgery_kbd,
    get_model_kb,
    start_kbd,
    start_moderator_kbd,
)
from bot.md_utils import refactor_string

logger = logging.getLogger(__name__)

router = Router()


class StatesBot(StatesGroup):
    IN_AI_DIALOG = State()


def get_start_text(full_name: str):
    return (
        aiogram.html.bold(f"Виртуальный доктор приветствует вас, {full_name}!\n\n")
        + "Выполните команду /start чтобы в любой момент вернутся в главное меню."
    )


@router.message(CommandStart())
async def start_message(message: types.Message, state: FSMContext, settings) -> None:
    await state.set_state()
    kb = start_moderator_kbd if message.from_user.id == settings.MODERATOR else start_kbd
    await message.answer(get_start_text(message.from_user.full_name), reply_markup=kb)


@router.message(Command("model"))
async def model_message(message: types.Message):
    await message.answer(texts["welcome"], reply_markup=get_model_kb())


@router.callback_query(MainMenuOption.filter(F.action == MainMenuBtns.AI_LEONARDO))
async def ai_leonardo_handler_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(StatesBot.IN_AI_DIALOG)
    await callback.message.edit_text(
        "Напишите своё сообщение в чат чтобы продолжить диалог, или начните новый диалог нажав на кнопку ниже",
        reply_markup=ai_kbd,
    )


@router.callback_query(MainMenuOption.filter())
async def main_menu_handler(callback: types.CallbackQuery, callback_data: MainMenuOption):
    await callback.answer()
    back_kbd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=SurgeryMenuOption(action=SurgeryMenuBtns.BACK).pack())]
        ]
    )
    match callback_data.action:
        case MainMenuBtns.BEFORE_SURGERY:
            await callback.message.edit_text("Рекомендации перед и после операции", reply_markup=before_surgery_kbd)
        case MainMenuBtns.ASK_QUESTION:
            await callback.message.edit_text(
                "Вы можете задать вопрос написав мне в телеграме: @StaisupovValeri\n\n"
                "Или в вотсапе : https://wa.me/79313009933",
                reply_markup=back_kbd,
            )
        case MainMenuBtns.SCHEDULE_CONSULTATION:
            link = f"https://wa.me/79213713864?{
                urlencode({'text': 'Здравствуйте! Я хочу записаться на консультацию к Стайсупову Валерию Юрьевичу.'})
            }"
            escaped_link = aiogram.html.link("ссылке", link)
            await callback.message.edit_text(
                f"Вы можете записаться на консультацию в WhatsApp по {escaped_link}\n\n"
                f""
                f"Или по телефону: +7-812-403-02-01",
                reply_markup=back_kbd,
            )
        case MainMenuBtns.SCHEDULE_SURGERY:
            link = f"https://wa.me/79213713864?{urlencode({'text': 'Здравствуйте! Я хочу записаться на операцию к Стайсупову Валерию Юрьевичу.'})}"
            escaped_link = aiogram.html.link("ссылке", link)
            await callback.message.edit_text(
                f"Вы можете записаться на операцию в WhatsApp по {escaped_link}\n\nИли по телефону: +7-812-403-02-01",
                reply_markup=back_kbd,
            )
        case MainMenuBtns.MODELLING:
            await callback.message.answer(texts["welcome"], reply_markup=get_model_kb())


@router.callback_query(SurgeryMenuOption.filter())
async def analyze_list_handler(callback: types.CallbackQuery, callback_data: SurgeryMenuOption, settings) -> None:
    match callback_data.action:
        case SurgeryMenuBtns.ANALYZE_LIST:
            fname = "data/Список Анализов.pdf"
            await callback.message.answer_document(FSInputFile(path=fname))
        case SurgeryMenuBtns.MEDICINE_AFTER:
            await callback.message.edit_text("Лекарства после операции", reply_markup=after_surgery_kbd)
        case SurgeryMenuBtns.BACK:
            kb = start_moderator_kbd if callback.from_user.id == settings.MODERATOR else start_kbd
            await callback.message.edit_text(get_start_text(callback.from_user.full_name), reply_markup=kb)


@router.callback_query(AfterSurgeryMenuOption.filter())
async def after_surgery_handler(callback: types.CallbackQuery, callback_data: AfterSurgeryMenuOption):
    if callback_data.action == AfterSurgeryMenuBtns.BACK:
        await callback.message.answer("Рекомендации перед и после операции", reply_markup=before_surgery_kbd)
        await callback.message.delete()
        return

    try:
        photo = InputMediaPhoto(media=IMGS[callback_data.action], caption=TEXTS[callback_data.action])
        try:
            await callback.message.edit_media(photo, reply_markup=after_surgery_kbd)
        except TelegramBadRequest:
            await callback.message.answer_photo(
                IMGS[callback_data.action], caption=TEXTS[callback_data.action], reply_markup=after_surgery_kbd
            )
    except TelegramBadRequest:
        pass


@router.callback_query(AIMenuOption.filter())
async def ai_menu_handler(
    callback: types.CallbackQuery, ai_client: AIClient, state: FSMContext, callback_data: AIMenuOption, settings
) -> None:
    if callback_data.action == AIMenuBtns.BACK:
        await state.set_state()
        kb = start_moderator_kbd if callback.from_user.id == settings.MODERATOR else start_kbd
        await callback.message.edit_text(get_start_text(callback.from_user.full_name), reply_markup=kb)
        return

    data = await state.get_data()

    if "ai_thread_id" in data:
        try:
            await ai_client.delete_thread(data["ai_thread_id"])
        except openai.NotFoundError:
            logger.warning("Thread %s not found", data["ai_thread_id"])

    new_thread_id = await ai_client.new_thread()
    await state.update_data(ai_thread_id=new_thread_id)
    await callback.message.answer("Чем я могу помочь?")


@router.callback_query(ModeratorMenuOption.filter())
async def moderator_menu_handler(
    callback: types.CallbackQuery, callback_data: ModeratorMenuOption, state: FSMContext, settings
) -> None:
    if callback.from_user.id != settings.MODERATOR:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    if callback_data.action == ModeratorMenuBtns.CLEAR_CONTEXTS:
        await state.storage.redis.flushdb()
        await state.set_state()
        await callback.message.edit_text("Контекст всех пользователей очищен.", reply_markup=start_moderator_kbd)


@router.message(StatesBot.IN_AI_DIALOG)
async def ai_leonardo_handler(message: types.Message, ai_client: AIClient, settings, state: FSMContext):
    logger.info("Processing user message %s from %s", message.message_id, message.from_user.id)
    data = await state.get_data()
    new_thread_id = data.get("ai_thread_id", None)
    if new_thread_id is None:
        new_thread_id = await ai_client.new_thread()
        await state.update_data(ai_thread_id=new_thread_id)
    with suppress(TelegramBadRequest):
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
            response = await ai_client.get_response(new_thread_id, message.text)
        except openai.NotFoundError:
            logger.warning("Thread %s not found", data["ai_thread_id"])
            response = None
            await state.update_data(ai_thread_id=None)

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
async def moderator_reply_handler(message: types.Message, state: FSMContext) -> None:
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
