# ┌─────────── Builder ───────────┐
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libopenblas-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install into a dedicated prefix
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ┌─────────── Runtime ───────────┐
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.11/site-packages"

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libgl1-mesa-glx libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# Create and use a non-root user
RUN useradd --create-home appuser
USER appuser
WORKDIR /home/appuser/app

# Copy installed Python packages from builder
COPY --from=builder /install /install

# Copy application code
COPY --chown=appuser:appuser . .

# Copy model weights if needed
COPY --chown=appuser:appuser weights/best_classes.onnx weights/

EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
