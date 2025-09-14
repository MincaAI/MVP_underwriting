FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services/document-processor/src:/app/packages/db/src:/app/packages/storage/src:/app/packages/ml/src:/app/packages/schemas/src:/app/packages/profiles/src

RUN pip install --no-cache-dir poetry==1.8.3
COPY . .
WORKDIR /app/services/document-processor
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root

EXPOSE 8001
# Run the simplified local runner which matches the current DB schema
CMD ["poetry", "run", "python", "/app/services/document-processor/run_local.py"]
