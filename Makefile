.PHONY: all build-fe build-be build-rs-be helm-package helm-deploy test tests venvs \
        compose-db compose-db-up compose-db-down compose-db-clean db-local \
        garden-up garden-test garden-down

BASE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

HELM_CHART := agent-be
HELM_DIR := charts/$(HELM_CHART)

RUST_APPS := agent-be
PYTHON_APPS := agentpy-be
NODE_APPS := agent-ui
APPS := $(PYTHON_APPS) $(NODE_APPS) $(RUST_APPS)

agent-be_PORT := 8080
agent-be_HEALTH_PORT := 8079
agentpy-be_PORT := 8080
agentpy-be_HEALTH_PORT := 8079
agent-ui_PORT := 3001

agent-be_INTERNAL_PORT := 8080
agent-be_INTERNAL_HEALTH_PORT := 8079
agentpy-be_INTERNAL_PORT := 8080
agentpy-be_INTERNAL_HEALTH_PORT := 8079
agent-ui_INTERNAL_PORT := 8080

# Docker Build
agent-be_DOCKER_BUILD_OPTS :=
agentpy-be_DOCKER_BUILD_OPTS := --secret id=GOOGLE_API_KEY,env=GOOGLE_API_KEY
agent-ui_DOCKER_BUILD_OPTS := --secret id=NODE_AUTH_TOKEN,env=NODE_AUTH_TOKEN

export APP_MAIN_AICLIENT__GOOGLE_API_KEY := ${GOOGLE_API_KEY}
export APP_PACKAGER_AICLIENT__GOOGLE_API_KEY := ${GOOGLE_API_KEY}
export APP_EMBEDDING_CLIENT__GOOGLE_API_KEY := ${GOOGLE_API_KEY}

# Top-level aggregate and alias commands
all: build-fe build-be helm-package

test:
	@echo "Running tests for all components..."
	$(MAKE) tests

build-fe: agent-ui-docker
build-be: agent-be-docker
build-py-be: agentpy-be-docker

helm-package:
	helm package $(HELM_DIR) -d charts

helm-deploy:
	helm upgrade --install $(HELM_CHART) $(HELM_DIR)

# --- Python Venvs & Deps ---

# Pattern to create venvs and install deps for any app in PYTHON_APPS
# Expects a folder name: <app>-container
$(foreach app,$(PYTHON_APPS),$(app)-venv/bin/activate):%-venv/bin/activate:%-container/pyproject.toml
	@echo Creating venv for $*
	python3 -m venv $*-venv
	$*-venv/bin/pip install --upgrade pip
	$*-venv/bin/pip install poetry
	cd $*-container && \
	. ../$*-venv/bin/activate && \
	poetry install --with dev

# Ensure pytest is available (installed via dev deps above)
$(foreach app,$(PYTHON_APPS),$(app)-venv/bin/pytest): %-venv/bin/pytest: %-venv/bin/activate
	@touch $@

# Ensure adev is available (installed via dev deps above)
$(foreach app,$(PYTHON_APPS),$(app)-venv/bin/adev):%-venv/bin/adev: %-venv/bin/activate
	@echo creating development tools for $*
	@# Dependencies are installed in the activate target
	@touch $@

# Run development server (Python)
$(foreach app,$(PYTHON_APPS),$(app)-dev):%-dev:%-venv/bin/adev
	-@lsof -t -i :$($*_PORT) | xargs kill -9 2>/dev/null || true
	$(if $($*_HEALTH_PORT),-@lsof -t -i :$($*_HEALTH_PORT) | xargs kill -9 2>/dev/null || true)
	cd $*-container && \
	${BASE_DIR}$*-venv/bin/adev runserver --port ${$*_PORT}

# Run tests (Python)
$(foreach app,$(PYTHON_APPS),$(app)-test):%-test:%-venv/bin/pytest
	cd $*-container && \
	PYTHONPATH=. ../$*-venv/bin/pytest

# --- Node/Frontend Patterns ---

# Install dependencies (Node)
$(foreach app,$(NODE_APPS),$(app)-container/node_modules):%-container/node_modules:%-container/package.json
	cd $*-container && npm install

# Run dev server (Node)
$(foreach app,$(NODE_APPS),$(app)-dev):%-dev:%-container/node_modules
	-@lsof -t -i :$($*_PORT) | xargs kill -9 2>/dev/null || true
	cd $*-container && ng serve --port ${$*_PORT}

# Run tests (Node)
$(foreach app,$(NODE_APPS),$(app)-test):%-test:%-container/node_modules
	cd $*-container && npm test

# --- Rust App Patterns ---

$(foreach app,$(RUST_APPS),$(app)-dev):%-dev:
	-@lsof -t -i :$($*_PORT) | xargs kill -9 2>/dev/null || true
	$(if $($*_HEALTH_PORT),-@lsof -t -i :$($*_HEALTH_PORT) | xargs kill -9 2>/dev/null || true)
	cd $*-container && cargo run

$(foreach app,$(RUST_APPS),$(app)-test):%-test:
	cd $*-container && cargo test

# --- Docker ---

$(foreach app,$(APPS),$(app)-docker):%-docker:
	cd $*-container && docker build ${$*_DOCKER_BUILD_OPTS} -t $* .

# Docker Run
$(foreach app,$(APPS),$(app)-docker-run):%-docker-run:%-docker
	docker run -it --rm --name $* \
		-p ${$*_PORT}:${$*_INTERNAL_PORT} \
		$(if $($*_HEALTH_PORT),-p ${$*_HEALTH_PORT}:${$*_INTERNAL_HEALTH_PORT}) \
		-e NO_DB=true \
		-e APP_PERSISTENCE__DB__CONNECTION__URL=postgresql://host.docker.internal:5432/agentdb \
		--mount type=bind,src=$(PWD)/$*-container/tests/test_data,dst=/test_data \
		$* start --config /test_data/config.yaml --secrets /test_data/secrets

venvs: $(foreach app,$(PYTHON_APPS),$(app)-venv/bin/activate)
tests: $(foreach app,$(APPS),$(app)-test)

# --- Database ---
compose-db-up:
	@if docker ps --format '{{.Names}}' | grep -Eq "^agent-postgres$$"; then \
		echo "Container agent-postgres is already running. Attaching to logs..."; \
		docker logs -f agent-postgres; \
	else \
		docker compose -f docker-compose/postgres.yaml up; \
	fi

compose-db-down:
	@echo "Stopping and removing local Postgres database container..."
	docker compose -f docker-compose/postgres.yaml down

compose-db-clean:
	@echo "Stopping Postgres container and removing database volumes..."
	docker compose -f docker-compose/postgres.yaml down -v

# Backward compatibility alias
compose-db: compose-db-up

db-local:
	docker container stop agent-postgres || true
	@echo "Starting Postgres on port 5432"
	docker run -it --rm --name agent-postgres \
		-e POSTGRES_PASSWORD=mysecretpassword \
		-e POSTGRES_DB=agentdb \
		-p 5432:5432 \
		pgvector/pgvector:pg15

# --- Garden ---
garden-up:
	@echo "Logging Helm into GHCR and running Garden deploy..."
	@echo "$${GHCR_TOKEN}" | helm registry login ghcr.io -u "$${GHCR_USER:-bengreen}" --password-stdin 2>/dev/null || true
	garden deploy

garden-test: garden-up
	@echo "Running Garden tests..."
	garden test

garden-down:
	@echo "Tearing down Garden environment..."
	garden cleanup env
