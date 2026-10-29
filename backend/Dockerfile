# Multi-stage build: the `builder` stage has the compiler toolchain needed
# to build faiss-cpu/scikit-learn wheels; the final image only ships the
# installed packages + app code, not build-essential or pip's cache — keeps
# the shipped image meaningfully smaller and reduces attack surface.

FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Build into a venv rather than --user installs — makes the COPY into the
# runtime stage a single, clean directory instead of chasing site-packages
# across both stages' Python install layouts.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


FROM python:3.12-slim AS runtime

# faiss needs libgomp1 (OpenMP) at runtime even though it doesn't need the
# full build-essential toolchain that compiled it.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Baked in at build time (CI passes --build-arg GIT_COMMIT_SHA=$GITHUB_SHA —
# see .github/workflows/ci.yml) so /health and /v1/evaluation/summary can
# report which exact commit is running, without a .git directory shipping
# in the image. core/config.py reads this via os.environ, falling back to
# `git rev-parse` for local `docker run` without the build-arg, then
# "unknown".
ARG GIT_COMMIT_SHA=unknown
ENV GIT_COMMIT_SHA=${GIT_COMMIT_SHA}

WORKDIR /app
COPY --chown=appuser:appuser . .

USER appuser

# Render/App Runner/ECS all set $PORT at runtime; default to 8000 for
# `docker run` / docker-compose local use.
ENV PORT=8000
EXPOSE 8000

# Container-level health check — distinct from the app's own /health route,
# this is what `docker ps` and docker-compose's `depends_on: condition:
# service_healthy` check against.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f "http://localhost:${PORT}/health" || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers ${UVICORN_WORKERS:-2}"]
