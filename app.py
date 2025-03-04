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
import PyPDF2

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff'}
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')
ALCHEMY_API_URL = os.getenv('ALCHEMY_API_URL', 'https://core-production.alchemy.cloud/core/api/v2/create-record')

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
        .file-type-toggle {
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-center mb-4">COA OCR to Alchemy</h1>
        
        <div class="alert alert-info">
            <strong>Tips for best results:</strong>
            <ul class="mb-0">
                <li>Image files (JPG, PNG) process faster than PDFs</li>
                <li>PDFs with embedded text work best</li>
                <li>Use clear, high-resolution images of your COA documents</li>
            </ul>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">Upload COA Document</h5>
            </div>
            <div class="card-body">
                <div class="file-type-toggle">
                    <div class="form-check form-check-inline">
                        <input class="form-check-input" type="radio" name="fileTypeOptions" id="imageOption" value="image" checked>
                        <label class="form-check-label" for="imageOption">Image (faster)</label>
                    </div>
                    <div class="form-check form-check-inline">
                        <input class="form-check-input" type="radio" name="fileTypeOptions" id="pdfOption" value="pdf">
                        <label class="form-check-label" for="pdfOption">PDF</label>
                    </div>
                </div>
                
                <form id="uploadForm" enctype="multipart/form-data" class="mb-3">
                    <div class="mb-3">
                        <label for="file" class="form-label">Select COA file</label>
                        <input class="form-control" type="file" id="file" name="file" accept=".jpg,.jpeg,.png,.pdf,.tiff">
                        <div class="form-text text-muted" id="fileTypeHelp">
                            Images process faster. Select file type above to change accepted formats.
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
                
                <div id="alchemyAlerts" class="mt-3" style="display: none;">
                    <div class="alert alert-success" id="successAlert" style="display: none;">
                        Data successfully sent to Alchemy!
                    </div>
                    <div class="alert alert-danger" id="errorAlert" style="display: none;">
                        <span id="errorMessage">Error sending data to Alchemy</span>
                    </div>
                </div>
                
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
                <input type="text" class="form-control" id="apiUrl" value="https://core-production.alchemy.cloud/core/api/v2/create-record">
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
            const fileInput = document.getElementById('file');
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
            const imageOption = document.getElementById('imageOption');
            const pdfOption = document.getElementById('pdfOption');
            const alchemyAlerts = document.getElementById('alchemyAlerts');
            const successAlert = document.getElementById('successAlert');
            const errorAlert = document.getElementById('errorAlert');
            const errorMessage = document.getElementById('errorMessage');
            
            // Load saved API settings from localStorage
            apiKey.value = localStorage.getItem('alchemyApiKey') || '';
            apiUrl.value = localStorage.getItem('alchemyApiUrl') || 'https://core-production.alchemy.cloud/core/api/v2/create-record';
            
            // Save API settings to localStorage when changed
            apiKey.addEventListener('change', () => {
                localStorage.setItem('alchemyApiKey', apiKey.value);
            });
            
            apiUrl.addEventListener('change', () => {
                localStorage.setItem('alchemyApiUrl', apiUrl.value);
            });
            
            // Set file input accept attribute based on file type selection
            imageOption.addEventListener('change', () => {
                if (imageOption.checked) {
                    fileInput.accept = ".jpg,.jpeg,.png,.tiff";
                }
            });
            
            pdfOption.addEventListener('change', () => {
                if (pdfOption.checked) {
                    fileInput.accept = ".pdf";
                }
            });
            
            let extractedData = null;
            let processingTimeout;
            
            uploadForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const file = fileInput.files[0];
                
                if (!file) {
                    alert('Please select a file');
                    return;
                }
                
                // Check if file type matches selected option
                const isPdf = file.name.toLowerCase().endsWith('.pdf');
                const isImage = !isPdf;
                
                if ((imageOption.checked && isPdf) || (pdfOption.checked && isImage)) {
                    const expectedType = imageOption.checked ? "image" : "PDF";
                    alert(`You selected ${expectedType} file type but uploaded a ${isPdf ? "PDF" : "image"} file. Please select the correct file type or change your selection.`);
                    return;
                }
                
                // Clear previous results
                dataTable.innerHTML = '';
                rawText.textContent = '';
                results.style.display = 'none';
                sendToAlchemy.disabled = true;
                apiResponse.style.display = 'none';
                alchemyAlerts.style.display = 'none';
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
                        progress += Math.random() * 5;
                        progressBar.style.width = `${progress}%`;
                        
                        // Update status text based on progress
                        if (progress > 20 && progress < 40) {
                            statusText.textContent = 'Processing document...';
                        } else if (progress > 40 && progress < 60) {
                            statusText.textContent = 'Extracting text...';
                        } else if (progress > 60 && progress < 80) {
                            statusText.textContent = 'Analyzing data...';
                        }
                    }
                }, 1000);
                
                // Set timeout to show warning after 30 seconds
                processingTimeout = setTimeout(() => {
                    statusText.textContent = 'Still processing... Please wait';
                }, 30000);
                
                const formData = new FormData();
                formData.append('file', file);
                
                fetch('/extract', {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    // Clear intervals and timeouts
                    clearInterval(progressInterval);
                    if (processingTimeout) clearTimeout(processingTimeout);
                    
                    // Complete progress bar
                    progressBar.style.width = '100%';
                    statusText.textContent = 'Processing complete!';
                    
                    // Hide processing indicators after a brief delay
                    setTimeout(() => {
                        processingStatus.style.display = 'none';
                    }, 1000);
                    
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
                    
                    // Enable send to Alchemy button if we have data to send
                    if (data.product_name || data.purity) {
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
                    alert('Error processing file. The server might have timed out. For PDFs, try using a smaller file or converting it to an image first.');
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
                
                // Hide previous alerts
                alchemyAlerts.style.display = 'none';
                successAlert.style.display = 'none';
                errorAlert.style.display = 'none';
                
                // Format data for Alchemy's expected structure
                const payload = {
                    data: extractedData,
                    api_key: apiKey.value,
                    api_url: apiUrl.value
                };
                
                fetch('/send-to-alchemy', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
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
                    
                    // Show appropriate alert
                    alchemyAlerts.style.display = 'block';
                    if (data.status === 'success') {
                        successAlert.style.display = 'block';
                        errorAlert.style.display = 'none';
                    } else {
                        successAlert.style.display = 'none';
                        errorAlert.style.display = 'block';
                        errorMessage.textContent = data.message || 'Error sending data to Alchemy';
                    }
                })
                .catch(error => {
                    // Hide processing status
                    processingStatus.style.display = 'none';
                    console.error('Error:', error);
                    
                    // Show error alert
                    alchemyAlerts.style.display = 'block';
                    successAlert.style.display = 'none';
                    errorAlert.style.display = 'block';
                    errorMessage.textContent = error.message || 'Failed to send data to Alchemy';
                    
                    // Show response area with error
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

def extract_text_from_pdf_without_ocr(pdf_path):
    """Try to extract text directly from PDF without OCR"""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(min(2, len(reader.pages))):
                page_text = reader.pages[page_num].extract_text() or ""
                if page_text:
                    text += f"--- Page {page_num+1} ---\n{page_text}\n\n"
        
        # If we got meaningful text (more than just a few characters)
        if len(text.strip()) > 100:
            return text
        return None
    except Exception as e:
        logging.error(f"Error extracting text directly from PDF: {e}")
        return None

def format_purity_value(purity_string):
    """Extract and format the purity value for Alchemy API"""
    if not purity_string:
        return ""
        
    # Remove any % signs
    purity_string = purity_string.replace('%', '').strip()
    
    # Try to extract the first number (e.g., get "99.95" from "99.95 ± 0.02")
    parts = purity_string.split()
    if parts:
        return parts[0].strip()
    
    return purity_string

def parse_coa_data(text):
    """Parse data from text for both COAs and technical data sheets"""
    data = {}
    
    # Determine document type first
    if re.search(r"Technical\s+Data\s+Sheet", text, re.IGNORECASE):
        data["document_type"] = "Technical Data Sheet"
        
        # Technical Data Sheet specific patterns
        tech_patterns = {
            "product_name": r"([A-Za-z®]+\s+TSA\s+Settle)",
            "ordering_number": r"Ordering\s+number:\s*([0-9\.]+)",
            "storage_conditions": r"stored\s+([^\.]+)",
            "shelf_life": r"The\s+product\s+can\s+be\s+used\s+([^\.]+)",
        }
        
        # Extract data using tech sheet patterns
        for key, pattern in tech_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Some patterns capture the whole match, others capture a group
                if key == "product_name" and match.group(1):
                    data[key] = match.group(1).strip()
                elif match.groups() and match.group(1):
                    data[key] = match.group(1).strip()
                else:
                    data[key] = match.group(0).strip()
    else:
        # Default to COA if not explicitly a technical data sheet
        data["document_type"] = "Certificate of Analysis"
        
        # COA specific patterns with improved patterns
        coa_patterns = {
            # Look for BENZENE specifically or other common chemical names
            "product_name": r"(?:BENZENE|TOLUENE|XYLENE|ETHYLBENZENE|METHANOL|ETHANOL|ACETONE|CHLOROFORM)",
            
            # More flexible purity patterns to catch various formats
            "purity": r"(?:Certified\s+purity|Det\.\s+Purity|Purity):\s*([\d\.]+\s*[±\+\-]\s*[\d\.]+\s*%)",
            
            # Improved lot number pattern
            "lot_number": r"Lot\s+(?:number|No\.?):\s*([A-Za-z0-9\-\/]+)",
            
            # Fixed CAS number pattern to capture the full number
            "cas_number": r"CAS\s+No\.?:\s*(?:\[?)([0-9\-]+)",
            
            # Date patterns
            "date_of_analysis": r"Date\s+of\s+Analysis:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
            "expiry_date": r"Expiry\s+Date:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
            
            # Chemical info patterns
            "formula": r"Formula:\s*([A-Za-z0-9]+)",
            "molecular_weight": r"Mol\.\s+Weight:\s*([\d\.]+)",
        }
        
        # Extract data using COA patterns
        for key, pattern in coa_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if key != "product_name" and match.groups():
                    data[key] = match.group(1).strip()
                elif match:
                    data[key] = match.group(0).strip()
        
        # Additional fallback pattern for purity that's more flexible
        if "purity" not in data or not data["purity"]:
            purity_patterns = [
                r"(\d{2,3}\.\d{1,2}\s*[±\+\-]\s*\d{1,2}\.\d{1,2}\s*%)",
                r"Certified\s+puri[^\:]*:\s*([\d\.]+\s*[±\+\-]\s*[\d\.]+\s*[%o])",
                r"purity:\s*([\d\.]+\s*[±\+\-]\s*[\d\.]+\s*%)",
                r"Det\.\s+Purity:\s*([\d\.]+\s*[±\+\-]\s*[\d\.]+\s*%)"
            ]
            
            for pattern in purity_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data["purity"] = match.group(1).strip()
                    break
    
    # Fallback for product name extraction if not found with specific patterns
    if "product_name" not in data or not data["product_name"] or data["product_name"].lower() == "page":
        # Specifically look for BENZENE in the document
        benzene_match = re.search(r"BENZENE", text, re.IGNORECASE)
        if benzene_match:
            data["product_name"] = "BENZENE"
        else:
            # Try to find a proper product name in the document
            product_line_pattern = r"Reference\s+Material\s+No\.[^\n]+\n+([A-Z]+)"
            match = re.search(product_line_pattern, text, re.IGNORECASE)
            if match:
                data["product_name"] = match.group(1).strip()
            else:
                # Look for any capitalized text that might be a product name
                lines = text.split('\n')
                for line in lines:
                    if re.match(r"^[A-Z]{3,}$", line.strip()):
                        data["product_name"] = line.strip()
                        break
    
    # Additional cleanup for CAS number - make sure it's complete
    if "cas_number" in data and len(data["cas_number"]) < 3:
        # Look for a more complete CAS number pattern
        cas_match = re.search(r"CAS[^:]*:\s*(?:\[?)([0-9]{1,3}\-[0-9]{2}\-[0-9])", text, re.IGNORECASE)
        if cas_match:
            data["cas_number"] = cas_match.group(1).strip()
    
    return data

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
            
            # Process based on file type
            if filepath.lower().endswith('.pdf'):
                logging.info("Processing PDF file")
                
                # First try to extract text directly (for text-based PDFs)
                text = extract_text_from_pdf_without_ocr(filepath)
                
                if text:
                    logging.info(f"Successfully extracted text directly from PDF in {time.time() - start_time:.2f} seconds")
                else:
                    logging.info("Direct text extraction failed, falling back to OCR")
                    # Convert PDF to images with highly optimized settings
                    images = convert_from_path(
                        filepath,
                        dpi=100,  # Very low DPI for speed
                        first_page=1,
                        last_page=1,  # Only process first page
                        thread_count=1,  # Single thread to reduce memory
                        grayscale=True  # Grayscale for faster processing
                    )
                    logging.info(f"Converted PDF to {len(images)} images in {time.time() - start_time:.2f} seconds")
                    
                    # OCR the first page only
                    if images:
                        text = pytesseract.image_to_string(images[0])
                        logging.info(f"OCR completed in {time.time() - start_time:.2f} seconds")
                    else:
                        return jsonify({"error": "Failed to extract pages from PDF"}), 500
            else:
                # For image files, process directly
                logging.info("Processing image file")
                img = Image.open(filepath)
                text = pytesseract.image_to_string(img)
                logging.info(f"Image OCR completed in {time.time() - start_time:.2f} seconds")
            
            # Clean up the file
            try:
                os.remove(filepath)
            except Exception as e:
                logging.warning(f"Failed to remove temp file: {e}")
            
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
                try:
                    os.remove(filepath)
                except:
                    pass
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "File type not allowed"}), 400

@app.route('/send-to-alchemy', methods=['POST'])
def send_to_alchemy():
    data = request.json
    
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    # Get API key and URL from request or environment variables
    api_key = data.get('api_key') or ALCHEMY_API_KEY
    api_url = data.get('api_url') or ALCHEMY_API_URL
    
    if not api_key:
        return jsonify({"status": "error", "message": "Missing API key"}), 400
    
    try:
        # Extract the data received from the client
        extracted_data = data.get('data', {})
        
        # Format purity value - extract just the numeric part
        purity_value = format_purity_value(extracted_data.get('purity', ""))
        
        # Format data for Alchemy API according to their expected structure
        alchemy_payload = [
            {
                "processId": None,
                "recordTemplate": "exampleParsing",
                "properties": [
                    {
                        "identifier": "RecordName",
                        "rows": [
                            {
                                "row": 0,
                                "values": [
                                    {
                                        "value": extracted_data.get('product_name', "Unknown Product"),
                                        "valuePreview": ""
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "identifier": "CasNumber",
                        "rows": [
                            {
                                "row": 0,
                                "values": [
                                    {
                                        "value": extracted_data.get('cas_number', ""),
                                        "valuePreview": ""
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "identifier": "Purity",
                        "rows": [
                            {
                                "row": 0,
                                "values": [
                                    {
                                        "value": purity_value,
                                        "valuePreview": ""
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "identifier": "LotNumber",
                        "rows": [
                            {
                                "row": 0,
                                "values": [
                                    {
                                        "value": extracted_data.get('lot_number', ""),
                                        "valuePreview": ""
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        
      # Send to Alchemy API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        logging.info(f"Sending data to Alchemy: {json.dumps(alchemy_payload)}")
        response = requests.post(api_url, headers=headers, json=alchemy_payload)
        
        # Log response for debugging
        logging.info(f"Alchemy API response status code: {response.status_code}")
        logging.info(f"Alchemy API response: {response.text}")
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Return success response
        return jsonify({
            "status": "success", 
            "message": "Data successfully sent to Alchemy",
            "response": response.json() if response.text else {"message": "No content in response"}
        })
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error sending to Alchemy: {e}")
        
        # Try to capture response content if available
        error_response = None
        if hasattr(e, 'response') and e.response:
            try:
                error_response = e.response.json()
            except:
                error_response = {"text": e.response.text}
        
        return jsonify({
            "status": "error", 
            "message": str(e),
            "details": error_response
        }), 500
        
    except Exception as e:
        logging.error(f"Error sending to Alchemy: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
