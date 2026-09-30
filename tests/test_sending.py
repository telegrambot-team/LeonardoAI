from bot.sending import split_text


def test_short_text_is_single_chunk():
    assert split_text("Привет\nмир") == ["Привет\nмир"]


def test_splits_on_line_boundaries():
    lines = [f"строка {i} " + "x" * 50 for i in range(200)]
    chunks = split_text("\n".join(lines), limit=1000)

    assert all(len(chunk) <= 1000 for chunk in chunks)
    assert "\n".join(chunks).splitlines() == lines


def test_splits_long_line_on_spaces():
    text = " ".join(["слово"] * 1000)
    chunks = split_text(text, limit=100)

    assert all(len(chunk) <= 100 for chunk in chunks)
    assert " ".join(chunks).split() == text.split()


def test_splits_line_without_spaces():
    chunks = split_text("x" * 250, limit=100)
    assert chunks == ["x" * 100, "x" * 100, "x" * 50]


def test_chars_label():
    from bot.settings_views import chars_label  # noqa: PLC0415

    assert [chars_label(n) for n in (1, 2, 5, 11, 21, 13223)] == [
        "1 символ",
        "2 символа",
        "5 символов",
        "11 символов",
        "21 символ",
        "13223 символа",
    ]
