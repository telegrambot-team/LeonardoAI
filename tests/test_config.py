from config import Settings

REQUIRED = {
    "BOT_TOKEN": "1:x",
    "ADMIN": "1",
    "MODERATOR": "2",
    "OPENAI_API_KEY": "sk",
    "CHAT_LOG_ID": "-100",
    "VECTOR_STORE_IDS": "vs_test",
}


def test_vector_store_ids_from_comma_separated_env(monkeypatch):
    for key, value in {**REQUIRED, "VECTOR_STORE_IDS": "vs_1, vs_2,", "ASSISTANT_ID": "asst_old"}.items():
        monkeypatch.setenv(key, value)

    settings = Settings(_env_file=None)

    assert settings.VECTOR_STORE_IDS == ("vs_1", "vs_2")


def test_defaults(monkeypatch):
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)

    settings = Settings(_env_file=None)

    assert settings.VECTOR_STORE_IDS == ("vs_test",)
    assert settings.DEFAULT_MODEL == "gpt-6-luna"
    assert settings.DEFAULT_EFFORT == "medium"
