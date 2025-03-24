FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for models
RUN mkdir -p /app/models

# Copy application files
COPY . .

# Expose port - environment variable will override this
EXPOSE 8080

# Use Render's PORT environment variable
CMD gunicorn --bind 0.0.0.0:$PORT app:app
