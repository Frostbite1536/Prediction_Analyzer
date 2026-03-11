.PHONY: install install-dev test lint fmt typecheck serve mcp gui clean help

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install core dependencies
	pip install -e .

install-dev: ## Install all dependencies (api + mcp + dev)
	pip install -e ".[api,mcp,dev]"

test: ## Run test suite
	pytest -q

test-cov: ## Run tests with coverage report
	pytest --cov=prediction_analyzer --cov=prediction_mcp --cov-report=term-missing

lint: ## Run flake8 linter
	flake8 prediction_analyzer prediction_mcp

fmt: ## Format code with black
	black prediction_analyzer prediction_mcp tests

fmt-check: ## Check formatting without modifying files
	black --check prediction_analyzer prediction_mcp tests

typecheck: ## Run mypy type checker
	mypy prediction_analyzer prediction_mcp

serve: ## Start the FastAPI web server
	python run_api.py

mcp: ## Start the MCP server (stdio)
	python -m prediction_mcp

mcp-sse: ## Start the MCP server (HTTP/SSE)
	python -m prediction_mcp --sse

gui: ## Launch the desktop GUI
	python run_gui.py

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build dist .pytest_cache htmlcov .coverage coverage.xml .mypy_cache
