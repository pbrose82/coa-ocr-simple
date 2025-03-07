from flask import Flask, request, jsonify, render_template, send_from_directory
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

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# Configuration
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Alchemy API Configuration
ALCHEMY_REFRESH_TOKEN = os.getenv('ALCHEMY_REFRESH_TOKEN')
ALCHEMY_REFRESH_URL = os.getenv('ALCHEMY_REFRESH_URL', 'https://core-production.alchemy.cloud/core/api/v2/refresh-token')
ALCHEMY_API_URL = os.getenv('ALCHEMY_API_URL', 'https://core-production.alchemy.cloud/core/api/v2/create-record')
ALCHEMY_BASE_URL = os.getenv('ALCHEMY_BASE_URL', 'https://app.alchemy.cloud/productcaseelnlims4uat/record/')
ALCHEMY_TENANT_NAME = os.getenv('ALCHEMY_TENANT_NAME', 'productcaseelnlims4uat')

# Token cache with expiration
alchemy_token_cache = {
    "access_token": None,
    "expires_at": 0  # Unix timestamp when the token expires
}

@app.route('/')
def index():
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def refresh_alchemy_token():
    """
    Refresh the Alchemy API token using the refresh token.
    Returns the access token for the specified tenant.
    """
    global alchemy_token_cache
    
    # Check if we have a cached token that's still valid (with 5 min buffer)
    current_time = time.time()
    if (alchemy_token_cache["access_token"] and 
        alchemy_token_cache["expires_at"] > current_time + 300):
        logging.info("Using cached Alchemy token")
        return alchemy_token_cache["access_token"]
    
    if not ALCHEMY_REFRESH_TOKEN:
        logging.error("Missing ALCHEMY_REFRESH_TOKEN environment variable")
        return None
    
    try:
        logging.info("Refreshing Alchemy API token")
        response = requests.put(
            ALCHEMY_REFRESH_URL, 
            json={"refreshToken": ALCHEMY_REFRESH_TOKEN},
            headers={"Content-Type": "application/json"}
        )
        
        if not response.ok:
            logging.error(f"Failed to refresh token. Status: {response.status_code}, Response: {response.text}")
            return None
        
        data = response.json()
        
        # Find token for the specified tenant
        tenant_token = next((token for token in data.get("tokens", []) 
                            if token.get("tenant") == ALCHEMY_TENANT_NAME), None)
        
        if not tenant_token:
            logging.error(f"Tenant '{ALCHEMY_TENANT_NAME}' not found in refresh response")
            return None
        
        # Cache the token with expiration time (default to 1 hour if not provided)
        access_token = tenant_token.get("accessToken")
        expires_in = tenant_token.get("expiresIn", 3600)
        
        alchemy_token_cache = {
            "access_token": access_token,
            "expires_at": current_time + expires_in
        }
        
        logging.info(f"Successfully refreshed Alchemy token, expires in {expires_in} seconds")
        return access_token
        
    except Exception as e:
        logging.error(f"Error refreshing Alchemy token: {str(e)}")
        return None

def preprocess_text_for_tables(text):
    """Preprocess text to better handle table structures"""
    # Replace multiple spaces with single tabs in table-like areas
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        # Check if line looks like it could be part of a table (has multiple spaces)
        if re.search(r"\s{3,}", line):
            # Replace groups of spaces with tabs
            processed_line = re.sub(r"\s{3,}", "\t", line)
            processed_lines.append(processed_line)
        else:
            processed_lines.append(line)
    
    return "\n".join(processed_lines)

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
    
    # If purity is a dictionary (from complex parsing)
    if isinstance(purity_string, dict):
        # Prefer base_purity if available
        if 'base_purity' in purity_string:
            # Remove % and any whitespace, convert to string
            return str(purity_string['base_purity']).replace('%', '').strip()
        # If no base_purity, try to extract first numeric value
        for value in purity_string.values():
            if isinstance(value, (int, float, str)):
                # Convert to string, remove %, strip whitespace
                return str(value).replace('%', '').strip()
        # Fallback
        return str(purity_string)
    
    # If it's a string
    if isinstance(purity_string, str):
        # Remove % sign and extra whitespace
        purity_string = purity_string.replace('%', '').strip()
        
        # Try to extract the first numeric value
        parts = purity_string.split()
        for part in parts:
            try:
                # Convert to float to ensure it's a number
                float(part)
                return part
            except ValueError:
                continue
    
    # Fallback - convert to string and strip
    return str(purity_string).replace('%', '').strip()

