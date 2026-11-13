# Image de production du back AXIOME.
#  - LibreOffice : conversion Word -> PDF des rapports (rapports_service appelle `soffice --headless`)
#  - Tesseract (fra+eng) et Poppler : OCR de la GED
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 \
    HOME=/home/axiome STORAGE_DIR=/data/storage

RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-writer libreoffice-calc default-jre-headless \
        fonts-liberation fonts-dejavu-core \
        tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng poppler-utils \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 axiome && mkdir -p /data/storage && chown -R axiome /data
WORKDIR /srv/axiome

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY --chown=axiome . .
USER axiome
VOLUME ["/data/storage"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

# Migrations puis serveur. WORKERS=2 par défaut ; ajuster selon le CPU.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-2} --proxy-headers --forwarded-allow-ips='*'"]
