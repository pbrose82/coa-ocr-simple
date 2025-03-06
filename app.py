import os
import re
import json
import tempfile
import requests
import pytesseract
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
import fitz  # PyMuPDF
from typing import Dict, List, Tuple, Any

app = Flask(__name__)

# Set up Tesseract configuration
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'  # Update this path if needed

# Alchemy API configuration - replace with your actual values
ALCHEMY_CLIENT_ID = os.environ.get('ALCHEMY_CLIENT_ID', 'your_client_id')
ALCHEMY_CLIENT_SECRET = os.environ.get('ALCHEMY_CLIENT_SECRET', 'your_client_secret')
ALCHEMY_API_BASE_URL = os.environ.get('ALCHEMY_API_BASE_URL', 'https://api.alchemy.cloud')

# Function to extract test results from a COA document
def extract_test_results(full_text: str) -> List[Dict[str, str]]:
    """
    Extract test results from a COA document text.
    
    Args:
        full_text: The full text content of the COA document
        
    Returns:
        A list of dictionaries containing test name, specification, and result
    """
    test_results = []
    
    # Find the Test/Specification/Result section - common in COAs
    test_section_pattern = r'(?i)Test\s+Specification\s+Result\s*\n[-_]+.*?\n(.*?)(?:\n\s*(?:Recommended|Version|Page|\Z))'
    match = re.search(test_section_pattern, full_text, re.DOTALL)
    
    if not match:
        # Alternative pattern for different COA formats
        test_section_pattern = r'(?i)(?:Test|Parameter).*?(?:Specification|Limit).*?(?:Result|Value).*?\n[-_]+\n(.*?)(?:\n\s*(?:Recommended|Version|Page|\Z))'
        match = re.search(test_section_pattern, full_text, re.DOTALL)
    
    if match:
        test_section = match.group(1)
        
        # Split the test section into lines
        lines = test_section.strip().split('\n')
        
        current_test = None
        current_spec = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('_') or line.startswith('-'):
                continue
                
            # Try to extract test, specification and result
            # Pattern 1: Test name at beginning of line followed by spec and result
            test_spec_result = re.match(r'^(.*?)\s{2,}([^_]+?)\s{2,}(.+)$', line)
            
            # Pattern 2: Just "< X ppm/%" or similar patterns that continue from previous line
            continuation = re.match(r'^([<≤]\s*[\d.]+\s*(?:ppm|%|ppb|APHA))\s+([<≤]\s*[\d.]+\s*(?:ppm|%|ppb|APHA))$', line)
            
            # Pattern 3: Some COAs have odd formatting with underscores or test names with colons
            special_format = re.match(r'^([^:]+):\s+(.+?)\s{2,}(.+)$', line)
            
            if test_spec_result:
                test_name = test_spec_result.group(1).strip()
                specification = test_spec_result.group(2).strip()
                result = test_spec_result.group(3).strip()
                
                # Skip lines that don't actually contain test data
                if any(skip in test_name.lower() for skip in ['_____', '-----', 'recommended', 'version']):
                    continue
                    
                test_results.append({
                    'test_name': test_name,
                    'specification': specification,
                    'result': result
                })
                
                current_test = test_name
                current_spec = specification
                
            elif continuation and current_test:
                # This is a continuation of the previous test
                specification = continuation.group(1).strip()
                result = continuation.group(2).strip()
                
                test_results.append({
                    'test_name': current_test + ' (continued)',
                    'specification': specification,
                    'result': result
                })
                
            elif special_format:
                test_name = special_format.group(1).strip()
                specification = special_format.group(2).strip()
                result = special_format.group(3).strip()
                
                test_results.append({
                    'test_name': test_name,
                    'specification': specification,
                    'result': result
                })
                
            elif current_test and line:
                # This might be additional information for the current test
                test_results.append({
                    'test_name': current_test + ' - Note',
                    'specification': '',
                    'result': line
                })
    
    return test_results

