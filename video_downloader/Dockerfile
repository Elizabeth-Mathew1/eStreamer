FROM python:3.12-slim


RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1


RUN pip install --no-cache-dir poetry


WORKDIR /app


COPY pyproject.toml poetry.lock ./


RUN poetry install --no-root --only main

COPY . .

CMD exec gunicorn --bind :$PORT --workers 1 main:app
