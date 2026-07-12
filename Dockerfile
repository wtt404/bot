FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium && \
    rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "-u", "main.py"]
