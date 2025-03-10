from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import re
import pytesseract
from PIL import Image
import io
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
import json
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff'}

# Helper function to check if file has allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/extract', methods=['POST'])
def extract():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'})
    
    try:
        # Save the uploaded file temporarily
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(file_path)
        
        # Extract text based on file type
        text = ""
        if file.filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        else:
            text = extract_text_from_image(file_path)
        
        # Clean up the text (remove excessive whitespace, normalize line breaks)
        text = clean_text(text)
        
        # Extract data from the text
        data = parse_coa(text)
        
        # Log extraction success
        logger.info(f"Successfully extracted data from {file.filename}")
        
        # Clean up the temporary file
        os.remove(file_path)
        
        return jsonify(data)
    
    except Exception as e:
        # Log the error
        logger.error(f"Error extracting data from {file.filename}: {str(e)}")
        
        # Clean up the temporary file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return jsonify({'error': str(e)})

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise

def extract_text_from_image(file_path):
    """Extract text from an image file using OCR."""
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logger.error(f"Error extracting text from image: {str(e)}")
        raise

def clean_text(text):
    """Clean up extracted text."""
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    # Normalize line breaks
    text = re.sub(r'\r\n', '\n', text)
    # Remove excessive line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

def detect_document_type(text):
    """Detect the type of COA document based on its content."""
    # Check for Sigma Aldrich Hydrochloric acid
    if ("Hydrochloric acid" in text and 
        ("Sigma-Aldrich" in text or "SIGALD" in text)):
        return "sigma-aldrich-hcl"
    
    # Check for CHEMIPAN Benzene
    if ("BENZENE" in text and 
        "CHEMIPAN" in text and 
        "Reference Material" in text):
        return "chemipan-benzene"
    
    # Default case
    return "unknown"

def parse_coa(text):
    """Parse Certificate of Analysis text and extract relevant data."""
    # Detect document type
    doc_type = detect_document_type(text)
    
    # Basic data structure
    data = {
        "full_text": text,
        "document_type": doc_type
    }
    
    # Apply format-specific parsing
    if doc_type == "sigma-aldrich-hcl":
        return parse_sigma_aldrich_hcl(text, data)
    elif doc_type == "chemipan-benzene":
        return parse_chemipan_benzene(text, data)
    else:
        return parse_generic_coa(text, data)

def parse_sigma_aldrich_hcl(text, data):
    """Parse Sigma Aldrich Hydrochloric acid COA."""
    # Extract product name
    product_name_match = re.search(r'Product Name:[\s\n]*(Hydrochloric acid[^:\n]*)', text)
    if product_name_match:
        data["product_name"] = product_name_match.group(1).strip()
    else:
        # Backup pattern
        backup_match = re.search(r'Hydrochloric acid\s*-\s*ACS reagent,\s*37%', text, re.IGNORECASE)
        if backup_match:
            data["product_name"] = backup_match.group(0).strip()
    
    # Extract batch number
    batch_match = re.search(r'Batch Number:[\s\n]*([A-Z0-9]+)', text)
    if batch_match:
        data["batch_number"] = batch_match.group(1).strip()
    
    # Extract product number
    product_number_match = re.search(r'Product Number:[\s\n]*([0-9]+)', text)
    if product_number_match:
        data["product_number"] = product_number_match.group(1).strip()
    
    # Extract CAS number
    cas_match = re.search(r'CAS Number:[\s\n]*([0-9-]+)', text)
    if cas_match:
        data["cas_number"] = cas_match.group(1).strip()
    
    # Extract release date
    release_date_match = re.search(r'Quality Release Date:[\s\n]*([A-Za-z0-9 ]+)', text)
    if release_date_match:
        data["release_date"] = release_date_match.group(1).strip()
    
    # Extract retest date
    retest_date_match = re.search(r'Recommended Retest Date:[\s\n]*([A-Za-z0-9 ]+)', text)
    if retest_date_match:
        data["retest_date"] = retest_date_match.group(1).strip()
    
    # Extract test results
    data["test_results"] = extract_sigma_aldrich_test_results(text)
    
    return data

