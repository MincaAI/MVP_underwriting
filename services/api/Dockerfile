FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOCKER_CONTAINER=true

RUN pip install --no-cache-dir poetry==1.8.3

# Copy the entire repo so Poetry can resolve local path dependencies
COPY . .

# Install the API and its path dependencies into the system environment (no venv)
WORKDIR /app/services/api
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi

# Verify the packages are installed correctly
RUN python -c "import app.db.session; print('Database package imported successfully')"
RUN python -c "import app.storage.s3; print('Storage package imported successfully')"
RUN python -c "import app.schemas; print('Schemas package imported successfully')"

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
