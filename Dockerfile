FROM python:3.13-slim

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    libfreetype6-dev \
    libjpeg-dev \
    libpng-dev \
    libssl-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Generate sample data
RUN python sample_data/generate_sample_pdfs.py

# Create storage dir
RUN mkdir -p backend/storage

EXPOSE 8000

# Production entrypoint — uses PORT env var (Render injects it)
CMD uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2
