# Import Section
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

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Flask Application Setup
app = Flask(__name__, static_folder='static', template_folder='templates')

# Configuration Constants
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Alchemy API Configuration
ALCHEMY_REFRESH_TOKEN = os.getenv('ALCHEMY_REFRESH_TOKEN')
ALCHEMY_REFRESH_URL = os.getenv('ALCHEMY_REFRESH_URL', 'https://core-production.alchemy.cloud/core/api/v2/refresh-token')
ALCHEMY_API_URL = os.getenv('ALCHEMY_API_URL', 'https://core-production.alchemy.cloud/core/api/v2/create-record')
ALCHEMY_BASE_URL = os.getenv('ALCHEMY_BASE_URL', 'https://app.alchemy.cloud/productcaseelnlims4uat/record/')
ALCHEMY_TENANT_NAME = os.getenv('ALCHEMY_TENANT_NAME', 'productcaseelnlims4uat')

# Global Token Cache
alchemy_token_cache = {
    "access_token": None,
    "expires_at": 0  # Unix timestamp when the token expires
}

# Route Handlers
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# Utility Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_text_for_tables(text):
    """Preprocess text to better handle table structures"""
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        if re.search(r"\s{3,}", line):
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
        
        return text if len(text.strip()) > 100 else None
    except Exception as e:
        logging.error(f"Error extracting text directly from PDF: {e}")
        return None

def format_purity_value(purity_string):
    """Extract and format the purity value for Alchemy API"""
    if not purity_string:
        return ""
    
    # If purity is a dictionary
    if isinstance(purity_string, dict):
        if 'base_purity' in purity_string:
            return str(purity_string['base_purity']).replace('%', '').strip()
        
        for value in purity_string.values():
            if isinstance(value, (int, float, str)):
                return str(value).replace('%', '').strip()
        
        return str(purity_string)
    
    # If it's a string
    if isinstance(purity_string, str):
        purity_string = purity_string.replace('%', '').strip()
        
        parts = purity_string.split()
        for part in parts:
            try:
                float(part)
                return part
            except ValueError:
                continue
    
    return str(purity_string).replace('%', '').strip()

def parse_coa_data(text):
    """Parse data from text for both COAs and technical data sheets"""
    data = {}
    
    # Preprocess text for better table handling
    preprocessed_text = preprocess_text_for_tables(text)
    
    # Generic patterns for extraction
    generic_patterns = {
        "product_number": r"Product\s+Number:\s*([A-Za-z0-9\-]+)",
        "batch_number": r"Batch\s+Number:\s*([A-Za-z0-9\-]+)",
        "brand": r"Brand:\s*([A-Za-z\s\-]+)",
        "cas_number": r"CAS\s+Number:\s*([0-9\-]+)",
        "formula": r"Formula:\s*([A-Z0-9]+)",
        "molecular_weight": r"Formula\s+Weight:\s*([\d\.]+)\s*g/mol",
        "quality_release_date": r"Quality\s+Release\s+Date:\s*(\d{1,2}\s+[A-Z]{3}\s+\d{4})",
        "purity": [
            r"Purity\s*(?:[\d\.]+%?)\s*Guaranteed\s+By\s+Supplier",
            r"Purity\s*:\s*([\d\.]+\s*%)",
            r"(?:Certified\s+)?Purity\s*:\s*([\d\.]+\s*%)"
        ]
    }
    
    # Extract data using patterns
    for key, pattern in generic_patterns.items():
        if key == "purity":
            for purity_pattern in pattern:
                match = re.search(purity_pattern, preprocessed_text, re.IGNORECASE)
                if match:
                    data[key] = match.group(1).strip() if match.groups() else match.group(0).strip()
                    break
            continue
        
        match = re.search(pattern, preprocessed_text, re.IGNORECASE)
        if match:
            data[key] = match.group(1).strip() if match.groups() else match.group(0).strip()
    
    # Document type
    data["document_type"] = "Certificate of Analysis"
    
    # Product name extraction
    product_name_patterns = [
        r"Product\s+Name:\s*([A-Za-z\s\-]+)",
        r"Certificate\s+of\s+Analysis\s+for\s+([A-Za-z\s\-]+)"
    ]
    
    for pattern in product_name_patterns:
        match = re.search(pattern, preprocessed_text, re.IGNORECASE)
        if match:
            data["product_name"] = match.group(1).strip()
            break
    
    # Fallback product name
    if "product_name" not in data:
        data["product_name"] = data.get("batch_number", data.get("product_number", "Unknown Product"))
    
    # Test results extraction
    test_result_pattern = r"((?:Test|Specification)\s*)(.*?)(Result)"
    test_results = re.findall(test_result_pattern, preprocessed_text, re.DOTALL | re.IGNORECASE)
    
    if test_results:
        test_details = {}
        for test_result in test_results:
            test_name = test_result[0].strip().lower().replace(" ", "_")
            test_value = test_result[1].strip()
            test_details[test_name] = test_value
        
        if test_details:
            data["test_results"] = test_details
    
    return data

