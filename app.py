from flask import Flask, request, jsonify, render_template_string
import os
import pytesseract
from PIL import Image
import re
import json
import requests
import time
import logging
from werkzeug.utils import secure_filename
import uuid
from pdf2image import convert_from_path
import PyPDF2

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Environment Variables
ALCHEMY_API_URL = os.getenv('ALCHEMY_API_URL', 'https://core-production.alchemy.cloud/core/api/v2/create-record')
ALCHEMY_REFRESH_URL = os.getenv('ALCHEMY_API_REFRESH_URL', 'https://core-production.alchemy.cloud/core/api/v2/refresh-token')

ALCHEMY_BASE_URL = os.getenv('ALCHEMY_BASE_URL', 'https://app.alchemy.cloud/productcaseelnlims4uat/record/')

# Token Cache
TOKEN_CACHE = {"access_token": None, "expires_at": 0}

# Utility Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_access_token():
    """Retrieve the access token, refreshing it if expired."""
    global TOKEN_CACHE

    if TOKEN_CACHE["access_token"] and time.time() < TOKEN_CACHE["expires_at"]:
        return TOKEN_CACHE["access_token"]

    logging.info("Refreshing API token...")
    response = requests.post(
        ALCHEMY_REFRESH_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": ALCHEMY_CLIENT_ID,
            "client_secret": ALCHEMY_CLIENT_SECRET
        }
    )

    if response.status_code == 200:
        data = response.json()
        TOKEN_CACHE["access_token"] = data["access_token"]
        TOKEN_CACHE["expires_at"] = time.time() + data["expires_in"] - 60  # Refresh 1 minute before expiry
        logging.info("Token refreshed successfully.")
        return TOKEN_CACHE["access_token"]
    else:
        logging.error(f"Failed to refresh token: {response.text}")
        raise Exception("Failed to obtain access token")

def extract_text_from_pdf(pdf_path):
    """Extract text directly from a text-based PDF."""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(min(2, len(reader.pages))):
                text += reader.pages[page_num].extract_text() or ""
        return text if len(text.strip()) > 50 else None
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        return None

def extract_text_with_ocr(image_path):
    """Extract text using OCR."""
    return pytesseract.image_to_string(Image.open(image_path))

def parse_coa_data(text):
    """Parse key fields from extracted text."""
    data = {"document_type": "Certificate of Analysis"}
    patterns = {
        "product_name": r"(?:BENZENE|TOLUENE|XYLENE|ETHYLBENZENE|METHANOL|ETHANOL|ACETONE|CHLOROFORM)",
        "purity": r"(?:Certified\s+purity|Purity):\s*([\d\.]+\s*[±\+\-]\s*[\d\.]+\s*%)",
        "lot_number": r"Lot\s+(?:number|No\.?):\s*([A-Za-z0-9\-\/]+)",
        "cas_number": r"CAS\s+No\.?:\s*(?:\[?)([0-9\-]+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data[key] = match.group(1).strip() if match.groups() else match.group(0).strip()
    
    data["full_text"] = text
    return data

@app.route('/')
def index():
    return "COA OCR Extractor API"

@app.route('/extract', methods=['POST'])
def extract():
    """Extract text from uploaded image/PDF and parse COA data."""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}_{filename}")

    try:
        file.save(filepath)
        text = extract_text_from_pdf(filepath) if filename.lower().endswith('.pdf') else extract_text_with_ocr(filepath)
        if not text:
            return jsonify({"error": "Failed to extract text"}), 500
        
        data = parse_coa_data(text)
        os.remove(filepath)  # Cleanup temp file

        return jsonify(data)
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/send-to-alchemy', methods=['POST'])
def send_to_alchemy():
    """Send extracted data to Alchemy with token management."""
    request_data = request.json
    if not request_data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    try:
        access_token = get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = [
            {
                "processId": None,
                "recordTemplate": "exampleParsing",
                "properties": [
                    {"identifier": "RecordName", "rows": [{"row": 0, "values": [{"value": request_data.get('product_name', "Unknown")}] }]},
                    {"identifier": "CasNumber", "rows": [{"row": 0, "values": [{"value": request_data.get('cas_number', "")}] }]},
                    {"identifier": "Purity", "rows": [{"row": 0, "values": [{"value": request_data.get('purity', "")}] }]},
                    {"identifier": "LotNumber", "rows": [{"row": 0, "values": [{"value": request_data.get('lot_number', "")}] }]},
                ]
            }
        ]

        response = requests.post(ALCHEMY_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        # Extract record ID if available
        record_id = response.json()[0].get("id") if response.json() else None
        record_url = f"{ALCHEMY_BASE_URL.rstrip('/')}/{record_id}" if record_id else None

        return jsonify({
            "status": "success",
            "message": "Data sent successfully",
            "record_id": record_id,
            "record_url": record_url
        })
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending to Alchemy: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
