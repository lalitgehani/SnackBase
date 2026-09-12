# SnackBase multi-stage image: React admin UI + Python API.
# Runtime keeps `uv` for Functions env builds, but not the C toolchain.
#
# Every base image is pinned by digest as well as tag: a floating tag resolves
# to whatever the registry serves at build time, so the same commit would not
# produce the same image and a compromised upstream tag would go unnoticed.
# The Python minor must match `.python-version` — otherwise CI validates an
# interpreter that never ships. Refresh a digest with:
#   docker buildx imagetools inspect <image>:<tag>

# ---------------------------------------------------------------------------
# Stage 1: Build React frontend
# ---------------------------------------------------------------------------
FROM node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 AS frontend-builder

WORKDIR /app/ui

# Manifests first: dependencies only re-resolve when they actually change,
# so editing UI source reuses the cached install layer.
COPY ui/package.json ui/package-lock.json ./

# `npm ci` installs the locked tree exactly — the same versions CI and a local
# checkout resolve. The SDK packages come from the registry like any other
# dependency, so this needs nothing outside the SnackBase build context.
RUN npm ci

COPY ui/ .

# Inject demo flag at build time so Vite inlines it into the bundle.
# VITE_* vars are read from process.env by Vite at build time only.
ARG VITE_IS_DEMO=false
ENV VITE_IS_DEMO=$VITE_IS_DEMO
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Install Python dependencies (wheels only — no compiler)
# ---------------------------------------------------------------------------
FROM python:3.14-slim@sha256:a7fb1e634c4a578f9e0bd6327f11a3cde11b7a9395f48e24360c0988bcc5c2bc AS python-builder

# Pin uv; bump intentionally when upgrading the Functions installer.
COPY --from=ghcr.io/astral-sh/uv:0.12.1@sha256:cf4eedcaa81655197f625739489effcbe71b61ceb1506f332c3facae5deceded /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Project metadata + lock first for better layer caching.
# alembic.ini and alembic/ must be present here: --no-editable builds a wheel,
# and hatch force-includes those paths into the package (needed so a pip-installed
# snackbase can migrate without a git checkout). Missing them fails the build
# with FileNotFoundError: Forced include not found: /app/alembic.
COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY packages ./packages

# Production deps only; manylinux wheels cover all native packages.
# ruff is also required at runtime: alembic.ini runs it as a post_write_hook when
# generating dynamic collection migrations.
RUN uv sync --frozen --no-dev --no-editable \
    && uv pip install "ruff==0.14.10"

# ---------------------------------------------------------------------------
# Stage 3: Slim runtime (no gcc; uv kept for Functions)
# ---------------------------------------------------------------------------
FROM python:3.14-slim@sha256:a7fb1e634c4a578f9e0bd6327f11a3cde11b7a9395f48e24360c0988bcc5c2bc

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH" \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# curl: docker-compose healthchecks. Do NOT install build-essential.
# Functions confinement needs no package: it uses the kernel's Landlock LSM,
# which requires neither extra capabilities nor a seccomp exemption.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uv is required at runtime for Functions per-version env builds.
COPY --from=ghcr.io/astral-sh/uv:0.12.1@sha256:cf4eedcaa81655197f625739489effcbe71b61ceb1506f332c3facae5deceded /uv /bin/uv

# Application virtualenv and source
COPY --from=python-builder /app/.venv /app/.venv
COPY --from=python-builder /app/src /app/src
COPY --from=python-builder /app/packages /app/packages
COPY --from=python-builder /app/pyproject.toml /app/uv.lock /app/README.md ./

# Migrations
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Built admin UI
COPY --from=frontend-builder /app/ui/dist ./static

EXPOSE 8000

# Use the venv uvicorn directly; uv remains available for Functions only.
CMD ["sh", "-c", "uvicorn snackbase.infrastructure.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