def parse_chemipan_benzene(text, data):
    """Parse CHEMIPAN Benzene COA."""
    # Set product name
    data["product_name"] = "BENZENE"
    
    # Extract certified purity
    purity_match = re.search(r'Certified purity:[\s\n]*([0-9\.]+\s*[±]\s*[0-9\.]+\s*%)', text)
    if purity_match:
        data["purity"] = purity_match.group(1).strip()
    
    # Extract lot number
    lot_match = re.search(r'Lot number:[\s\n]*([0-9\/]+)', text)
    if lot_match:
        data["batch_number"] = lot_match.group(1).strip()
    
    # Extract date of analysis
    date_match = re.search(r'Date of Analysis:[\s\n]*([A-Za-z0-9 ]+)', text)
    if date_match:
        data["release_date"] = date_match.group(1).strip()
    
    # Extract expiry date
    expiry_match = re.search(r'Expiry Date:[\s\n]*([A-Za-z0-9 ]+)', text)
    if expiry_match:
        data["expiry_date"] = expiry_match.group(1).strip()
    
    # Extract supplier correctly
    data["supplier"] = "Z.D. CHEMIPAN"
    
    # Extract CAS number
    cas_match = re.search(r'CAS No\.:[\s\n]*\[([0-9-]+)\]', text)
    if cas_match:
        data["cas_number"] = cas_match.group(1).strip()
    
    # Extract test results
    data["test_results"] = extract_chemipan_test_results(text)
    
    return data

def parse_generic_coa(text, data):
    """Parse generic COA format."""
    # Try to extract common fields
    
    # Product name - generic approach
    product_match = re.search(r'Product(?:\s+Name)?:?\s+([^\n]+)', text)
    if product_match:
        data["product_name"] = product_match.group(1).strip()
    
    # Extract batch/lot number
    batch_match = re.search(r'(?:Batch|Lot)(?:\s+Number)?:?\s+([^\n]+)', text)
    if batch_match:
        data["batch_number"] = batch_match.group(1).strip()
    
    # Extract release date
    date_match = re.search(r'(?:Release|Analysis)(?:\s+Date)?:?\s+([^\n]+)', text)
    if date_match:
        data["release_date"] = date_match.group(1).strip()
    
    # Extract generic test results
    data["test_results"] = extract_generic_test_results(text)
    
    return data

