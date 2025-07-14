from enum import IntEnum, auto

from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder


class MainMenuBtns(IntEnum):
    AI_LEONARDO = auto()
    BEFORE_SURGERY = auto()
    ASK_QUESTION = auto()
    SCHEDULE_CONSULTATION = auto()
    SCHEDULE_SURGERY = auto()


class MainMenuOption(CallbackData, prefix="main_menu"):
    action: MainMenuBtns


class SurgeryMenuBtns(IntEnum):
    ANALYZE_LIST = auto()
    MEDICINE_AFTER = auto()
    BACK = auto()


class AfterSurgeryMenuBtns(IntEnum):
    RINOPLASTIC = auto()
    MAMMOPLASTIC = auto()
    RENEW = auto()
    LIPOSACTION = auto()
    BACK = auto()


class AIMenuBtns(IntEnum):
    NEW_DIALOG = auto()
    BACK = auto()


class SurgeryMenuOption(CallbackData, prefix="surgery_menu"):
    action: SurgeryMenuBtns


class AfterSurgeryMenuOption(CallbackData, prefix="after_surgery_menu"):
    action: AfterSurgeryMenuBtns


class AIMenuOption(CallbackData, prefix="ai_menu"):
    action: AIMenuBtns


class AdminMenuBtns(IntEnum):
    CLEAR_CONTEXTS = auto()


class AdminMenuOption(CallbackData, prefix="admin_menu"):
    action: AdminMenuBtns


def _build_start_kbd(*, is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="Разговор с моей цифровой копией", callback_data=MainMenuOption(action=MainMenuBtns.AI_LEONARDO))
    kb.button(text="Перед операцией", callback_data=MainMenuOption(action=MainMenuBtns.BEFORE_SURGERY))
    kb.button(text="Задать вопрос доктору", callback_data=MainMenuOption(action=MainMenuBtns.ASK_QUESTION))
    kb.button(
        text="Записаться на консультацию", callback_data=MainMenuOption(action=MainMenuBtns.SCHEDULE_CONSULTATION)
    )
    kb.button(text="Записаться на операцию", callback_data=MainMenuOption(action=MainMenuBtns.SCHEDULE_SURGERY))
    kb.adjust(1, 2, 2)
    if is_admin:
        kb.button(text="Очистить контекст", callback_data=AdminMenuOption(action=AdminMenuBtns.CLEAR_CONTEXTS))
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
start_admin_kbd = _build_start_kbd(is_admin=True)
before_surgery_kbd = _before_surgery_kbd()
after_surgery_kbd = _after_surgery_kbd()
ai_kbd = _ai_kbd()
