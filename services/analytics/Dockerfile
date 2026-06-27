FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY shared/ /shared/
RUN pip install --no-cache-dir /shared

COPY services/analytics/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/analytics/app/ ./app/

FROM base AS production

RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 8005

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8005/health')"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "1"]
