FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock .env ./

RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true

RUN poetry install --no-interaction --no-ansi --no-root

COPY server/ .

ENV PORT=8080

CMD ["/app/.venv/bin/gunicorn", "--bind", ":8080", "--workers", "1", "main:app"]