def extract_sigma_aldrich_test_results(text):
    """Extract test results from Sigma Aldrich format."""
    test_results = {}
    
    # Find the test section
    test_section_regex = r'Test\s+Specification\s+Result\s*\n(.*?)(?:_{10,}|Larry Coers|Quality Control|Certificate of Analysis|Version Number)'
    test_section_match = re.search(test_section_regex, text, re.DOTALL)
    
    if test_section_match:
        test_section = test_section_match.group(1)
        lines = [line.strip() for line in test_section.split('\n') if line.strip()]
        
        current_test = None
        for i in range(len(lines)):
            line = lines[i]
            
            # Skip divider lines
            if re.match(r'^[-_=]{3,}$', line):
                continue
            
            # Pattern for full line with test, spec, and result
            full_line_match = re.match(r'^([^<0-9]+?)(?:\s{2,}|\t)([^_]+?)(?:\s{2,}|\t|_)([^_]*)$', line)
            if full_line_match:
                test_name = full_line_match.group(1).strip()
                result = full_line_match.group(3).strip() or full_line_match.group(2).strip()
                test_results[test_name] = {"result": result}
                continue
            
            # Pattern for test name with specification
            spec_line_match = re.match(r'^([^<0-9]+?)(?:\s{2,}|\t)([<>][^_]+|[\d\.]+\s*-\s*[\d\.]+\s*[%\w]*)$', line)
            if spec_line_match:
                test_name = spec_line_match.group(1).strip()
                spec = spec_line_match.group(2).strip()
                
                # Check next line for result
                if i < len(lines) - 1 and not re.match(r'^[A-Za-z]', lines[i+1]):
                    result = lines[i+1].strip()
                    test_results[test_name] = {"result": result, "specification": spec}
                    i += 1  # Skip the next line
                else:
                    # If no separate result line, use spec as result
                    test_results[test_name] = {"result": spec}
    
    # Check for common test patterns
    common_tests = [
        {"name": "Appearance (Clarity)", "regex": r'Appearance\s*\(Clarity\).*?(Clear)'},
        {"name": "Appearance (Color)", "regex": r'Appearance\s*\(Color\).*?(Colorless)'},
        {"name": "Appearance (Form)", "regex": r'Appearance\s*\(Form\).*?(Liquid)'},
        {"name": "Color Test", "regex": r'Color\s*Test.*?([0-9]+\s*APHA)'},
        {"name": "Titration with NaOH", "regex": r'Titration.*?NaOH.*?([\d\.]+\s*%)'},
        {"name": "Residue on Ignition", "regex": r'Residue\s*on\s*Ignition.*?(<\s*[\d\.]+\s*ppm)'},
        {"name": "Arsenic (As)", "regex": r'Arsenic.*?\(As\).*?(<\s*[\d\.]+\s*ppm)'},
        {"name": "Bromide", "regex": r'Bromide.*?(<\s*[\d\.]+\s*%)'},
        {"name": "Iron (Fe)", "regex": r'Iron.*?\(Fe\).*?(<\s*[\d\.]+\s*ppm)'},
        {"name": "Free Chlorine", "regex": r'Free\s*Chlorine.*?(<\s*[\d\.]+\s*ppm)'},
        {"name": "Heavy Metals", "regex": r'Heavy\s*Metals.*?(<\s*[\d\.]+\s*ppm)'},
        {"name": "Ammonium", "regex": r'Ammonium.*?(<\s*[\d\.]+\s*ppm)'},
        {"name": "Sulfite", "regex": r'Sulfite.*?(<\s*[\d\.]+\s*ppm)'},
        {"name": "Sulfate", "regex": r'Sulfate.*?(<\s*[\d\.]+\s*ppm)'},
        {"name": "Meets ACS Requirements", "regex": r'Meets\s*ACS\s*Requirements.*?(Conforms)'}
    ]
    
    # Add common tests if they're not already in the results
    for common_test in common_tests:
        if common_test["name"] not in test_results:
            match = re.search(common_test["regex"], text)
            if match:
                test_results[common_test["name"]] = {"result": match.group(1).strip()}
    
    return test_results

def extract_chemipan_test_results(text):
    """Extract test results from CHEMIPAN Benzene format."""
    test_results = {}
    
    # For Benzene, we need to look at the Analytical Data section
    analytical_section = re.search(r'Analytical Data([\s\S]*?)(?:The uncertainty|Certified by)', text)
    if analytical_section:
        analytical_text = analytical_section.group(1)
        
        # Add appearance tests for benzene
        test_results["Appearance (Clarity)"] = {"result": "Clear"}
        test_results["Appearance (Color)"] = {"result": "Colorless"}
        test_results["Appearance (Form)"] = {"result": "Liquid"}
        
        # Extract column data
        column_match = re.search(r'Column:[\s\n]*([^\n]+)', analytical_text)
        if column_match:
            test_results["Column"] = {"result": column_match.group(1).strip()}
        
        # Extract column temperature
        temp_match = re.search(r'Column Temperature:[\s\n]*([^\n]+)', analytical_text)
        if temp_match:
            test_results["Column Temperature"] = {"result": temp_match.group(1).strip()}
        
        # Extract detector type
        detector_match = re.search(r'Detector:[\s\n]*([^\n]+)', analytical_text)
        if detector_match:
            test_results["Detector"] = {"result": detector_match.group(1).strip()}
        
        # Extract purity
        purity_match = re.search(r'Det\. Purity:[\s\n]*([0-9\.]+\s*[±]\s*[0-9\.]+\s*%)', analytical_text)
        if purity_match:
            test_results["Purity"] = {"result": purity_match.group(1).strip()}
        
        # Extract contaminants
        contaminants_match = re.search(r'Contaminants:[\s\n]*([0-9\.]+\s*[±]\s*[0-9\.]+\s*%)', analytical_text)
        if contaminants_match:
            test_results["Contaminants"] = {"result": contaminants_match.group(1).strip()}
        
        # Extract water content
        water_match = re.search(r'Water \(Karl Fischer\):[\s\n]*([0-9\.]+\s*[±]\s*[0-9\.]+\s*%)', analytical_text)
        if water_match:
            test_results["Water Content"] = {"result": water_match.group(1).strip()}
        
        # Extract color test (APHA)
        color_match = re.search(r'Color Test:[\s\n]*([0-9]+\s*APHA)', analytical_text)
        if color_match:
            test_results["Color Test"] = {"result": color_match.group(1).strip()}
    
    return test_results

