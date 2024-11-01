from urllib.parse import urlencode

import aiogram.utils.formatting
from aiogram import Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.chat_action import ChatActionSender

from ai_client import AIClient
from bot.handlers.consts import TEXTS, IMGS
from bot.keyboards import (
    start_kbd,
    MainMenuOption,
    MainMenuBtns,
    before_surgery_kbd,
    SurgeryMenuOption,
    SurgeryMenuBtns,
    after_surgery_kbd,
    AfterSurgeryMenuOption,
    AfterSurgeryMenuBtns,
    ai_kbd,
    AIMenuOption,
    AIMenuBtns,
)
from database.models import User

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
async def ai_leonardo_handler(callback: types.CallbackQuery, state: FSMContext):
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
async def analyze_list_handler(callback: types.CallbackQuery, callback_data: AfterSurgeryMenuOption):
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
async def analyze_list_handler(
    callback: types.CallbackQuery, user: User, ai_client: AIClient, state: FSMContext, callback_data: AIMenuOption
):
    if callback_data.action == AIMenuBtns.BACK:
        await state.set_state()
        await callback.message.edit_text(get_start_text(callback.from_user.full_name), reply_markup=start_kbd)
        return
    if user.ai_thread_id is not None:
        await ai_client.delete_thread(user.ai_thread_id)

    user.ai_thread_id = await ai_client.new_thread()
    await callback.message.answer("Чем я могу помочь?")


@router.message(StatesBot.IN_AI_DIALOG)
async def ai_leonardo_handler(message: types.Message, user: User, ai_client: AIClient, settings):
    if user.ai_thread_id is None:
        user.ai_thread_id = await ai_client.new_thread()

    await message.forward(settings.CHAT_LOG_ID)
    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        response = await ai_client.get_response(user.ai_thread_id, message.text)
        if response is None:
            await message.answer("Извините, я не могу ответить на ваш вопрос")
            return
        msg_answer = await message.answer(response)
        await msg_answer.forward(settings.CHAT_LOG_ID)
