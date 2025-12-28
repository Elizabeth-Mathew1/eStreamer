FROM python:3.11-slim

WORKDIR /app
# Install ffmpeg and yt-dlp dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*



WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY main.py .
COPY service_account_creds.json .

ENV PORT=8080


CMD ["python3", "main.py"]