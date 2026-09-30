from aiogram.types import Chat, Message, Update, User

from bot.handlers import errors_handler
from bot.handlers.errors_handler import _should_report, format_error_report


def _update() -> Update:
    user = User(id=42, is_bot=False, first_name="Test")
    message = Message(message_id=1, date=0, chat=Chat(id=42, type="private"), from_user=user, text="hi")
    return Update(update_id=1, message=message)


def test_report_is_short_and_escaped():
    report = format_error_report(ValueError("<bad> " + "x" * 1000), _update())

    assert "ValueError" in report
    assert "&lt;bad&gt;" in report
    assert "message, user 42" in report
    assert "Traceback" not in report
    assert len(report) < 700


def test_same_error_is_reported_once(monkeypatch):
    monkeypatch.setattr(errors_handler, "_last_reported", {})

    assert _should_report(RuntimeError("boom"))
    assert not _should_report(RuntimeError("boom"))
    assert _should_report(RuntimeError("other"))
