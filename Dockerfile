FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RENDER=true

# Install Tesseract OCR and Poppler (needed for PDF processing)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create model directory
RUN mkdir -p /app/models

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Make directories if they don't exist
RUN mkdir -p static && mkdir -p templates

# Run with gunicorn - Render will set the PORT environment variable
CMD gunicorn --bind 0.0.0.0:$PORT app:app --timeout 120
