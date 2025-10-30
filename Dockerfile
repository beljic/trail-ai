# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY common/ ./common/
COPY scrapers/ ./scrapers/
COPY ai/ ./ai/
COPY api/ ./api/
COPY scrape_all.py .
COPY import_to_db.py .
COPY embed_races.py .
COPY embed_from_jsonl.py .

# Create data directories
RUN mkdir -p data/raw data/clean data/chroma

# Expose API port
EXPOSE 8000

# Default command: run scraper
CMD ["python", "scrape_all.py"]
