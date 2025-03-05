FROM python:3.9-slim

# Install Tesseract OCR and Poppler utils for PDF processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py config.py templates.py ./
COPY static/ ./static/

# Create uploads directory
RUN mkdir -p uploads

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
