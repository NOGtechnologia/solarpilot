.PHONY: install dev backend frontend test test-backend test-frontend lint format build e2e docker up down

PY ?= python3
VENV = backend/.venv
BIN = $(VENV)/bin

install:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -e "backend[dev]"
	cd frontend && npm ci

# Backend (:8000) und Frontend mit Hot-Reload (:3000) parallel
dev:
	$(MAKE) -j2 backend frontend

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	cd backend && .venv/bin/pytest --cov=app --cov-report=term-missing

test-frontend:
	cd frontend && npm test

lint:
	cd backend && .venv/bin/ruff check app tests && .venv/bin/ruff format --check app tests
	cd frontend && npm run lint

format:
	cd backend && .venv/bin/ruff format app tests && .venv/bin/ruff check --fix app tests

build:
	cd frontend && npm run build

# End-to-End-Test: Backend liefert das gebaute Frontend aus, Playwright klickt durch
e2e: build
	cd frontend && npm run e2e

docker:
	docker build -t solarpilot:local .

up:
	docker compose up -d --build

down:
	docker compose down
