FROM python:3.11-slim
WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY main.py .
COPY service_account_creds.json .


CMD ["python3", "main.py"]