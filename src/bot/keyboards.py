from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.internal.enums import AfterSurgeryMenuBtns, AIMenuBtns, MainMenuBtns, ModeratorMenuBtns, SurgeryMenuBtns


class MainMenuOption(CallbackData, prefix="main_menu"):
    action: MainMenuBtns


class SurgeryMenuOption(CallbackData, prefix="surgery_menu"):
    action: SurgeryMenuBtns


class AfterSurgeryMenuOption(CallbackData, prefix="after_surgery_menu"):
    action: AfterSurgeryMenuBtns


class AIMenuOption(CallbackData, prefix="ai_menu"):
    action: AIMenuBtns


class ModeratorMenuOption(CallbackData, prefix="moderator_menu"):
    action: ModeratorMenuBtns


def _build_start_kbd(*, is_moderator: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="Услуга моделирования", url="https://t.me/model_nosa_bot")
    kb.button(text="Анализы перед операцией", callback_data=SurgeryMenuOption(action=SurgeryMenuBtns.ANALYZE_LIST))
    kb.button(text="Лекарства после операции", callback_data=SurgeryMenuOption(action=SurgeryMenuBtns.MEDICINE_AFTER))
    kb.button(text="Записаться к доктору", callback_data=MainMenuOption(action=MainMenuBtns.SCHEDULE_CONSULTATION))
    kb.adjust(1)
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
