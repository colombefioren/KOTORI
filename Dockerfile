# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# KOTORI — single container, non-root, with a writable data volume
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    KOTORI_DATA_DIR=/data \
    PORT=7860 \
    GRADIO_SERVER_NAME=0.0.0.0

COPY --from=ghcr.io/astral-sh/uv:0.12.11 /uv /uvx /usr/local/bin/

WORKDIR /app

# dependencies first: this layer only rebuilds when the lockfile moves
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

COPY app.py ./
COPY .env.example ./

ENV PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --uid 10001 kotori \
 && mkdir -p /data \
 && chown -R kotori:kotori /data /app /opt/venv

USER kotori
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c 'import os, urllib.request; urllib.request.urlopen("http://127.0.0.1:" + os.environ.get("PORT", "7860") + "/", timeout=4)'

CMD ["python", "app.py"]
