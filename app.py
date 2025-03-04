from flask import Flask, request, jsonify
import os
import requests
import time
import logging
from werkzeug.utils import secure_filename
import uuid
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import PyPDF2

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Configuration from environment variables
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALCHEMY_REFRESH_URL = os.getenv('ALCHEMY_REFRESH_URL', 'https://core-production.alchemy.cloud/core/api/v2/refresh-token')
ALCHEMY_UPDATE_URL = os.getenv('ALCHEMY_UPDATE_URL', 'https://core-production.alchemy.cloud/core/api/v2/update-record')
ALCHEMY_REFRESH_TOKEN = os.getenv('ALCHEMY_REFRESH_TOKEN')
TENANT_NAME = os.getenv('ALCHEMY_TENANT_NAME', 'productcaseelnlims4uat')

# Token Cache
TOKEN_CACHE = {"access_token": None, "expires_at": 0}

def get_access_token():
    """Retrieve the access token, refreshing it if expired."""
    global TOKEN_CACHE

    if TOKEN_CACHE["access_token"] and time.time() < TOKEN_CACHE["expires_at"]:
        return TOKEN_CACHE["access_token"]

    logging.info("Refreshing Alchemy API token...")
    response = requests.put(ALCHEMY_REFRESH_URL, json={"refreshToken": ALCHEMY_REFRESH_TOKEN})

    if response.status_code == 200:
        data = response.json()
        tenant_token = next((t for t in data["tokens"] if t["tenant"] == TENANT_NAME), None)

        if not tenant_token:
            raise Exception(f"Tenant '{TENANT_NAME}' not found in token response.")

        TOKEN_CACHE["access_token"] = tenant_token["accessToken"]
        TOKEN_CACHE["expires_at"] = time.time() + 3600  # Assuming 1 hour token validity
        logging.info("Token refreshed successfully.")
        return TOKEN_CACHE["access_token"]
    
    logging.error(f"Failed to refresh token: {response.text}")
    raise Exception("Failed to obtain access token")

def extract_text_from_pdf(pdf_path):
    """Extract text directly from a text-based PDF."""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages[:2]:  # Extract only first 2 pages
                text += page.extract_text() or ""
        return text if text.strip() else None
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
        "cas_number": r"CAS\s+No\.?:\s*(?:\[?)([0-9\-]+)"
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

        response = requests.put(ALCHEMY_UPDATE_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        return jsonify({"status": "success", "message": "Alchemy record updated", "data": response.json()})
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending to Alchemy: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
