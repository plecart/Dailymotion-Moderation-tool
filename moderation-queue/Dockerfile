# Moderation Queue API - standalone service (see docker-compose)
# Structure kept in sync with dailymotion-api-proxy/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos "" --uid 1000 app && chown -R app:app /app
USER app

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
