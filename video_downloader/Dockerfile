FROM python:3.12-slim


RUN apt-get update && \
    apt-get install -y ffmpeg curl unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV DENO_INSTALL="/root/.deno"
RUN curl -fsSL https://deno.land/install.sh | sh && \
    mv /root/.deno/bin/deno /usr/local/bin/deno && \
    rm -rf /root/.deno

ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1


RUN pip install --no-cache-dir poetry


WORKDIR /app


COPY pyproject.toml poetry.lock ./


RUN poetry install --no-root --only main

COPY . .

CMD exec gunicorn --bind :${PORT:-8080} --workers 1 --threads 8 --timeout 0 main:app
