import logging
from urllib.parse import urlencode

import aiogram.utils.formatting
import openai
from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from aiogram.utils.chat_action import ChatActionSender

from ai_client import AIClient
from bot.handlers.consts import IMGS, TEXTS
from bot.keyboards import (
    AfterSurgeryMenuBtns,
    AfterSurgeryMenuOption,
    AIMenuBtns,
    AIMenuOption,
    MainMenuBtns,
    MainMenuOption,
    SurgeryMenuBtns,
    SurgeryMenuOption,
    after_surgery_kbd,
    ai_kbd,
    before_surgery_kbd,
    start_kbd,
)
from bot.md_utils import refactor_string

router = Router()


class StatesBot(StatesGroup):
    IN_AI_DIALOG = State()


def get_start_text(full_name: str):
    return (
        aiogram.html.bold(f"Виртуальный доктор приветствует вас, {full_name}!\n\n")
        + "Выполните команду /start чтобы в любой момент вернутся в главное меню."
    )


@router.message(CommandStart())
async def start_message(message: types.Message, state: FSMContext) -> None:
    await state.set_state()
    await message.answer(get_start_text(message.from_user.full_name), reply_markup=start_kbd)


@router.callback_query(MainMenuOption.filter(F.action == MainMenuBtns.AI_LEONARDO))
async def ai_leonardo_handler_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(StatesBot.IN_AI_DIALOG)
    await callback.message.edit_text(
        "Напишите своё сообщение в чат чтобы продолжить диалог," " или начните новый диалог нажав на кнопку ниже",
        reply_markup=ai_kbd,
    )


@router.callback_query(MainMenuOption.filter())
async def main_menu_handler(callback: types.CallbackQuery, callback_data: MainMenuOption):
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
            link = f"https://wa.me/79213713864?{urlencode({"text":
                                                               "Здравствуйте! Я хочу записаться на консультацию к Стайсупову Валерию Юрьевичу."})}"
            escaped_link = aiogram.html.link("ссылке", link)
            await callback.message.edit_text(
                f"Вы можете записаться на консультацию в WhatsApp по {escaped_link}\n\n"
                f""
                f"Или по телефону: +7-812-403-02-01",
                reply_markup=back_kbd,
            )
        case MainMenuBtns.SCHEDULE_SURGERY:
            link = f"https://wa.me/79213713864?{urlencode({"text": "Здравствуйте! Я хочу записаться на операцию к Стайсупову Валерию Юрьевичу."})}"
            escaped_link = aiogram.html.link("ссылке", link)
            await callback.message.edit_text(
                f"Вы можете записаться на операцию в WhatsApp по {escaped_link}\n\n"
                f""
                f"Или по телефону: +7-812-403-02-01",
                reply_markup=back_kbd,
            )


@router.callback_query(SurgeryMenuOption.filter())
async def analyze_list_handler(callback: types.CallbackQuery, callback_data: SurgeryMenuOption):
    match callback_data.action:
        case SurgeryMenuBtns.ANALYZE_LIST:
            fname = "data/Список Анализов.pdf"
            await callback.message.answer_document(FSInputFile(path=fname))
        case SurgeryMenuBtns.MEDICINE_AFTER:
            await callback.message.edit_text("Лекарства после операции", reply_markup=after_surgery_kbd)
        case SurgeryMenuBtns.BACK:
            await callback.message.edit_text(get_start_text(callback.from_user.full_name), reply_markup=start_kbd)


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
    callback: types.CallbackQuery, ai_client: AIClient, state: FSMContext, callback_data: AIMenuOption
):
    if callback_data.action == AIMenuBtns.BACK:
        await state.set_state()
        await callback.message.edit_text(get_start_text(callback.from_user.full_name), reply_markup=start_kbd)
        return

    data = await state.get_data()

    if "ai_thread_id" in data:
        try:
            await ai_client.delete_thread(data["ai_thread_id"])
        except openai.NotFoundError:
            logging.warning(f"Thread {data['ai_thread_id']} not found")

    new_thread_id = await ai_client.new_thread()
    await state.update_data(ai_thread_id=new_thread_id)
    await callback.message.answer("Чем я могу помочь?")


@router.message(StatesBot.IN_AI_DIALOG)
async def ai_leonardo_handler(message: types.Message, ai_client: AIClient, settings, state: FSMContext):
    data = await state.get_data()
    new_thread_id = data.get("ai_thread_id", None)
    if new_thread_id is None:
        new_thread_id = await ai_client.new_thread()
        await state.update_data(ai_thread_id=new_thread_id)

    await message.forward(settings.CHAT_LOG_ID)
    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        try:
            response = await ai_client.get_response(new_thread_id, message.text)
        except openai.NotFoundError:
            logging.warning(f"Thread {data['ai_thread_id']} not found")
            response = None
        if response is None:
            await message.answer("Извините, я отвлекся, давайте начнём новый разговор 🙈")
            return
        cleaned_response = refactor_string(response)
        msg_answer = await message.answer(cleaned_response, parse_mode=ParseMode.MARKDOWN_V2)
        await msg_answer.forward(settings.CHAT_LOG_ID)
