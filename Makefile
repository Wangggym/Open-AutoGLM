SHELL := /bin/bash

HIDE ?= @

# Load .env file if exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

.PHONY: gen install dev run test check fix lint clean help

name := "phone-agent"

# Initialize environment (first-time setup)
gen:
	@echo "🐍 Initializing Python project environment..."
	$(HIDE)uv sync
	$(HIDE)uv run pre-commit install
	-$(HIDE)cp .env.example .env 2>/dev/null || true
	@echo "✅ Environment initialized."
	@echo "📝 Please edit .env file and set your API key."

# Install dependencies (production only)
install:
	$(HIDE)uv sync --no-dev
	@echo "✅ Dependencies installed."

# Development mode (interactive)
dev:
	$(HIDE)uv run python main.py --interactive

# Run phone agent
run:
	$(HIDE)uv run python main.py

# Run with specific task
run-task:
	$(HIDE)uv run python main.py --task "$(TASK)"

# Check system requirements
run-check:
	$(HIDE)uv run python main.py --check

# Run tests
test:
	$(HIDE)uv run pytest -v
	@echo "✅ Tests passed."

# Type checking and linting
check:
	$(HIDE)uv run ruff check .
	$(HIDE)uv run mypy phone_agent/
	@echo "✅ Check and lint completed."

# Format and fix code
fix:
	$(HIDE)uv run black .
	$(HIDE)uv run ruff check --fix .
	@echo "✅ Code formatted and fixed."

# Lint check (without fixing)
lint:
	$(HIDE)uv run ruff check .
	$(HIDE)uv run black --check .
	@echo "✅ Lint check completed."

# Run pre-commit hooks
pre-commit:
	$(HIDE)uv run pre-commit run --all-files
	@echo "✅ Pre-commit hooks passed."

# Update dependencies
update:
	$(HIDE)uv lock --upgrade
	$(HIDE)uv sync
	@echo "✅ Dependencies updated."

# Run examples
example-basic:
	$(HIDE)uv run python examples/basic_usage.py

example-thinking:
	$(HIDE)uv run python examples/demo_thinking.py

# Deployment check scripts
check-deploy-cn:
	$(HIDE)uv run python scripts/check_deployment_cn.py

check-deploy-en:
	$(HIDE)uv run python scripts/check_deployment_en.py

# Sync with upstream repository
upstream-sync:
	$(HIDE)git fetch upstream
	$(HIDE)git merge upstream/main
	@echo "✅ Synced with upstream."

upstream-rebase:
	$(HIDE)git fetch upstream
	$(HIDE)git rebase upstream/main
	@echo "✅ Rebased on upstream."

# Cleanup
clean:
	-$(HIDE)rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	-$(HIDE)rm -rf build/ dist/ *.egg-info/
	-$(HIDE)find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	-$(HIDE)find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleaned up."

clean-all: clean
	-$(HIDE)rm -rf .venv/
	@echo "✅ Cleaned all (including venv)."

# Help
help:
	@echo "Available commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make gen            - Initialize environment (creates .env from .env.example)"
	@echo "  make install        - Install dependencies (production)"
	@echo "  make update         - Update all dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev            - Run in interactive mode"
	@echo "  make run            - Run phone agent"
	@echo "  make run-task TASK= - Run specific task"
	@echo "  make run-check      - Check system requirements"
	@echo "  make test           - Run tests"
	@echo "  make check          - Type checking and linting"
	@echo "  make fix            - Format and fix code"
	@echo "  make lint           - Lint check"
	@echo "  make pre-commit     - Run pre-commit hooks"
	@echo ""
	@echo "Examples:"
	@echo "  make example-basic    - Run basic usage example"
	@echo "  make example-thinking - Run thinking demo"
	@echo ""
	@echo "Deployment Check:"
	@echo "  make check-deploy-cn  - Check deployment (Chinese)"
	@echo "  make check-deploy-en  - Check deployment (English)"
	@echo ""
	@echo "Git:"
	@echo "  make upstream-sync    - Sync with upstream (merge)"
	@echo "  make upstream-rebase  - Sync with upstream (rebase)"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          - Clean cache files"
	@echo "  make clean-all      - Clean all (including venv)"
