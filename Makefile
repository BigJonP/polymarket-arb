SHELL := /bin/bash

VENV_PYTHON := .venv/bin/python
BACKEND_DIR := backend
BACKEND_APP := app.main:app
FRONTEND_DIR := frontend

.DEFAULT_GOAL := help

.PHONY: help db install install-backend install-frontend backend frontend dev

help:
	@printf "Available targets:\n"
	@printf "  make db                Start PostgreSQL in Docker\n"
	@printf "  make install-backend   Create .venv if needed and install backend dependencies\n"
	@printf "  make install-frontend  Install frontend dependencies\n"
	@printf "  make install           Install backend and frontend dependencies\n"
	@printf "  make backend           Run the FastAPI backend on http://localhost:8000\n"
	@printf "  make frontend          Run the Vite frontend on http://localhost:5173\n"
	@printf "  make dev               Start db, backend, and frontend together\n"

db:
	docker compose up db -d

install: install-backend install-frontend

install-backend:
	@test -x $(VENV_PYTHON) || python3 -m venv .venv
	./.venv/bin/pip install -r backend/requirements.txt

install-frontend:
	npm --prefix $(FRONTEND_DIR) install

backend:
	@test -x $(VENV_PYTHON) || (echo "Missing .venv. Run 'make install-backend' first." >&2; exit 1)
	$(VENV_PYTHON) -m uvicorn $(BACKEND_APP) --app-dir $(BACKEND_DIR) --reload

frontend:
	@test -d $(FRONTEND_DIR)/node_modules || (echo "Missing frontend/node_modules. Run 'make install-frontend' first." >&2; exit 1)
	npm --prefix $(FRONTEND_DIR) run dev

dev:
	@test -x $(VENV_PYTHON) || (echo "Missing .venv. Run 'make install-backend' first." >&2; exit 1)
	@test -d $(FRONTEND_DIR)/node_modules || (echo "Missing frontend/node_modules. Run 'make install-frontend' first." >&2; exit 1)
	@set -e; \
		trap 'kill 0' EXIT INT TERM; \
		docker compose up db -d >/dev/null; \
		$(VENV_PYTHON) -m uvicorn $(BACKEND_APP) --app-dir $(BACKEND_DIR) --reload & \
		npm --prefix $(FRONTEND_DIR) run dev & \
		wait
