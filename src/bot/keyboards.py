from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.internal.enums import (
    AfterSurgeryMenuBtns,
    AIMenuBtns,
    MainMenuBtns,
    ModelMenuBtns,
    ModeratorMenuBtns,
    PhotoMenuBtns,
    SurgeryMenuBtns,
)


class MainMenuOption(CallbackData, prefix="main_menu"):
    action: MainMenuBtns


class SurgeryMenuOption(CallbackData, prefix="surgery_menu"):
    action: SurgeryMenuBtns


class AfterSurgeryMenuOption(CallbackData, prefix="after_surgery_menu"):
    action: AfterSurgeryMenuBtns


class AIMenuOption(CallbackData, prefix="ai_menu"):
    action: AIMenuBtns


class ModelMenuOption(CallbackData, prefix="model_menu"):
    action: ModelMenuBtns


class UploadPhotoOption(CallbackData, prefix="photo_menu"):
    action: PhotoMenuBtns
    chat_id: int


class ModeratorMenuOption(CallbackData, prefix="moderator_menu"):
    action: ModeratorMenuBtns


def _build_start_kbd(*, is_moderator: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="Разговор с моей цифровой копией", callback_data=MainMenuOption(action=MainMenuBtns.AI_LEONARDO))
    kb.button(text="Услуга моделирования", callback_data=MainMenuOption(action=MainMenuBtns.MODELLING))
    kb.button(text="Перед операцией", callback_data=MainMenuOption(action=MainMenuBtns.BEFORE_SURGERY))
    kb.button(text="Задать вопрос доктору", callback_data=MainMenuOption(action=MainMenuBtns.ASK_QUESTION))
    kb.button(
        text="Записаться на консультацию", callback_data=MainMenuOption(action=MainMenuBtns.SCHEDULE_CONSULTATION)
    )
    kb.button(text="Записаться на операцию", callback_data=MainMenuOption(action=MainMenuBtns.SCHEDULE_SURGERY))
    kb.adjust(1, 2, 2)
    if is_moderator:
        kb.button(text="Очистить контекст", callback_data=ModeratorMenuOption(action=ModeratorMenuBtns.CLEAR_CONTEXTS))
        kb.adjust(1)
    return kb.as_markup()


def _before_surgery_kbd():
    kb = InlineKeyboardBuilder()
    kb.button(text="Список анализов", callback_data=SurgeryMenuOption(action=SurgeryMenuBtns.ANALYZE_LIST))
    kb.button(text="Лекарства после операции", callback_data=SurgeryMenuOption(action=SurgeryMenuBtns.MEDICINE_AFTER))
    kb.button(text="Назад", callback_data=SurgeryMenuOption(action=SurgeryMenuBtns.BACK))
    kb.adjust(1)
    return kb.as_markup()


def _after_surgery_kbd():
    kb = InlineKeyboardBuilder()
    kb.button(text="Ринопластика", callback_data=AfterSurgeryMenuOption(action=AfterSurgeryMenuBtns.RINOPLASTIC))
    kb.button(text="Маммопластика", callback_data=AfterSurgeryMenuOption(action=AfterSurgeryMenuBtns.MAMMOPLASTIC))
    kb.button(text="Омолаживающие операции", callback_data=AfterSurgeryMenuOption(action=AfterSurgeryMenuBtns.RENEW))
    kb.button(text="Липосакция", callback_data=AfterSurgeryMenuOption(action=AfterSurgeryMenuBtns.LIPOSACTION))
    kb.button(text="Назад", callback_data=AfterSurgeryMenuOption(action=AfterSurgeryMenuBtns.BACK))
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def _ai_kbd():
    kb = InlineKeyboardBuilder()
    kb.button(text="Начать новый разговор", callback_data=AIMenuOption(action=AIMenuBtns.NEW_DIALOG))
    kb.button(text="В главное меню", callback_data=AIMenuOption(action=AIMenuBtns.BACK))
    kb.adjust(1)
    return kb.as_markup()


start_kbd = _build_start_kbd()
start_moderator_kbd = _build_start_kbd(is_moderator=True)
before_surgery_kbd = _before_surgery_kbd()
after_surgery_kbd = _after_surgery_kbd()
ai_kbd = _ai_kbd()


def get_model_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Стоимость и сроки", callback_data=ModelMenuOption(action=ModelMenuBtns.DETAILS))
    kb.button(text="📋 Требования к фото", callback_data=ModelMenuOption(action=ModelMenuBtns.PHOTO_REQUIREMENTS))
    kb.button(text="📝 Часто задаваемые вопросы", url="https://staisupov.ru/mod#rec1237052556")
    kb.button(text="Перейти к  оплате", callback_data="payment")
    kb.adjust(1)
    return kb.as_markup()


def get_requirements_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Стоимость и сроки", callback_data=ModelMenuOption(action=ModelMenuBtns.DETAILS))
    kb.button(text="📝 Часто задаваемые вопросы", url="https://staisupov.ru/mod#rec1237052556")
    kb.button(text="Перейти к  оплате", callback_data="payment")
    kb.adjust(1)
    return kb.as_markup()


def get_details_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Требования к фото", callback_data=ModelMenuOption(action=ModelMenuBtns.PHOTO_REQUIREMENTS))
    kb.button(text="📝 Часто задаваемые вопросы", url="https://staisupov.ru/mod#rec1237052556")
    kb.button(text="Перейти к  оплате", callback_data="payment")
    kb.adjust(1)
    return kb.as_markup()


def get_payment_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить", callback_data="payment")
    return kb.as_markup()


def get_photo_buttons(chat_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅", callback_data=UploadPhotoOption(action=PhotoMenuBtns.ACCEPT, chat_id=chat_id))
    kb.button(text="❌", callback_data=UploadPhotoOption(action=PhotoMenuBtns.DECLINE, chat_id=chat_id))
    return kb.as_markup()


def get_rejected_photo_buttons():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Требования к фото", callback_data=ModelMenuOption(action=ModelMenuBtns.PHOTO_REQUIREMENTS))
    kb.button(text="Оставить прежнее фото", callback_data=ModelMenuOption(action=ModelMenuBtns.KEEP_PHOTO))
    kb.adjust(1)
    return kb.as_markup()


def get_keep_rejected_photo_buttons():
    kb = InlineKeyboardBuilder()
    kb.button(text="Оставить прежнее фото", callback_data=ModelMenuOption(action=ModelMenuBtns.CONFIRM_KEEP_PHOTO))
    kb.button(text="📋 Требования к фото", callback_data=ModelMenuOption(action=ModelMenuBtns.PHOTO_REQUIREMENTS))
    kb.button(text="Загрузить новое фото", callback_data=ModelMenuOption(action=ModelMenuBtns.UPLOAD_NEW_PHOTO))
    kb.adjust(1)
    return kb.as_markup()
