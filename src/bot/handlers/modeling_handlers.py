from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import CallbackQuery, FSInputFile, LabeledPrice, Message, PreCheckoutQuery

from bot.internal.controllers import admin_reply_dispatch
from bot.internal.enums import ModelMenuBtns, PhotoMenuBtns
from bot.internal.lexicon import texts
from bot.keyboards import (
    ModelMenuOption,
    UploadPhotoOption,
    get_details_kb,
    get_keep_rejected_photo_buttons,
    get_photo_buttons,
    get_rejected_photo_buttons,
    get_requirements_kb,
)
from config import Settings

router = Router()
image_types = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "image/tiff"}


@router.callback_query(ModelMenuOption.filter())
async def model_menu_handler(
    callback: CallbackQuery, callback_data: ModelMenuOption, settings: Settings, state: FSMContext
):
    await callback.answer()
    match callback_data.action:
        case ModelMenuBtns.UPLOAD_PHOTO:
            await callback.message.answer(texts["upload_photo"])
        case ModelMenuBtns.UPLOAD_NEW_PHOTO:
            await callback.message.answer(texts["payment_success"])
        case ModelMenuBtns.KEEP_PHOTO:
            await callback.message.answer(text=texts["keep_photo"], reply_markup=get_keep_rejected_photo_buttons())
        case ModelMenuBtns.CONFIRM_KEEP_PHOTO:
            data = await state.get_data()
            doc_id = data.get("last_document")
            if not doc_id:
                await callback.answer(
                    "Не найдено последнее загруженное фото-файл. Загрузите документ заново.", show_alert=True
                )
                return
            await callback.message.answer(texts["patient_keep_photo"])
            await callback.message.bot.send_document(
                chat_id=settings.CHAT_LOG_ID,
                document=doc_id,
                caption=f"uid:{callback.from_user.id}\n\n{texts['confirm_keep_photo']}",
            )
        case ModelMenuBtns.PHOTO_REQUIREMENTS:
            await callback.message.answer(texts["photo_requirements"], reply_markup=get_requirements_kb())
        case ModelMenuBtns.DETAILS:
            await callback.message.answer(texts["modeling_message"], reply_markup=get_details_kb())


@router.callback_query(UploadPhotoOption.filter())
async def photo_upload_handler(callback: CallbackQuery, callback_data: UploadPhotoOption, state: FSMContext):
    await callback.answer()
    match callback_data.action:
        case PhotoMenuBtns.ACCEPT:
            await callback.message.bot.send_message(callback_data.chat_id, texts["photo_uploaded"])
            key = StorageKey(
                bot_id=callback.message.bot.id, chat_id=callback_data.chat_id, user_id=callback_data.chat_id
            )
            client_state = FSMContext(storage=state.storage, key=key)
            await client_state.update_data(paid=False)
            await callback.message.reply(texts["admin_accept_photo"])
        case PhotoMenuBtns.DECLINE:
            await callback.message.bot.send_message(
                callback_data.chat_id, texts["photo_rejected"], reply_markup=get_rejected_photo_buttons()
            )
            await callback.message.reply(texts["admin_deny_photo"])


@router.callback_query(F.data == "payment")
async def model_payment_handler(callback: CallbackQuery, settings: Settings):
    await callback.answer()
    amount = 3000 * 100
    prices = [LabeledPrice(label="Оплатить", amount=amount)]
    await callback.message.answer_invoice(
        title="Услуга моделирования.",
        description=texts["payment_description"],
        payload="model",
        provider_token=settings.PAYMENT_PROVIDER_TOKEN.get_secret_value(),
        currency="RUB",
        prices=prices,
    )


@router.pre_checkout_query()
async def on_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, state: FSMContext):
    await state.update_data(paid=True)
    await message.answer(texts["payment_success"])


@router.message(F.photo)
async def on_photo(message: Message, state: FSMContext, settings: Settings):
    if message.from_user.id == settings.MODERATOR:
        await admin_reply_dispatch(message, settings)
        return

    data = await state.get_data()
    if not data.get("paid", False):
        return
    await message.answer_photo(
        photo=FSInputFile(str(Path(__file__).resolve().parents[1] / "internal" / "upload_screenshot.jpg")),
        caption=texts["photo_low_quality"],
    )


@router.message(F.text)
async def admin_text_reply(message: Message, settings: Settings):
    await admin_reply_dispatch(message, settings)


@router.message(F.document)
async def on_document(message: Message, state: FSMContext, settings: Settings):
    if message.from_user.id == settings.MODERATOR:
        await admin_reply_dispatch(message, settings)
        return

    doc = message.document
    if not doc or (doc.mime_type not in image_types):
        return

    data = await state.get_data()
    if not data.get("paid", False):
        return

    user_caption = message.caption or ""
    await message.bot.send_document(
        chat_id=settings.CHAT_LOG_ID,
        document=doc.file_id,
        caption=f"uid:{message.from_user.id}\n\n{user_caption}",
        reply_markup=get_photo_buttons(chat_id=message.chat.id),
    )
    await state.update_data(last_document=doc.file_id)
    await message.answer(texts["photo_sent"])