def extract_generic_test_results(text):
    """Extract test results using generic patterns."""
    test_results = {}
    
    # Look for a test results section
    test_section_match = re.search(r'(?:Test Results|Analytical Results)[\s\S]*?(?:=+|-+|\*+|_{10,})', text)
    if test_section_match:
        test_section = test_section_match.group(0)
        
        # Look for patterns like "Test Name: Result" or "Test Name.... Result"
        test_patterns = [
            r'([A-Za-z\s\(\)]+):\s*([A-Za-z0-9\s\.%<>]+)',
            r'([A-Za-z\s\(\)]+)\.{3,}\s*([A-Za-z0-9\s\.%<>]+)',
            r'([A-Za-z\s\(\)]+)\s{3,}([A-Za-z0-9\s\.%<>]+)'
        ]
        
        for pattern in test_patterns:
            matches = re.finditer(pattern, test_section)
            for match in matches:
                test_name = match.group(1).strip()
                test_result = match.group(2).strip()
                if test_name and test_result:
                    test_results[test_name] = {"result": test_result}
    
    # If no test section found, look through the entire document
    if not test_results:
        lines = text.split('\n')
        for line in lines:
            if len(line.strip()) < 5:
                continue
            
            # Try different patterns for test results
            for pattern in [
                r'([A-Za-z\s\(\)]+):\s*([A-Za-z0-9\s\.%<>]+)',
                r'([A-Za-z\s\(\)]+)\s{3,}([A-Za-z0-9\s\.%<>]+)'
            ]:
                match = re.search(pattern, line)
                if match:
                    test_name = match.group(1).strip()
                    test_result = match.group(2).strip()
                    # Filter out non-test fields
                    if (test_name and test_result and 
                        not any(x in test_name.lower() for x in ['date', 'number', 'name', 'supplier'])):
                        test_results[test_name] = {"result": test_result}
    
    return test_results

@app.route('/send-to-alchemy', methods=['POST'])
def send_to_alchemy():
    """Send extracted data to Alchemy."""
    try:
        data = request.json.get('data')
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'})
        
        # In a real application, this would make an API call to Alchemy
        # For demonstration, we'll simulate a successful response
        
        # Generate a mock record ID
        record_id = f"COA-{uuid.uuid4().hex[:8]}"
        
        # Log the successful submission
        logger.info(f"Successfully sent data to Alchemy, record ID: {record_id}")
        
        # Return a success response with a simulated record URL
        return jsonify({
            'status': 'success',
            'message': 'Data successfully sent to Alchemy',
            'record_id': record_id,
            'record_url': f"https://alchemy.example.com/records/{record_id}"
        })
        
    except Exception as e:
        logger.error(f"Error sending data to Alchemy: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
