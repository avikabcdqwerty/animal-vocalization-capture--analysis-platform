# syntax=docker/dockerfile:1

# --- Stage 1: Build dependencies ---
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

# --- Stage 2: Install Python dependencies ---
FROM base as builder

COPY backend/app/requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && \
    pip install --prefix=/install -r /app/requirements.txt

# --- Stage 3: Final image ---
FROM base

# Copy installed python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY backend/app /app

# Expose FastAPI port
EXPOSE 8000

# Environment variables for production
ENV TZ=UTC
ENV LANG=C.UTF-8

# Create non-root user for security
RUN useradd -m appuser
USER appuser

# Entrypoint: run FastAPI app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- Exported: This Dockerfile builds the backend FastAPI API service ---