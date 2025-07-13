from bot.md_utils import escape_markdown_v2, escape_stars, refactor_string, starts_with_hash_space


def test_escape_markdown_v2():
    text = r"*_[]()~`>#+-=|{}.!"
    escaped = escape_markdown_v2(text)
    expected = "".join(f"\\{ch}" for ch in text)
    assert escaped == expected


def test_escape_stars():
    assert escape_stars("a**b*c") == "a*b\\*c"


def test_starts_with_hash_space():
    assert starts_with_hash_space("# heading") is True
    assert starts_with_hash_space("## heading") is True
    assert starts_with_hash_space("no heading") is False


def test_refactor_string():
    src = """# Заголовок\nТекст **bold**"""
    res = refactor_string(src)
    assert res == "*Заголовок*\nТекст *bold*"
