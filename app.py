from flask import Flask, request, jsonify, render_template_string
import os
import pytesseract
from PIL import Image
import re
import json
import requests
from werkzeug.utils import secure_filename
import uuid
import logging
import time
from pdf2image import convert_from_path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff'}
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')
ALCHEMY_API_URL = os.getenv('ALCHEMY_API_URL')

# HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>COA OCR Extractor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { 
            padding-top: 20px; 
            padding-bottom: 40px;
        }
        .container {
            max-width: 800px;
        }
        .result-box {
            margin-top: 20px;
            padding: 15px;
            border-radius: 5px;
            background-color: #f8f9fa;
        }
        pre {
            background-color: #f1f1f1;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
        }
        .loader {
            border: 5px solid #f3f3f3;
            border-top: 5px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 2s linear infinite;
            margin: 20px auto;
            display: none;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .api-settings {
            margin-top: 20px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .processing-status {
            display: none;
            margin-top: 15px;
            padding: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-center mb-4">COA OCR to Alchemy</h1>
        
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">Upload COA Document</h5>
            </div>
            <div class="card-body">
                <form id="uploadForm" enctype="multipart/form-data" class="mb-3">
                    <div class="mb-3">
                        <label for="file" class="form-label">Select COA file (JPG, PNG, PDF, TIFF)</label>
                        <input class="form-control" type="file" id="file" name="file" accept=".jpg,.jpeg,.png,.pdf,.tiff">
                        <div class="form-text text-muted">
                            PDFs may take longer to process. For faster results, consider uploading images.
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">Extract Data</button>
                </form>
                
                <div id="processingStatus" class="alert alert-info processing-status">
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                        <span id="statusText">Processing your document...</span>
                    </div>
                    <div class="progress mt-2" style="height: 5px;">
                        <div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated" style="width: 0%"></div>
                    </div>
                </div>
                
                <div id="loader" class="loader"></div>
                
                <div id="results" class="result-box" style="display: none;">
                    <h5>Extracted Data:</h5>
                    <table class="table table-bordered">
                        <tbody id="dataTable">
                            <!-- Data will be inserted here -->
                        </tbody>
                    </table>
                    
                    <div class="mt-4">
                        <h5>Raw Text:</h5>
                        <pre id="rawText" style="max-height: 200px; overflow-y: auto;"></pre>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="api-settings mt-4">
            <h5>Alchemy API Settings</h5>
            <div class="mb-3">
                <label for="apiKey" class="form-label">API Key</label>
                <input type="password" class="form-control" id="apiKey">
            </div>
            <div class="mb-3">
                <label for="apiUrl" class="form-label">API URL</label>
                <input type="text" class="form-control" id="apiUrl">
            </div>
            <button id="sendToAlchemy" class="btn btn-success" disabled>Send to Alchemy</button>
            
            <div id="apiResponse" class="mt-3" style="display: none;">
                <h5>API Response:</h5>
                <pre id="responseText"></pre>
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const uploadForm = document.getElementById('uploadForm');
            const loader = document.getElementById('loader');
            const results = document.getElementById('results');
            const dataTable = document.getElementById('dataTable');
            const rawText = document.getElementById('rawText');
            const sendToAlchemy = document.getElementById('sendToAlchemy');
            const apiKey = document.getElementById('apiKey');
            const apiUrl = document.getElementById('apiUrl');
            const apiResponse = document.getElementById('apiResponse');
            const responseText = document.getElementById('responseText');
            const processingStatus = document.getElementById('processingStatus');
            const statusText = document.getElementById('statusText');
            const progressBar = document.getElementById('progressBar');
            
            // Load saved API settings from localStorage
            apiKey.value = localStorage.getItem('alchemyApiKey') || '';
            apiUrl.value = localStorage.getItem('alchemyApiUrl') || '';
            
            // Save API settings to localStorage when changed
            apiKey.addEventListener('change', () => {
                localStorage.setItem('alchemyApiKey', apiKey.value);
            });
            
            apiUrl.addEventListener('change', () => {
                localStorage.setItem('alchemyApiUrl', apiUrl.value);
            });
            
            let extractedData = null;
            let processingTimeout;
            
            uploadForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const fileInput = document.getElementById('file');
                const file = fileInput.files[0];
                
                if (!file) {
                    alert('Please select a file');
                    return;
                }
                
                // Clear previous results
                dataTable.innerHTML = '';
                rawText.textContent = '';
                results.style.display = 'none';
                sendToAlchemy.disabled = true;
                extractedData = null;
                
                // Show processing status
                processingStatus.style.display = 'block';
                statusText.textContent = 'Uploading document...';
                progressBar.style.width = '10%';
                
                // Clear any existing timeout
                if (processingTimeout) clearTimeout(processingTimeout);
                
                // Set up simulated progress for user feedback
                let progress = 10;
                const progressInterval = setInterval(() => {
                    if (progress < 90) {
                        progress += Math.random() * 10;
                        progressBar.style.width = `${progress}%`;
                        
                        // Update status text based on progress
                        if (progress > 20 && progress < 40) {
                            statusText.textContent = 'Processing document...';
                        } else if (progress > 40 && progress < 60) {
                            statusText.textContent = 'Extracting text with OCR...';
                        } else if (progress > 60 && progress < 80) {
                            statusText.textContent = 'Analyzing data...';
                        }
                    }
                }, 2000);
                
                // Set timeout to show warning after 30 seconds
                processingTimeout = setTimeout(() => {
                    statusText.textContent = 'Still processing... PDF files may take longer';
                }, 30000);
                
                const formData = new FormData();
                formData.append('file', file);
                
                fetch('/extract', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    // Clear intervals and timeouts
                    clearInterval(progressInterval);
                    if (processingTimeout) clearTimeout(processingTimeout);
                    
                    // Hide processing indicators
                    processingStatus.style.display = 'none';
                    
                    if (data.error) {
                        alert('Error: ' + data.error);
                        return;
                    }
                    
                    // Save extracted data
                    extractedData = data;
                    
                    // Display results
                    results.style.display = 'block';
                    
                    // Display extracted data in table
                    for (const [key, value] of Object.entries(data)) {
                        if (key !== 'full_text') {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td><strong>${key.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}</strong></td>
                                <td>${value}</td>
                            `;
                            dataTable.appendChild(row);
                        }
                    }
                    
                    // Display raw text
                    rawText.textContent = data.full_text;
                    
                    // Enable send to Alchemy button if purity was found
                    if (data.purity && data.purity !== 'Not found') {
                        sendToAlchemy.disabled = false;
                    }
                })
                .catch(error => {
                    // Clear intervals and timeouts
                    clearInterval(progressInterval);
                    if (processingTimeout) clearTimeout(processingTimeout);
                    
                    // Hide processing indicators
                    processingStatus.style.display = 'none';
                    
                    console.error('Error:', error);
                    alert('Error processing file. If you uploaded a PDF, it may be too large or complex. Try again with a smaller file or an image instead.');
                });
            });
            
            sendToAlchemy.addEventListener('click', function() {
                if (!extractedData || !apiKey.value || !apiUrl.value) {
                    alert('Missing data or API settings');
                    return;
                }
                
                // Show processing status
                processingStatus.style.display = 'block';
                statusText.textContent = 'Sending data to Alchemy...';
                progressBar.style.width = '50%';
                
                // Prepare data for Alchemy
                const payload = {
                    purity: extractedData.purity,
                    product_name: extractedData.product_name || '',
                    lot_number: extractedData.lot_number || '',
                    cas_number: extractedData.cas_number || '',
                    date_of_analysis: extractedData.date_of_analysis || '',
                    // Add more fields as needed
                };
                
                fetch(apiUrl.value, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${apiKey.value}`
                    },
                    body: JSON.stringify(payload)
                })
                .then(response => response.json())
                .then(data => {
                    // Hide processing status
                    processingStatus.style.display = 'none';
                    
                    // Show API response
                    apiResponse.style.display = 'block';
                    responseText.textContent = JSON.stringify(data, null, 2);
                })
                .catch(error => {
                    processingStatus.style.display = 'none';
                    console.error('Error:', error);
                    apiResponse.style.display = 'block';
                    responseText.textContent = `Error: ${error.message}`;
                });
            });
        });
    </script>
