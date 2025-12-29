FROM python:3.11-slim


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



WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY main.py .
COPY service_account_creds.json .

ENV PORT=8080


CMD ["python3", "main.py"]
