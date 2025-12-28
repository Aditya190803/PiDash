# syntax=docker/dockerfile:1.4

# Builder stage: build wheels and install into a virtualenv (uses pip cache via BuildKit)
FROM python:3.12-slim AS builder
WORKDIR /app

# copy only requirements first so this layer is cacheable
COPY requirements.txt .

# install build deps required for packages like psutil
# use BuildKit cache mounts for apt to avoid re-downloading packages between builds
RUN --mount=type=cache,target=/var/cache/apt/archives \
  --mount=type=cache,target=/var/lib/apt/lists \
  apt-get update && apt-get install -y --no-install-recommends \
  gcc make python3-dev libffi-dev libssl-dev curl && \
  rm -rf /var/lib/apt/lists/*

# Build wheels (cached by BuildKit) and install into a virtualenv
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir=/wheels --prefer-binary -r requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-index --find-links=/wheels -r requirements.txt


# Final lightweight runtime image
FROM python:3.12-slim
WORKDIR /app

# Install only small runtime deps (curl for healthcheck)
RUN --mount=type=cache,target=/var/cache/apt/archives \
  --mount=type=cache,target=/var/lib/apt/lists \
  apt-get update && apt-get install -y --no-install-recommends \
  curl && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code (after deps so rebuilds are cached when code changes)
COPY . .

# Ensure upload dir exists and set permissions
RUN mkdir -p /app/lsfile \
  && groupadd -r appuser \
  && useradd -r -g appuser -d /app -s /sbin/nologin -c "App user" appuser \
  && chown -R appuser:appuser /app /app/lsfile

VOLUME /app/lsfile
USER appuser

EXPOSE 5001

COPY .env.example .env

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--timeout", "120", "app:app"]

