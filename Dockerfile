FROM python:3.12-slim AS base

WORKDIR /app

# Install system deps (needed for cryptography wheel)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml setup.py requirements.txt ./
COPY prediction_analyzer/ prediction_analyzer/
COPY prediction_mcp/ prediction_mcp/

RUN pip install --no-cache-dir -e ".[api,mcp]"

# ---------------------------------------------------------------------------
# Web API target
# ---------------------------------------------------------------------------
FROM base AS api

EXPOSE 8000

# Non-root user for security
RUN useradd --create-home appuser
USER appuser

# Ensure data directory exists
RUN mkdir -p /app/data

CMD ["uvicorn", "prediction_analyzer.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------------------------------------------------------------------------
# MCP SSE server target
# ---------------------------------------------------------------------------
FROM base AS mcp

EXPOSE 8001

RUN useradd --create-home appuser
USER appuser

CMD ["python", "-m", "prediction_mcp", "--sse", "--port", "8001"]
