from enum import IntEnum, auto


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


class ModelMenuBtns(IntEnum):
    UPLOAD_PHOTO = auto()
    UPLOAD_NEW_PHOTO = auto()
    KEEP_PHOTO = auto()
    CONFIRM_KEEP_PHOTO = auto()
    PHOTO_REQUIREMENTS = auto()
    DETAILS = auto()


class PhotoMenuBtns(IntEnum):
    ACCEPT = auto()
    DECLINE = auto()


class MainMenuBtns(IntEnum):
    AI_LEONARDO = auto()
    MODELLING = auto()
    BEFORE_SURGERY = auto()
    ASK_QUESTION = auto()
    SCHEDULE_CONSULTATION = auto()
    SCHEDULE_SURGERY = auto()


class ModeratorMenuBtns(IntEnum):
    CLEAR_CONTEXTS = auto()
