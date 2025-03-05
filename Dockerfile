FROM python:3.9-slim

# Install Tesseract OCR and Poppler utils for PDF processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY app.py requirements.txt ./
COPY static/ ./static/

# Create uploads directory
RUN mkdir -p uploads

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
