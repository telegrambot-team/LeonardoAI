from enum import IntEnum, auto

from aiogram.fsm.state import State, StatesGroup


class StatesBot(StatesGroup):
    IN_AI_DIALOG = State()


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


class MainMenuBtns(IntEnum):
    MODELLING = auto()
    BEFORE_SURGERY = auto()
    SCHEDULE_CONSULTATION = auto()


class ModeratorMenuBtns(IntEnum):
    CLEAR_CONTEXTS = auto()
