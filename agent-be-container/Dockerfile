# Stage 1: Build environment
FROM python:3.11-slim AS build

# Install poetry
RUN pip install poetry

WORKDIR /app

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY README.md ./

# Copy application source and migrations
COPY src ./src
COPY migrations ./migrations
COPY yoyo.ini ./yoyo.ini

# Create virtual environment
RUN python -m venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    POETRY_NO_INTERACTION=1

RUN poetry install --no-root --only main

# Build the project to generate the entrypoint script
RUN poetry install --only main

# Stage 2: Test environment
FROM build AS test

# Copy test files
COPY tests ./tests

# Install dev dependencies
RUN poetry install --no-interaction --no-ansi --with dev

# Run tests and create success flag
ENV PYTHONPATH=src
RUN --mount=type=secret,id=GOOGLE_API_KEY \
    GAK=$(cat /run/secrets/GOOGLE_API_KEY) && \
    export APP_MAIN_AICLIENT__GOOGLE_API_KEY=$GAK && \
    export APP_PACKAGER_AICLIENT__GOOGLE_API_KEY=$GAK && \
    export GOOGLE_API_KEY=$GAK && \
    poetry run pytest && touch /app/tests/.test_success

# Stage 3: Final image
FROM python:3.11-slim

# Add OCI labels
LABEL org.opencontainers.image.title="Agent Backend"
LABEL org.opencontainers.image.description="AI Agent Backend with LangGraph"
LABEL org.opencontainers.image.authors="Ben Greene <BenJGreene@gmail.com>"
LABEL org.opencontainers.image.source="https://github.com/polecatworks/Angry-agent"
LABEL org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

WORKDIR /app

# Expose required port
EXPOSE 8080 8079

# Copy test success flag, venv, and source code from previous stages
COPY --from=test /app/tests/.test_success /app/tests/.test_success
COPY --from=build /opt/venv /opt/venv
COPY --from=build /app/src ./src
COPY --from=build /app/migrations ./migrations
COPY --from=build /app/yoyo.ini ./yoyo.ini

# Setup environment variables
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app/src

# Command to run the application via CLI
ENTRYPOINT ["agent-be"]
CMD ["--help"]
