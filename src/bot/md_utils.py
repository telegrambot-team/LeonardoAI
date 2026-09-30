import re

# File search citations left by the model in the answer text:
# - old format: 【4:0†DOCTOR_INFO.md】
# - new format: \ue200filecite\ue202turn8file0\ue202turn8file2\ue201 (private use characters
#   U+E200 start, U+E202 separator, U+E201 end); the end mark may be lost if the answer is cut off
CITATION_PATTERN = re.compile("[ \t]*(?:【[^】\n]*】|\ue200[^\ue201\n]*(?:\ue201|$))", re.MULTILINE)
# Private use characters have no standard glyph, Telegram clients render them as random icons
PRIVATE_USE_PATTERN = re.compile("[\ue000-\uf8ff]")


def clean(response: str) -> str:
    return PRIVATE_USE_PATTERN.sub("", CITATION_PATTERN.sub("", response))


def escape_markdown_v2(text: str) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    pattern = rf"([{re.escape(escape_chars)}])"
    return re.sub(pattern, r"\\\1", text)


def escape_stars(s):
    process = s.split("**")
    return "*".join([escape_markdown_v2(i) for i in process])


def starts_with_hash_space(s: str) -> bool:
    pattern = r"^#+\s"
    return bool(re.match(pattern, s))


def refactor_string(string: str) -> str:
    lines = clean(string).splitlines()
    indices_to_wrap = []

    for i, line in enumerate(lines):
        if starts_with_hash_space(line):
            lines[i] = re.sub(r"^#+\s", "", line)
            indices_to_wrap.append(i)
        lines[i] = escape_stars(lines[i])

    for i in indices_to_wrap:
        lines[i] = f"*{lines[i]}*"

    return "\n".join(lines)
