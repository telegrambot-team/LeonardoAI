from enum import IntEnum, StrEnum, auto

from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    WAITING_PROMPT = State()
    WAITING_MODEL = State()


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


class MainMenuBtns(IntEnum):
    # explicit value keeps buttons in already sent messages working
    SCHEDULE_CONSULTATION = 3


class SettingsAction(StrEnum):
    MAIN = "main"
    PROMPT = "prompt"
    PROMPT_DOWNLOAD = "prompt_dl"
    PROMPT_UPLOAD = "prompt_ul"
    MODEL = "model"
    EFFORT = "effort"
    SET_EFFORT = "set_effort"
    VERBOSITY = "verbosity"
    SET_VERBOSITY = "set_verb"
    CLEAR = "clear"
    CLEAR_CONFIRM = "clear_ok"
    CLOSE = "close"
