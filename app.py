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
    
    # Preprocess text for better table handling
    preprocessed_text = preprocess_text_for_tables(text)
    
    # Determine document type first
    if re.search(r"Technical\s+Data\s+Sheet", preprocessed_text, re.IGNORECASE):
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
            match = re.search(pattern, preprocessed_text, re.IGNORECASE)
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
            # Look for specific chemical names
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
            match = re.search(pattern, preprocessed_text, re.IGNORECASE)
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
                match = re.search(pattern, preprocessed_text, re.IGNORECASE)
                if match:
                    data["purity"] = match.group(1).strip()
                    break
        
        # Extract data from tables - look for test/result pairs
        test_result_pattern = r"(?:Test|Parameter)(?:\s+Method)?(?:\s+Units)?(?:\s+(?:Specification|Limits))?\s+Results"
        if re.search(test_result_pattern, preprocessed_text, re.IGNORECASE):
            # Find table rows by looking for test names followed by results
            table_rows = re.findall(r"([A-Za-z][A-Za-z\s\(\)\-\@]+)(?:(?:\s+[A-Z]+\s+[A-Z]\s+\d+)|(?:\s+Visual)|(?:\s+[A-Za-z\s]+))(?:\s+[a-z/]+)?(?:\s+[\d\.\-]+)?(?:\s+[\d\.\-]+)?\s+((?:[\d\.]+|(?:Colorless,\s+Clear\s+liquid)|(?:\d+\.\d+\s*[A-Z]+))(?:\s+[A-Za-z\s,]+)?)", preprocessed_text)
            
            for test, result in table_rows:
                test_name = test.strip().lower().replace(" ", "_")
                data[test_name] = result.strip()
    
    # Fallback for product name extraction if not found with specific patterns
    if "product_name" not in data or not data["product_name"] or data["product_name"].lower() == "page":
        # Specifically look for BENZENE in the document
        benzene_match = re.search(r"BENZENE", preprocessed_text, re.IGNORECASE)
        if benzene_match:
            data["product_name"] = "BENZENE"
        else:
            # Try to find a proper product name in the document
            product_line_pattern = r"Reference\s+Material\s+No\.[^\n]+\n+([A-Z]+)"
            match = re.search(product_line_pattern, preprocessed_text, re.IGNORECASE)
            if match:
                data["product_name"] = match.group(1).strip()
            else:
                # Look for any capitalized text that might be a product name
                lines = preprocessed_text.split('\n')
                for line in lines:
                    if re.match(r"^[A-Z]{3,}$", line.strip()):
                        data["product_name"] = line.strip()
                        break
    
    # Additional cleanup for CAS number - make sure it's complete
    if "cas_number" in data and len(data["cas_number"]) < 3:
        # Look for a more complete CAS number pattern
        cas_match = re.search(r"CAS[^:]*:\s*(?:\[?)([0-9]{1,3}\-[0-9]{2}\-[0-9])", preprocessed_text, re.IGNORECASE)
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
                    logging.info(f"Successfully extracted text directly from PDF in {time.time() - start