def refresh_alchemy_token():
    """Refresh the Alchemy API token"""
    global alchemy_token_cache
    
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
        
        # Cache the token
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

# Route for File Extraction
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

# Route for Sending Data to Alchemy
@app.route('/send-to-alchemy', methods=['POST'])
def send_to_alchemy():
    data = request.json
    
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    try:
        # Extract the data received from the client
        extracted_data = data.get('data', {})
        
        # Format purity value - extract just the numeric part
        purity_value = format_purity_value(extracted_data.get('purity', ""))
        
        # Get a fresh access token from Alchemy
        access_token = refresh_alchemy_token()
        
        if not access_token:
            return jsonify({
                "status": "error", 
                "message": "Failed to authenticate with Alchemy API"
            }), 500
        
        # Format data for Alchemy API - exactly matching the Postman structure
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
                                        "value": extracted_data.get('hs_code', extracted_data.get('product_number', extracted_data.get('batch_number', ""))),
                                        "valuePreview": ""
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        
        # Continue with the rest of your function here...
        # For example:
        # response = send_to_alchemy_api(alchemy_payload, access_token)
        # return jsonify(response)
        
        # Placeholder return for demonstration
        return jsonify({
            "status": "success",
            "message": "Data formatted for Alchemy",
            "record_id": "12345",
            "record_url": "https://app.alchemy.cloud/records/12345"
        })
        
    except Exception as e:
        print(f"Error sending data to Alchemy: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
        
        # Send to Alchemy API
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        logging.info(f"Sending data to Alchemy: {json.dumps(alchemy_payload)}")
        response = requests.post(ALCHEMY_API_URL, headers=headers, json=alchemy_payload)
        
        # Log response for debugging
        logging.info(f"Alchemy API response status code: {response.status_code}")
        logging.info(f"Alchemy API response: {response.text}")
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Try to extract the record ID from the response
        record_id = None
        record_url = None
        try:
            response_data = response.json()
            # Extract record ID from response - adjust this based on actual response structure
            if isinstance(response_data, list) and len(response_data) > 0:
                if 'id' in response_data[0]:
                    record_id = response_data[0]['id']
                elif 'recordId' in response_data[0]:
                    record_id = response_data[0]['recordId']
            elif isinstance(response_data, dict):
                if 'id' in response_data:
                    record_id = response_data['id']
                elif 'recordId' in response_data:
                    record_id = response_data['recordId']
                elif 'data' in response_data and isinstance(response_data['data'], list) and len(response_data['data']) > 0:
                    if 'id' in response_data['data'][0]:
                        record_id = response_data['data'][0]['id']
                    elif 'recordId' in response_data['data'][0]:
                        record_id = response_data['data'][0]['recordId']
            
            # If record ID was found, construct the URL
            if record_id:
                record_url = f"https://app.alchemy.cloud/productcaseelnlims4uat/record/{record_id}"
                logging.info(f"Created record URL: {record_url}")
            
        except Exception as e:
            logging.warning(f"Could not extract record ID from response: {e}")
        
        # Return success response with record URL if available
        return jsonify({
            "status": "success", 
            "message": "Data successfully sent to Alchemy",
            "response": response.json() if response.text else {"message": "No content in response"},
            "record_id": record_id,
            "record_url": record_url
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

# Main Application Runner
if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)# Import Section
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

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Flask Application Setup
app = Flask(__name__, static_folder='static', template_folder='templates')

# Configuration Constants
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Alchemy API Configuration
ALCHEMY_REFRESH_TOKEN = os.getenv('ALCHEMY_REFRESH_TOKEN')
ALCHEMY_REFRESH_URL = os.getenv('ALCHEMY_REFRESH_URL', 'https://core-production.alchemy.cloud/core/api/v2/refresh-token')
ALCHEMY_API_URL = os.getenv('ALCHEMY_API_URL', 'https://core-production.alchemy.cloud/core/api/v2/create-record')
ALCHEMY_BASE_URL = os.getenv('ALCHEMY_BASE_URL', 'https://app.alchemy.cloud/productcaseelnlims4uat/record/')
ALCHEMY_TENANT_NAME = os.getenv('ALCHEMY_TENANT_NAME', 'productcaseelnlims4uat')

# Global Token Cache
alchemy_token_cache = {
    "access_token": None,
    "expires_at": 0  # Unix timestamp when the token expires
}

# Route Handlers
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# Utility Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_text_for_tables(text):
    """Preprocess text to better handle table structures"""
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        if re.search(r"\s{3,}", line):
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
        
        return text if len(text.strip()) > 100 else None
    except Exception as e:
        logging.error(f"Error extracting text directly from PDF: {e}")
        return None

def format_purity_value(purity_string):
    """Extract and format the purity value for Alchemy API"""
    if not purity_string:
        return ""
    
    # If purity is a dictionary
    if isinstance(purity_string, dict):
        if 'base_purity' in purity_string:
            return str(purity_string['base_purity']).replace('%', '').strip()
        
        for value in purity_string.values():
            if isinstance(value, (int, float, str)):
                return str(value).replace('%', '').strip()
        
        return str(purity_string)
    
    # If it's a string
    if isinstance(purity_string, str):
        purity_string = purity_string.replace('%', '').strip()
        
        parts = purity_string.split()
        for part in parts:
            try:
                float(part)
                return part
            except ValueError:
                continue
    
    return str(purity_string).replace('%', '').strip()

def parse_coa_data(text):
    """Parse data from text for both COAs and technical data sheets"""
    data = {}
    
    # Preprocess text for better table handling
    preprocessed_text = preprocess_text_for_tables(text)
    
    # Generic patterns for extraction
    generic_patterns = {
        "product_number": r"Product\s+Number:\s*([A-Za-z0-9\-]+)",
        "batch_number": r"Batch\s+Number:\s*([A-Za-z0-9\-]+)",
        "brand": r"Brand:\s*([A-Za-z\s\-]+)",
        "cas_number": r"CAS\s+Number:\s*([0-9\-]+)",
        "formula": r"Formula:\s*([A-Z0-9]+)",
        "molecular_weight": r"Formula\s+Weight:\s*([\d\.]+)\s*g/mol",
        "quality_release_date": r"Quality\s+Release\s+Date:\s*(\d{1,2}\s+[A-Z]{3}\s+\d{4})",
        "purity": [
            r"Purity\s*(?:[\d\.]+%?)\s*Guaranteed\s+By\s+Supplier",
            r"Purity\s*:\s*([\d\.]+\s*%)",
            r"(?:Certified\s+)?Purity\s*:\s*([\d\.]+\s*%)"
        ]
    }
    
    # Extract data using patterns
    for key, pattern in generic_patterns.items():
        if key == "purity":
            for purity_pattern in pattern:
                match = re.search(purity_pattern, preprocessed_text, re.IGNORECASE)
                if match:
                    data[key] = match.group(1).strip() if match.groups() else match.group(0).strip()
                    break
            continue
        
        match = re.search(pattern, preprocessed_text, re.IGNORECASE)
        if match:
            data[key] = match.group(1).strip() if match.groups() else match.group(0).strip()
    
    # Document type
    data["document_type"] = "Certificate of Analysis"
    
    # Product name extraction
    product_name_patterns = [
        r"Product\s+Name:\s*([A-Za-z\s\-]+)",
        r"Certificate\s+of\s+Analysis\s+for\s+([A-Za-z\s\-]+)"
    ]
    
    for pattern in product_name_patterns:
        match = re.search(pattern, preprocessed_text, re.IGNORECASE)
        if match:
            data["product_name"] = match.group(1).strip()
            break
    
    # Fallback product name
    if "product_name" not in data:
        data["product_name"] = data.get("batch_number", data.get("product_number", "Unknown Product"))
    
    # Test results extraction
    test_result_pattern = r"((?:Test|Specification)\s*)(.*?)(Result)"
    test_results = re.findall(test_result_pattern, preprocessed_text, re.DOTALL | re.IGNORECASE)
    
    if test_results:
        test_details = {}
        for test_result in test_results:
            test_name = test_result[0].strip().lower().replace(" ", "_")
            test_value = test_result[1].strip()
            test_details[test_name] = test_value
        
        if test_details:
            data["test_results"] = test_details
    
    return data

def refresh_alchemy_token():
    """Refresh the Alchemy API token"""
    global alchemy_token_cache
    
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
        
        # Cache the token
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

# Route for File Extraction
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

# Route for Sending Data to Alchemy
@app.route('/send-to-alchemy', methods=['POST'])
def send_to_alchemy():
    data = request.json
    
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    try:
        # Extract the data received from the client
        extracted_data = data.get('data', {})
        
        # Format purity value - extract just the numeric part
        purity_value = format_purity_value(extracted_data.get('purity', ""))
        
        # Get a fresh access token from Alchemy
        access_token = refresh_alchemy_token()
        
        if not access_token:
            return jsonify({
                "status": "error", 
                "message": "Failed to authenticate with Alchemy API"
            }), 500
        
        # Format data for Alchemy API - exactly matching the Postman structure
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
                                        "value": extracted_data.get('hs_code', extracted_data.get('product_number', extracted_data.get('batch_number', ""))),
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
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        logging.info(f"Sending data to Alchemy: {json.dumps(alchemy_payload)}")
        response = requests.post(ALCHEMY_API_URL, headers=headers, json=alchemy_payload)
        
        # Log response for debugging
        logging.info(f"Alchemy API response status code: {response.status_code}")
        logging.info(f"Alchemy API response: {response.text}")
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Try to extract the record ID from the response
        record_id = None
        record_url = None
        try:
            response_data = response.json()
            # Extract record ID from response - adjust this based on actual response structure
            if isinstance(response_data, list) and len(response_data) > 0:
                if 'id' in response_data[0]:
                    record_id = response_data[0]['id']
                elif 'recordId' in response_data[0]:
                    record_id = response_data[0]['recordId']
            elif isinstance(response_data, dict):
                if 'id' in response_data:
                    record_id = response_data['id']
                elif 'recordId' in response_data:
                    record_id = response_data['recordId']
                elif 'data' in response_data and isinstance(response_data['data'], list) and len(response_data['data']) > 0:
                    if 'id' in response_data['data'][0]:
                        record_id = response_data['data'][0]['id']
                    elif 'recordId' in response_data['data'][0]:
                        record_id = response_data['data'][0]['recordId']
            
            # If record ID was found, construct the URL
            if record_id:
                record_url = f"https://app.alchemy.cloud/productcaseelnlims4uat/record/{record_id}"
                logging.info(f"Created record URL: {record_url}")
            
        except Exception as e:
            logging.warning(f"Could not extract record ID from response: {e}")
        
        # Return success response with record URL if available
        return jsonify({
            "status": "success", 
            "message": "Data successfully sent to Alchemy",
            "response": response.json() if response.text else {"message": "No content in response"},
            "record_id": record_id,
            "record_url": record_url
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

# Main Application Runner
if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
