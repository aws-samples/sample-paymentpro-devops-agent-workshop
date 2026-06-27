# Multi-stage build for Fraud Service
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy shared library first (dependency)
COPY shared/ /shared/
RUN pip install --no-cache-dir /shared

# Copy service requirements and install
COPY services/fraud/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/fraud/app/ ./app/

# Production stage
FROM base AS production

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 8004

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8004/health')"]

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004", "--workers", "1"]
