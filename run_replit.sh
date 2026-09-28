#!/bin/bash
set -e

echo "=== Initializing NEXUS Enterprise Platform on Replit ==="

# 1. Generate sample enterprise documents if not already generated
if [ ! -d "sample_data/documents" ] || [ -z "$(ls -A sample_data/documents 2>/dev/null)" ]; then
    echo "Generating sample enterprise policy PDFs..."
    python sample_data/generate_sample_pdfs.py
fi

# 2. Start Uvicorn server on port 8080 (standard Replit Webview port)
echo "Starting Uvicorn ASGI Server..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8080 --reload
