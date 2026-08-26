FROM python:3.11-slim as base

LABEL maintainer="PR Triage Bot"
LABEL description="AI-powered maintainer co-pilot"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ─── System dependencies ───────────────────────
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# ─── Install Python dependencies ───────────────
COPY pyproject.toml .
RUN pip install -e "."

# ─── Copy source ────────────────────────────────
COPY src/ ./src/
COPY config/ ./config/

# ─── Non-root user ──────────────────────────────
RUN useradd -m -u 1000 triage && chown -R triage:triage /app
USER triage

ENTRYPOINT ["triage"]
CMD ["--help"]