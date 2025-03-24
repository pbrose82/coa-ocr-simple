FROM python:3.9-slim

# Install Tesseract OCR and Poppler (needed for PDF processing)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p static/css static/js templates models

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py ai_document_processor.py ./
COPY static/ static/
COPY templates/ templates/

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Run the application with gunicorn for production
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --timeout 120 app:app
