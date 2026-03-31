# ─────────────────────────────────────────────────────────────────────────────
# NEXUS — Production Dockerfile for Cloud Run
#
# Multi-stage build:
#   builder  →  compiles wheels for psycopg2 and grpcio (C extensions)
#   runtime  →  minimal image, no build tools, non-root user
#
# Cloud Run specifics:
#   • Listens on $PORT (injected by Cloud Run, default 8080)
#   • Single worker — Cloud Run scales horizontally, not vertically
#   • No .env file — secrets come from Secret Manager / env vars at deploy
#   • SIGTERM handling via --timeout-graceful-shutdown 10
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Build deps for psycopg2-binary, grpcio, aiohttp (C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY nexus/requirements.txt ./

# Build wheels into a local cache directory for the runtime stage
RUN pip install --upgrade pip \
 && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime OS deps only (libpq for psycopg2 shared lib)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1001 nexus \
    && useradd  --uid 1001 --gid nexus --shell /bin/bash --create-home nexus

# Install pre-built wheels — no compiler needed
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* \
 && rm -rf /wheels

# Copy application code (repo root → /app, so `nexus` is a package)
# .dockerignore strips venvs, .git, secrets, tests
COPY . .

# Storage dir for Blackboard JSON (L2 persistence)
RUN mkdir -p /app/nexus/storage \
 && chown -R nexus:nexus /app

USER nexus

# Cloud Run injects PORT; we expose the default for documentation
EXPOSE 8080

# uvicorn flags:
#   --workers 1        — Cloud Run scales by instances, not workers
#   --loop uvloop      — faster event loop (installed via requirements)
#   --timeout-graceful-shutdown 10  — give in-flight SSE streams 10 s
ENV PORT=8080
CMD ["sh", "-c", \
     "uvicorn nexus.main:app \
        --host 0.0.0.0 \
        --port ${PORT} \
        --workers 1 \
        --timeout-graceful-shutdown 10 \
        --no-access-log"]
