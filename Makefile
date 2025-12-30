.PHONY: help install dev test lint format clean docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies with uv"
	@echo "  make dev        - Start development server"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean cache and build files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up  - Start Docker Compose"
	@echo "  make docker-down - Stop Docker Compose"

install:
	uv sync

dev:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run mypy src

format:
	uv run black src tests
	uv run ruff check --fix .

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

docker-build:
	docker build -t qualifybot:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down


