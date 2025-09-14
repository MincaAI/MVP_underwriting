FROM python:3.11-slim

# Install Poetry
RUN pip install poetry

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy Poetry configuration
COPY pyproject.toml poetry.lock* ./
COPY packages/ ./packages/
COPY services/worker-transform/pyproject.toml ./services/worker-transform/

# Install dependencies
RUN cd services/worker-transform && poetry install --only=main && rm -rf $POETRY_CACHE_DIR

# Copy service code
COPY services/worker-transform/src/ ./services/worker-transform/src/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/services/worker-transform
CMD ["poetry", "run", "python", "-m", "worker_transform.main"]