[![CI](https://github.com/telegrambot-team/LeonardoAI/actions/workflows/ci.yml/badge.svg)](https://github.com/telegrambot-team/LeonardoAI/actions/workflows/ci.yml)
[![Coverage](https://telegrambot-team.github.io/LeonardoAI/coverage.svg)](https://telegrambot-team.github.io/LeonardoAI/)

### Setup project

1. Create env:

```
python -m venv venv
source venv/bin/activate
```

2. Install dependencies

```
pip install -Ue .
```

3. Create `.env` file and fill it with needed variables. You can copy it from `example.env`

4. Run postgres database. You can use `docker-compose.yml` in the repo root.

```
docker compose up -d
```

### Run bot

```
bot-run
```
