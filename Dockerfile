# Builds the NiftyScout API service (backend/) for Railway.
# Built from the repo root so it can pull in the niftyscout/ package that
# lives alongside backend/ — do not set a "root directory" for this service
# in Railway, leave it pointed at the repo root.
FROM python:3.11-slim

WORKDIR /app

# matplotlib needs these at build time for some wheels/backends
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY niftyscout/ niftyscout/
COPY backend/ backend/
COPY config.yaml config.yaml

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
