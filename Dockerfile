FROM python:3.9-slim

# Install system dependencies: OCR engine (Tesseract) & PDF utilities (Poppler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Create required folders (used by app)
RUN mkdir -p static/css static/js templates models

# Copy requirements file first for Docker cache optimization
COPY requirements.txt .

# Install dependencies (minus torch, which we handle separately)
RUN pip install --no-cache-dir -r requirements.txt || echo "Proceeding without torch"

# Install PyTorch separately from the official CPU-only wheel source
RUN pip install --no-cache-dir torch==2.0.1+cpu --index-url https://download.pytorch.org/whl/cpu

# Pre-download transformers model into image (avoids slow cold starts)
RUN python -c "from transformers import pipeline; pipeline('zero-shot-classification', model='typeform/distilbert-base-uncased-mnli')"

# Copy application code and assets
COPY app.py ai_document_processor.py ./
COPY static/ static/
COPY templates/ templates/

# Environment best practices
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose the port Flask runs on
EXPOSE 5000

# Launch the app using Gunicorn (production-ready WSGI server)
CMD gunicorn --workers=1 --bind 0.0.0.0:${PORT:-5000} --timeout 120 app:app
