FROM python:3.12-slim

WORKDIR /app


RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --only main

COPY . .

ENV PORT 8080


CMD exec gunicorn --bind :$PORT --workers 1 main:app
