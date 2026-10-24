# Multi-stage production container for OrderFlow360 Analytics Platform
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Create data directories
RUN mkdir -p /app/data/raw /app/data/staging /app/data/quarantine /app/data/warehouse /app/reports

# Run ETL pipeline on container build to seed warehouse
RUN python src/etl/pipeline.py

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/kpis || exit 1

CMD ["python", "app/server.py"]
