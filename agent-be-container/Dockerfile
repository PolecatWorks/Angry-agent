FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY README.md ./
COPY src ./src

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Expose port
EXPOSE 8000

# Command
CMD ["python", "src/main.py"]
