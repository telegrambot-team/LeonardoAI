FROM python:3.12-slim

RUN pip install uv

WORKDIR /app
COPY . /app

RUN uv pip install --system -Ue .
CMD ["bot-run"]
