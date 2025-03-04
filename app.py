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
                    </div>
                    <button type="submit" class="btn btn-primary">Extract Data</button>
                </form>
                
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
                
                // Show loader
                loader.style.display = 'block';
                
                const formData = new FormData();
                formData.append('file', file);
                
                fetch('/extract', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    // Hide loader
                    loader.style.display = 'none';
                    
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
                                <td><strong>${key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</strong></td>
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
                    loader.style.display = 'none';
                    console.error('Error:', error);
                    alert('Error processing file');
                });
            });
            
            sendToAlchemy.addEventListener('click', function() {
                if (!extractedData || !apiKey.value || !apiUrl.value) {
                    alert('Missing data or API settings');
                    return;
                }
                
                // Show loader
                loader.style.display = 'block';
                
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
                    // Hide loader
                    loader.style.display = 'none';
                    
                    // Show API response
                    apiResponse.style.display = 'block';
                    responseText.textContent = JSON.stringify(data, null, 2);
                })
                .catch(error => {
                    loader.style.display = 'none';
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
            # Save the file temporarily
            file.save(filepath)
            
            # Process with OCR
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img)
            
            # Clean up the file
            os.remove(filepath)
            
            # Parse data with regex
            data = parse_coa_data(text)
            
            # Add the full text
            data['full_text'] = text
            
            return jsonify(data)
        except Exception as e:
            logging.error(f"Error processing file: {e}")
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
