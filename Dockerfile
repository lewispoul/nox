# Multi-stage Dockerfile for Nox API v7.0.0
# Optimized for production with security hardening

# ===== BUILD STAGE =====
FROM python:3.13-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    rust \
    cargo \
    openssl-dev

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt

# ===== RUNTIME STAGE =====
FROM python:3.13-alpine AS runtime

# Install runtime dependencies only
RUN apk add --no-cache \
    postgresql-libs \
    curl \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1001 -S noxapi && \
    adduser -S -D -H -u 1001 -h /app -s /sbin/nologin -G noxapi -g noxapi noxapi

# Set working directory and copy virtual environment
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=noxapi:noxapi . .

# Ensure virtual environment is in PATH
ENV PATH="/opt/venv/bin:$PATH"

# Create logs directory
RUN mkdir -p /app/logs && chown -R noxapi:noxapi /app/logs

# Switch to non-root user
USER noxapi

# Expose port
EXPOSE 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8082/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "nox-api.api.nox_api:app", "--host", "0.0.0.0", "--port", "8082"]
