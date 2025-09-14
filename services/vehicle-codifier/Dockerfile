FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services/vehicle-codifier/src:/app/packages/db/src:/app/packages/storage/src:/app/packages/ml/src:/app/packages/schemas/src:/app/packages/profiles/src

RUN pip install --no-cache-dir poetry==1.8.3
COPY . .
WORKDIR /app/services/vehicle-codifier
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root

EXPOSE 8002
CMD ["uvicorn", "vehicle_codifier.main:app", "--host", "0.0.0.0", "--port", "8002", "--log-level", "info"]