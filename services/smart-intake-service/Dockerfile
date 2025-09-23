FROM python:3.11-slim

WORKDIR /app

# System deps (if needed by some libs)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services/smart-intake-service/app:/app/packages/db/src:/app/packages/storage/src:/app/packages/ml/src:/app/packages/schemas/src:/app/packages/profiles/src:/app/packages/mq/src:/app/packages/common/src

# Copy local packages required to build/install MQ
COPY packages/common /app/packages/common
COPY packages/mq /app/packages/mq

# Install local packages (install common first, then MQ which depends on it)
RUN pip install --no-cache-dir /app/packages/common /app/packages/mq

# Copy requirements and install service dependencies
COPY services/smart-intake-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the smart-intake-service code
COPY services/smart-intake-service/app/ /app/services/smart-intake-service/app/

# Copy other packages needed for PYTHONPATH
COPY packages/db /app/packages/db
COPY packages/storage /app/packages/storage
COPY packages/ml /app/packages/ml
COPY packages/schemas /app/packages/schemas
COPY packages/profiles /app/packages/profiles

WORKDIR /app/services/smart-intake-service

EXPOSE 8003
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--log-level", "info"]