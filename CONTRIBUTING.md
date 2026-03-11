# Contributing to Prediction Analyzer

Thank you for your interest in contributing! This guide covers setup, standards, and the PR process.

## Development Setup

```bash
# Clone and install in editable mode with all extras
git clone https://github.com/Frostbite1536/Prediction_Analyzer.git
cd Prediction_Analyzer
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[api,mcp,dev]"
```

## Running Checks

```bash
make test        # Run tests
make lint        # Lint with flake8
make fmt         # Format with black
make typecheck   # Type check with mypy
```

All checks must pass before submitting a PR. The CI pipeline runs tests on Python 3.9-3.12.

## Code Standards

- **Formatting**: black (line length 100). Run `make fmt` before committing.
- **Linting**: flake8 with the project `.flake8` config.
- **Type hints**: Required on all public function signatures. Run `make typecheck`.
- **Docstrings**: Required on all public functions and classes.
- **Tests**: New features must include tests. Bug fixes should include a regression test.

## Architecture Rules

- `prediction_mcp` may import from `prediction_analyzer`, but not the reverse.
- All MCP tool handlers must use the `@safe_tool` decorator — no manual try/except.
- Never log API keys. Only reference environment variable *names* in error messages.
- Use `sanitize_numeric()` on all floats before JSON serialization.
- DB monetary columns must use `Numeric(18, 8)`, never `Float`.

## Branch Strategy

- `main` — stable release branch
- Feature branches: `feature/<description>`
- Bug fixes: `fix/<description>`

## Pull Request Process

1. Create a feature/fix branch from `main`
2. Make your changes with clear, atomic commits
3. Ensure all checks pass (`make test lint fmt-check`)
4. Open a PR against `main` with:
   - A clear title (under 70 chars)
   - Description of what and why
   - Test plan
5. Address review feedback

## Adding a New Provider

See the detailed guide in [CLAUDE.md](CLAUDE.md#adding-a-new-provider).

## Adding a New MCP Tool

See the detailed guide in [CLAUDE.md](CLAUDE.md#adding-a-new-mcp-tool).

## License

By contributing, you agree that your contributions will be licensed under the AGPL-3.0 license.
