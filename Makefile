.PHONY: test test-cov test-fast install install-test clean lint format quality help

# Default target
help:
	@echo "Available commands:"
	@echo "  install      Install dependencies"
	@echo "  install-test Install test dependencies"
	@echo "  test         Run all tests"
	@echo "  test-cov     Run tests with coverage report"
	@echo "  test-fast    Run tests without verbose output"
	@echo "  lint         Run code linting"
	@echo "  format       Format code with black and isort"
	@echo "  quality      Run all quality checks"
	@echo "  clean        Clean up temporary files"

# Install dependencies
install:
	python3 -m venv venv
	. venv/bin/activate && pip install -U pip
	. venv/bin/activate && pip install -r requirements.txt

# Install test dependencies
install-test:
	. venv/bin/activate && pip install -r requirements-test.txt

# Run tests
test:
	. venv/bin/activate && pytest tests/ -v

# Run tests with coverage
test-cov:
	. venv/bin/activate && pytest tests/ --cov=get_bus_data --cov-report=term-missing --cov-report=html

# Run tests quickly (less verbose)
test-fast:
	. venv/bin/activate && pytest tests/ -q

# Clean up
clean:
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf __pycache__/
	rm -rf tests/__pycache__/
	rm -f .coverage
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

# Code quality tools
lint:
	. venv/bin/activate && ruff check .

format:
	. venv/bin/activate && black .
	. venv/bin/activate && isort .

quality: lint test
	. venv/bin/activate && black --check .
	. venv/bin/activate && isort --check-only .

# Install quality tools
install-quality:
	. venv/bin/activate && pip install black isort ruff bandit