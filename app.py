from flask import Flask, request, send_from_directory
import os
import pytesseract
from PIL import Image
import pdf2image
import tempfile
import config
from templates import get_index_html, get_result_html

app = Flask(__name__, static_folder='static')

# Create uploads folder if it doesn't exist
if not os.path.exists(config.UPLOAD_FOLDER):
    os.makedirs(config.UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER

@app.route('/')
def index():
    """Render the main page with the file upload form"""
    return get_index_html(
        app_title=config.APP_TITLE,
        company_name=config.COMPANY_NAME,
        logo_path=config.LOGO_PATH,
        allowed_extensions=config.ALLOWED_EXTENSIONS
    )

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files like CSS, JS, and images"""
    return send_from_directory(app.static_folder, filename)

@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload and OCR processing"""
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    
    if file.filename == '':
        return 'No selected file'
    
    # Check if the file extension is allowed
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if file_ext not in config.ALLOWED_EXTENSIONS:
        return f'File type not allowed. Allowed types: {", ".join(config.ALLOWED_EXTENSIONS)}'
    
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        text = extract_text(file_path, file_ext)
        return get_result_html(
            text=text,
            app_title=config.APP_TITLE,
            company_name=config.COMPANY_NAME,
            logo_path=config.LOGO_PATH,
            filename=file.filename
        )

def extract_text(file_path, file_ext):
    """
    Extract text from the uploaded file using Tesseract OCR
    Supports images and PDFs
    """
    try:
        # For PDF files
        if file_ext == 'pdf':
            return extract_text_from_pdf(file_path)
        # For image files
        else:
            return pytesseract.image_to_string(
                Image.open(file_path), 
                lang=config.OCR_LANGUAGE,
                config=config.TESSERACT_CONFIG
            )
    except Exception as e:
        return f"Error processing file: {str(e)}"

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF files by converting pages to images first"""
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Convert PDF to images
            pdf_pages = pdf2image.convert_from_path(
                pdf_path, 
                dpi=config.PDF_DPI,
                output_folder=temp_dir
            )
            
            # Extract text from each page
            text_results = []
            for i, page in enumerate(pdf_pages):
                text = pytesseract.image_to_string(
                    page, 
                    lang=config.OCR_LANGUAGE,
                    config=config.TESSERACT_CONFIG
                )
                text_results.append(f"--- Page {i+1} ---\n{text}")
            
            # Join all the text
            return "\n\n".join(text_results)
        except Exception as e:
            return f"Error processing PDF: {str(e)}"

if __name__ == '__main__':
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