def format_test_results_for_alchemy(test_results: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Format the extracted test results into Alchemy API format.
    
    Args:
        test_results: List of test result dictionaries
        
    Returns:
        List of properties formatted for Alchemy API
    """
    alchemy_properties = []
    
    for i, test in enumerate(test_results):
        # Create a sanitized identifier from the test name
        identifier = re.sub(r'[^a-zA-Z0-9]', '', test['test_name'])
        if not identifier:
            identifier = f"Test{i+1}"
        
        # Create property for test name
        alchemy_properties.append({
            "identifier": f"{identifier}Name",
            "rows": [
                {
                    "row": 0,
                    "values": [
                        {
                            "value": test['test_name'],
                            "valuePreview": ""
                        }
                    ]
                }
            ]
        })
        
        # Create property for specification
        alchemy_properties.append({
            "identifier": f"{identifier}Specification",
            "rows": [
                {
                    "row": 0,
                    "values": [
                        {
                            "value": test['specification'],
                            "valuePreview": ""
                        }
                    ]
                }
            ]
        })
        
        # Create property for result
        alchemy_properties.append({
            "identifier": f"{identifier}Result",
            "rows": [
                {
                    "row": 0,
                    "values": [
                        {
                            "value": test['result'],
                            "valuePreview": ""
                        }
                    ]
                }
            ]
        })
    
    return alchemy_properties

def format_purity_value(purity_text):
    """Extract just the numeric part of a purity value."""
    if not purity_text:
        return ""
        
    # Try to find a percentage value
    match = re.search(r'(\d+(?:\.\d+)?)\s*%', purity_text)
    if match:
        return match.group(1) + "%"
        
    # Try to find a numeric value followed by units
    match = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)', purity_text)
    if match:
        return match.group(1) + " " + match.group(2)
        
    # Just return the original text if no pattern matches
    return purity_text

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    text = ""
    try:
        # Open the PDF file
        doc = fitz.open(pdf_path)
        
        # Iterate through each page
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
            
        # Close the document
        doc.close()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        # Try OCR as a fallback
        text = extract_text_from_pdf_using_ocr(pdf_path)
        
    return text

def extract_text_from_pdf_using_ocr(pdf_path):
    """Extract text from a PDF file using OCR (for scanned PDFs)."""
    text = ""
    try:
        # Open the PDF file
        doc = fitz.open(pdf_path)
        
        # Use a temporary directory to store image files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Iterate through each page
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Render page to an image
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                img_path = os.path.join(temp_dir, f"page_{page_num}.png")
                pix.save(img_path)
                
                # Use OCR to extract text from the image
                img = Image.open(img_path)
                page_text = pytesseract.image_to_string(img)
                text += page_text + "\n"
                
        # Close the document
        doc.close()
    except Exception as e:
        print(f"Error extracting text from PDF using OCR: {e}")
        
    return text

def extract_text_from_image(image_path):
    """Extract text from an image file using OCR."""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""

def extract_coa_data(text):
    """Extract structured data from COA text."""
    data = {}
    
    # Extract product name
    product_name_patterns = [
        r'Product Name:?\s*(.+?)(?:\n|$)',
        r'(?:Item|Material|Product) (?:Name|Description):?\s*(.+?)(?:\n|$)',
    ]
    
    for pattern in product_name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['product_name'] = match.group(1).strip()
            break
    
    # Extract CAS number
    cas_patterns = [
        r'CAS(?:[ -]*(?:No|Number|#)):?\s*(\d+[-\s]*\d+[-\s]*\d+)',
        r'CAS:?\s*(\d+[-\s]*\d+[-\s]*\d+)',
    ]
    
    for pattern in cas_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Format CAS number consistently
            cas = match.group(1).strip()
            cas = re.sub(r'\s+', '', cas)  # Remove whitespace
            data['cas_number'] = cas
            break
    
    # Extract batch/lot number
    batch_patterns = [
        r'(?:Batch|Lot)(?:[ -]*(?:No|Number|#)):?\s*([A-Z0-9-]+)',
        r'(?:Batch|Lot):?\s*([A-Z0-9-]+)',
    ]
    
    for pattern in batch_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['batch_number'] = match.group(1).strip()
            break
    
    # Extract product number
    product_num_patterns = [
        r'Product (?:No|Number|#):?\s*([A-Z0-9-]+)',
        r'(?:Catalog|Cat|Item|Article)(?:[ -]*(?:No|Number|#)):?\s*([A-Z0-9-]+)',
    ]
    
    for pattern in product_num_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['product_number'] = match.group(1).strip()
            break
    
    # Extract purity
    purity_patterns = [
        r'Purity:?\s*((?:\d+(?:\.\d+)?)\s*%)',
        r'Assay:?\s*((?:\d+(?:\.\d+)?)\s*%)',
        r'Content:?\s*((?:\d+(?:\.\d+)?)\s*%)',
        r'(?:Titration|Titre):?\s*((?:\d+(?:\.\d+)?)\s*%)',
    ]
    
    for pattern in purity_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['purity'] = match.group(1).strip()
            break
    
    # Try to extract purity from the test results section if not found above
    if 'purity' not in data:
        titration_pattern = r'Titration with NaOH.*?(\d+\.\d+\s*%)'
        match = re.search(titration_pattern, text, re.IGNORECASE)
        if match:
            data['purity'] = match.group(1).strip()
    
    # Extract additional identifiers that might be useful (HS Code, etc.)
    hs_code_pattern = r'(?:HS|TARIC|Harmonized|HTS)(?:[ -]*(?:Code|Number|#)):?\s*([0-9.]+)'
    match = re.search(hs_code_pattern, text, re.IGNORECASE)
    if match:
        data['hs_code'] = match.group(1).strip()
    
    return data

def refresh_alchemy_token():
    """Get a fresh access token from Alchemy API."""
    try:
        response = requests.post(
            f"{ALCHEMY_API_BASE_URL}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": ALCHEMY_CLIENT_ID,
                "client_secret": ALCHEMY_CLIENT_SECRET,
                "scope": "read write"
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            print(f"Failed to get token: {response.status_code} {response.text}")
            return None
            
    except Exception as e:
        print(f"Error getting Alchemy token: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Route for Extracting Data from Uploaded File
@app.route('/extract', methods=['POST'])
def extract_data():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save the uploaded file to the temporary directory
        file_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(file_path)
        
        try:
            # Process the file and extract text
            if file.filename.lower().endswith('.pdf'):
                text = extract_text_from_pdf(file_path)
            else:
                # Assume it's an image
                text = extract_text_from_image(file_path)
                
            # If we couldn't extract any text, return an error
            if not text or len(text.strip()) < 10:
                return jsonify({
                    "error": "Could not extract sufficient text from the document. Please try a clearer image or a PDF with embedded text."
                }), 400
                
            # Extract structured data from the text
            extracted_data = extract_coa_data(text)
            
            # Also extract test results and add them to the response
            test_results = extract_test_results(text)
                
            # Return the extracted data
            return jsonify({
                **extracted_data,
                "full_text": text,
                "test_results": test_results
            })
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            return jsonify({"error": f"Error processing file: {str(e)}"}), 500

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
        
        # Extract test results from the full text
        full_text = extracted_data.get('full_text', '')
        test_results = extracted_data.get('test_results', [])
        
        # If test_results not provided in the request, extract them now
        if not test_results:
            test_results = extract_test_results(full_text)
        
        # Format test results for Alchemy API
        test_properties = format_test_results_for_alchemy(test_results)
        
        # Base properties that we always include
        base_properties = [
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
        
        # Combine base properties with test properties
        all_properties = base_properties + test_properties
        
        # Format data for Alchemy API - exactly matching the Postman structure
        alchemy_payload = [
            {
                "processId": None,
                "recordTemplate": "exampleParsing",
                "properties": all_properties
            }
        ]
        
        # Here you would send the alchemy_payload to your Alchemy API
        # For example:
        # response = requests.post(
        #     f"{ALCHEMY_API_BASE_URL}/api/v1/records",
        #     headers={
        #         "Authorization": f"Bearer {access_token}",
        #         "Content-Type": "application/json"
        #     },
        #     json=alchemy_payload
        # )
        # 
        # if response.status_code == 201:
        #     record_data = response.json()
        #     record_id = record_data.get("id")
        #     record_url = f"https://app.alchemy.cloud/records/{record_id}"
        #     return jsonify({
        #         "status": "success",
        #         "record_id": record_id,
        #         "record_url": record_url,
        #         "tests_extracted": len(test_results)
        #     })
        # else:
        #     return jsonify({
        #         "status": "error",
        #         "message": f"Alchemy API error: {response.status_code} {response.text}"
        #     }), 500
        
        # For now, we'll return a success response with some info about the extracted tests
        return jsonify({
            "status": "success",
            "message": f"Data formatted for Alchemy with {len(test_results)} test results",
            "record_id": "12345",  # This would come from your API response
            "record_url": "https://app.alchemy.cloud/records/12345",  # This would come from your API response
            "tests_extracted": len(test_results)
        })
        
    except Exception as e:
        print(f"Error sending data to Alchemy: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
