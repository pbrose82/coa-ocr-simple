FROM python:3.9-slim

# Install Tesseract OCR and Poppler (needed for PDF processing)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY static/ static/
COPY templates/ templates/

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
