[![CI](https://github.com/telegrambot-team/LeonardoAI/actions/workflows/ci.yml/badge.svg)](https://github.com/telegrambot-team/LeonardoAI/actions/workflows/ci.yml)
[![Coverage](https://telegrambot-team.github.io/LeonardoAI/coverage.svg)](https://telegrambot-team.github.io/LeonardoAI/)

Telegram assistant of a plastic surgeon powered by the OpenAI Responses API.

- Agent settings (prompt, model, reasoning effort, verbosity) are stored in SQLite and changed by the
  moderator via `/settings` in the bot.
- The knowledge base is an OpenAI vector store, configured with `VECTOR_STORE_IDS` in `.env`.
- User ↔ conversation links and the log chat mapping are stored in SQLite, Redis keeps only FSM state.

### Roles

- `ADMIN` gets start/stop notifications and short error reports.
- `MODERATOR` manages agent settings via `/settings` and answers users from the log chat.

### Local run

1. Install [uv](https://docs.astral.sh/uv/) and dependencies: `uv sync`
2. Copy `example.env` to `.env` and fill it in. Redis must be running.
3. Run the bot: `uv run bot-run`

Checks: `uv run ruff format src tests && uv run ruff check src tests && uv run pytest`

### Deploy

The bot runs on the server as a plain process inside tmux.

```bash
# 1. Only for the first deploy of this version: upload the initial prompt
scp Promt_v4.md contabo:~/projects/LeonardoAI/prompt.md

# 2. On the server
ssh contabo
cd ~/projects/LeonardoAI
# only for the first deploy of this version: add the knowledge base and the initial prompt
echo "VECTOR_STORE_IDS=<vector store id>" >> .env
echo "INITIAL_PROMPT_PATH=prompt.md" >> .env
uv self update   # the lock file needs a recent uv
git pull
uv sync

# 3. Restart the bot in tmux
tmux attach -t doctor     # then Ctrl+b 2 — the bot window
# Ctrl+C to stop the running bot, then:
uv run bot-run
# Ctrl+b d — detach, the bot keeps running
```

On the first start the bot creates `db/bot.db`, fills the settings from `.env` and `prompt.md`, and copies
conversation ids and the log chat mapping from Redis (Redis itself is not modified). After that `prompt.md`
and `INITIAL_PROMPT_PATH` are not used anymore: the prompt is changed via `/settings`.

Backup: copy `db/bot.db` (the only state besides Redis FSM).
