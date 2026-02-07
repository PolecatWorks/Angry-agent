
.PHONY: frontend-dev frontend-docker frontend-docker-run \
        db-local

BASE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))


PYTHON_APPS := agent-be
NODE_APPS := agent-ui
APPS := $(PYTHON_APPS) $(NODE_APPS)

agent-be_PORT := 8080
agent-ui_PORT := 4200

agent-be_INTERNAL_PORT := 8080
agent-ui_INTERNAL_PORT := 8080

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

# Run development server
$(foreach app,$(PYTHON_APPS),$(app)-dev):%-dev:%-venv/bin/adev
	cd $*-container && \
	${BASE_DIR}$*-venv/bin/adev runserver --port ${$*_PORT}

# Run tests
$(foreach app,$(PYTHON_APPS),$(app)-test):%-test:%-venv/bin/pytest
	cd $*-container && \
	PYTHONPATH=src ../$*-venv/bin/pytest

# --- Node/Frontend Patterns ---

# Install dependencies (Node)
$(foreach app,$(NODE_APPS),$(app)-container/node_modules):%-container/node_modules:%-container/package.json
	cd $*-container && npm install

# Run dev server (Node)
$(foreach app,$(NODE_APPS),$(app)-dev):%-dev:%-container/node_modules
	cd $*-container && npm start

# Run tests (Node)
$(foreach app,$(NODE_APPS),$(app)-test):%-test:%-container/node_modules
	cd $*-container && npm test

# --- Docker ---

# Docker Build
$(foreach app,$(APPS),$(app)-docker):%-docker:
	docker build -t $* $*-container

# Docker Run
$(foreach app,$(APPS),$(app)-docker-run):%-docker-run:%-docker
	docker run -it --rm --name $* \
		-p ${$*_PORT}:${$*_INTERNAL_PORT} \
		-e NO_DB=true \
		$*

.PHONY: venvs tests
venvs: $(foreach app,$(PYTHON_APPS),$(app)-venv/bin/activate)
tests: $(foreach app,$(APPS),$(app)-test)




# --- Database ---

db-local:
	docker container stop agent-postgres || true
# 	docker rm -f agent-postgres || true
	@echo "Starting Postgres on port 5432"
	docker run -it --rm --name agent-postgres \
		-e POSTGRES_PASSWORD=mysecretpassword \
		-e POSTGRES_DB=agentdb \
		-p 5432:5432 \
		postgres:15-alpine
