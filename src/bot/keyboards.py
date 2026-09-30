from aiogram.enums import ButtonStyle
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.internal.enums import AfterSurgeryMenuBtns, MainMenuBtns, SettingsAction, SurgeryMenuBtns
from schemas import AgentSettings, ReasoningEffort, Verbosity


class MainMenuOption(CallbackData, prefix="main_menu"):
    action: MainMenuBtns


class SurgeryMenuOption(CallbackData, prefix="surgery_menu"):
    action: SurgeryMenuBtns


class AfterSurgeryMenuOption(CallbackData, prefix="after_surgery_menu"):
    action: AfterSurgeryMenuBtns


class SettingsOption(CallbackData, prefix="st"):
    action: SettingsAction
    value: str = ""


def _build_start_kbd():
    kb = InlineKeyboardBuilder()
    kb.button(text="Услуга моделирования", url="https://t.me/model_nosa_bot")
    kb.button(text="Анализы перед операцией", callback_data=SurgeryMenuOption(action=SurgeryMenuBtns.ANALYZE_LIST))
    kb.button(text="Лекарства после операции", callback_data=SurgeryMenuOption(action=SurgeryMenuBtns.MEDICINE_AFTER))
    kb.button(text="Записаться к доктору", callback_data=MainMenuOption(action=MainMenuBtns.SCHEDULE_CONSULTATION))
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


def _back_to_start_kbd():
    kb = InlineKeyboardBuilder()
    kb.button(text="Назад", callback_data=SurgeryMenuOption(action=SurgeryMenuBtns.BACK))
    return kb.as_markup()


start_kbd = _build_start_kbd()
after_surgery_kbd = _after_surgery_kbd()
back_to_start_kbd = _back_to_start_kbd()


def _settings_button(
    kb: InlineKeyboardBuilder, text: str, action: SettingsAction, value: str = "", style: ButtonStyle | None = None
) -> None:
    kb.button(text=text, callback_data=SettingsOption(action=action, value=value), style=style)


def _back_button(kb: InlineKeyboardBuilder, text: str = "⬅️ Назад") -> None:
    _settings_button(kb, text, SettingsAction.MAIN)


def settings_main_kbd(settings: AgentSettings) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _settings_button(kb, "📝 Промпт", SettingsAction.PROMPT, style=ButtonStyle.PRIMARY)
    _settings_button(kb, "🤖 Модель", SettingsAction.MODEL, style=ButtonStyle.PRIMARY)
    if settings.supported_efforts:
        _settings_button(kb, "🧠 Reasoning effort", SettingsAction.EFFORT, style=ButtonStyle.PRIMARY)
    _settings_button(kb, "💬 Verbosity", SettingsAction.VERBOSITY, style=ButtonStyle.PRIMARY)
    _settings_button(kb, "🗑 Очистить все диалоги", SettingsAction.CLEAR, style=ButtonStyle.DANGER)
    _settings_button(kb, "✖️ Закрыть", SettingsAction.CLOSE)
    kb.adjust(2, 2 if settings.supported_efforts else 1, 1, 1)
    return kb.as_markup()


def settings_prompt_kbd() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _settings_button(kb, "📥 Скачать текущий", SettingsAction.PROMPT_DOWNLOAD, style=ButtonStyle.PRIMARY)
    _settings_button(kb, "📤 Загрузить новый", SettingsAction.PROMPT_UPLOAD, style=ButtonStyle.SUCCESS)
    _back_button(kb)
    kb.adjust(2, 1)
    return kb.as_markup()


def settings_cancel_kbd(back_to: SettingsAction = SettingsAction.MAIN) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _settings_button(kb, "⬅️ Отмена", back_to)
    return kb.as_markup()


def settings_back_kbd() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _back_button(kb)
    return kb.as_markup()


def settings_effort_kbd(settings: AgentSettings) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for effort in ReasoningEffort:
        if effort not in settings.supported_efforts:
            continue
        is_current = effort == settings.reasoning_effort
        text = f"✅ {effort}" if is_current else str(effort)
        style = ButtonStyle.SUCCESS if is_current else None
        _settings_button(kb, text, SettingsAction.SET_EFFORT, value=effort, style=style)
    _back_button(kb)
    kb.adjust(len(settings.supported_efforts), 1)
    return kb.as_markup()


def settings_verbosity_kbd(settings: AgentSettings) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for verbosity in Verbosity:
        is_current = verbosity == settings.verbosity
        text = f"✅ {verbosity}" if is_current else str(verbosity)
        style = ButtonStyle.SUCCESS if is_current else None
        _settings_button(kb, text, SettingsAction.SET_VERBOSITY, value=verbosity, style=style)
    _back_button(kb)
    kb.adjust(len(Verbosity), 1)
    return kb.as_markup()


def settings_clear_kbd() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _settings_button(kb, "🗑 Да, очистить", SettingsAction.CLEAR_CONFIRM, style=ButtonStyle.DANGER)
    _back_button(kb, "⬅️ Отмена")
    kb.adjust(1)
    return kb.as_markup()