</body>
</html>
'''

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/extract', methods=['POST'])
def extract():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    # If the user does not select a file, the browser submits an empty file
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        try:
            # Start timing
            start_time = time.time()
            logging.info(f"Starting processing for {filename}")
            
            # Save the file temporarily
            file.save(filepath)
            logging.info(f"File saved at {filepath}")
            
            # Process with OCR - handle different file types
            if filepath.lower().endswith('.pdf'):
                logging.info("Processing PDF file")
                # For PDFs, use pdf2image to convert to images first
                
                # Convert PDF to images with optimized settings
                logging.info("Converting PDF to images")
                images = convert_from_path(
                    filepath,
                    dpi=150,  # Lower DPI for faster processing 
                    first_page=1,
                    last_page=3,  # Only process up to 3 pages
                    thread_count=2  # Use parallel processing
                )
                logging.info(f"Converted PDF to {len(images)} images in {time.time() - start_time:.2f} seconds")
                
                # OCR the pages
                text = ""
                for i, img in enumerate(images):
                    page_start = time.time()
                    logging.info(f"Processing page {i+1}")
                    
                    # Extract text from the image directly without saving
                    page_text = pytesseract.image_to_string(img)
                    text += f"\n\n----- PAGE {i+1} -----\n\n{page_text}"
                    
                    logging.info(f"Page {i+1} processed in {time.time() - page_start:.2f} seconds")
            else:
                # For image files, process directly
                logging.info("Processing image file")
                img = Image.open(filepath)
                text = pytesseract.image_to_string(img)
                logging.info(f"Image processed in {time.time() - start_time:.2f} seconds")
            
            # Clean up the file
            os.remove(filepath)
            
            # Parse data with regex
            parsing_start = time.time()
            logging.info("Parsing extracted text")
            data = parse_coa_data(text)
            logging.info(f"Parsing completed in {time.time() - parsing_start:.2f} seconds")
            
            # Add the full text
            data['full_text'] = text
            
            total_time = time.time() - start_time
            logging.info(f"Total processing time: {total_time:.2f} seconds")
            
            return jsonify(data)
            
        except Exception as e:
            logging.error(f"Error processing file: {e}")
            # Clean up the file in case of error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "File type not allowed"}), 400

@app.route('/send-to-alchemy', methods=['POST'])
def send_to_alchemy():
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Get API key and URL from request or environment variables
    api_key = data.get('api_key') or ALCHEMY_API_KEY
    api_url = data.get('api_url') or ALCHEMY_API_URL
    
    if not api_key or not api_url:
        return jsonify({"error": "Missing API credentials"}), 400
    
    try:
        # Prepare payload for Alchemy
        payload = data.get('data', {})
        
        # Send to Alchemy API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        return jsonify(response.json())
    except Exception as e:
        logging.error(f"Error sending to Alchemy: {e}")
        return jsonify({"error": str(e)}), 500

def parse_coa_data(text):
    """Parse COA data from text"""
    data = {}
    
    # Define regex patterns for key fields
    patterns = {
        "product_name": r"(?:BENZENE|TOLUENE|XYLENE|ETHYLBENZENE|METHANOL|ETHANOL|ACETONE|CHLOROFORM|[A-Z]{3,})",
        "purity": r"(?:Certified\s+purity|Det\.\s+Purity):\s*([\d\.]+\s*[±\+\-]\s*[\d\.]+\s*%)",
        "lot_number": r"Lot\s+(?:number|No\.?):\s*([A-Za-z0-9\-\/]+)",
        "cas_number": r"CAS\s+No\.?:\s*\[?([0-9\-]+)",
        "date_of_analysis": r"Date\s+of\s+Analysis:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        "expiry_date": r"Expiry\s+Date:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        "formula": r"Formula:\s*([A-Za-z0-9]+)",
        "molecular_weight": r"Mol\.\s+Weight:\s*([\d\.]+)",
    }
    
    # Extract data using patterns
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match and key != "product_name":
            data[key] = match.group(1).strip()
        elif match:
            data[key] = match.group(0).strip()
    
    return data

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
