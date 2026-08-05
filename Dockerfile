FROM node:22-bookworm-slim AS node-deps
WORKDIR /node
COPY node/package.json ./package.json
RUN npm install --omit=dev --no-audit --no-fund --registry=https://registry.npmjs.org
COPY node/worker.mjs ./worker.mjs

FROM debian:bookworm-slim AS official-artifacts
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl unzip && rm -rf /var/lib/apt/lists/*
COPY scripts/fetch_official_xsd.sh /usr/local/bin/fetch_official_xsd.sh
RUN /usr/local/bin/fetch_official_xsd.sh /opt/fiscalrail/ubl

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    APP_ENV=production \
    ALLOW_UNAUTHENTICATED=false \
    ALLOW_LEGACY_FALLBACK=false \
    ENABLE_OFFICIAL_ENGINE=true \
    OFFICIAL_WORKER_PATH=/app/node/worker.mjs \
    UBL_XSD_ROOT=/opt/fiscalrail/ubl

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=node-deps /usr/local/bin/node /usr/local/bin/node
COPY --from=node-deps /node /app/node
COPY --from=official-artifacts /opt/fiscalrail/ubl /opt/fiscalrail/ubl
COPY app ./app
COPY examples ./examples
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT','8000') + '/ready', timeout=4)"
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'"]
