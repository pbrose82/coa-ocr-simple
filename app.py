from flask import Flask, request, send_from_directory
import os
import pytesseract
from PIL import Image
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
        logo_path=config.LOGO_PATH
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
    
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        text = extract_text(file_path)
        return get_result_html(
            text=text,
            app_title=config.APP_TITLE,
            company_name=config.COMPANY_NAME,
            logo_path=config.LOGO_PATH
        )

def extract_text(image_path):
    """Extract text from the uploaded image using Tesseract OCR"""
    try:
        return pytesseract.image_to_string(Image.open(image_path))
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == '__main__':
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