def parse_coa_data(text):
    """Parse data from text for both COAs and technical data sheets"""
    data = {}
    
    # Preprocess text for better table handling
    preprocessed_text = preprocess_text_for_tables(text)
    
    # Generic patterns for extraction
    generic_patterns = {
        # Product identification patterns
        "product_number": r"Product\s+Number:\s*([A-Za-z0-9\-]+)",
        "batch_number": r"Batch\s+Number:\s*([A-Za-z0-9\-]+)",
        "brand": r"Brand:\s*([A-Za-z\s\-]+)",
        
        # Chemical identification patterns
        "cas_number": r"CAS\s+Number:\s*([0-9\-]+)",
        "formula": r"Formula:\s*([A-Z0-9]+)",
        "molecular_weight": r"Formula\s+Weight:\s*([\d\.]+)\s*g/mol",
        
        # Date patterns
        "quality_release_date": r"Quality\s+Release\s+Date:\s*(\d{1,2}\s+[A-Z]{3}\s+\d{4})",
        
        # Purity patterns
        "purity": [
            r"Purity\s*(?:[\d\.]+%?)\s*Guaranteed\s+By\s+Supplier",
            r"Purity\s*:\s*([\d\.]+\s*%)",
            r"(?:Certified\s+)?Purity\s*:\s*([\d\.]+\s*%)"
        ]
    }
    
    # Extract data using generic patterns
    for key, pattern in generic_patterns.items():
        # Handle purity separately as it might be a list of patterns
        if key == "purity":
            for purity_pattern in pattern:
                match = re.search(purity_pattern, preprocessed_text, re.IGNORECASE)
                if match:
                    # If match has groups, use the first group, otherwise use the whole match
                    data[key] = match.group(1).strip() if match.groups() else match.group(0).strip()
                    break
            continue
        
        # For other patterns
        match = re.search(pattern, preprocessed_text, re.IGNORECASE)
        if match:
            # If match has groups, use the first group, otherwise use the whole match
            data[key] = match.group(1).strip() if match.groups() else match.group(0).strip()
    
    # Determine document type
    data["document_type"] = "Certificate of Analysis"
    
    # Try to extract product name
    product_name_patterns = [
        r"Product\s+Name:\s*([A-Za-z\s\-]+)",
        r"Certificate\s+of\s+Analysis\s+for\s+([A-Za-z\s\-]+)"
    ]
    
    for pattern in product_name_patterns:
        match = re.search(pattern, preprocessed_text, re.IGNORECASE)
        if match:
            data["product_name"] = match.group(1).strip()
            break
    
    # Fallback product name extraction
    if "product_name" not in data:
        # Try to use batch number or product number
        data["product_name"] = data.get("batch_number", data.get("product_number", "Unknown Product"))
    
    # Extract test results if possible
    test_result_pattern = r"((?:Test|Specification)\s*)(.*?)(Result)"
    test_results = re.findall(test_result_pattern, preprocessed_text, re.DOTALL | re.IGNORECASE)
    
    if test_results:
        test_details = {}
        for test_result in test_results:
            test_name = test_result[0].strip().lower().replace(" ", "_")
            test_value = test_result[1].strip()
            test_details[test_name] = test_value
        
        # If test details found, add to data
        if test_details:
            data["test_results"] = test_details
    
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
    
    try:
        # Extract the data received from the client
        extracted_data = data.get('data', {})

            
