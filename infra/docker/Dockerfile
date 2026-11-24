# JourneyX API and Streamlit UI
FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/packages:/app/apps

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt README.md ./
COPY packages ./packages
COPY apps ./apps
COPY config ./config
COPY data ./data
COPY certs ./certs

RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .

RUN useradd -m -u 10001 journeyx
USER journeyx

EXPOSE 8000 8501