from flask import Flask, request, send_from_directory
import os
import pytesseract
from PIL import Image
import pdf2image

app = Flask(__name__, static_folder='static')

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>OCR App</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                display: flex;
                align-items: center;
                margin-bottom: 20px;
            }
            .logo {
                height: 40px;
                margin-right: 15px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <img src="/static/logo.png" alt="Logo" class="logo">
            <h1>OCR App</h1>
        </div>
        <p>Upload a file to extract text:</p>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file">
            <input type="submit" value="Extract Text">
        </form>
    </body>
    </html>
    '''

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    
    if file.filename == '':
        return 'No selected file'
    
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        text = extract_text(file_path)
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>OCR Result</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    display: flex;
                    align-items: center;
                    margin-bottom: 20px;
                }}
                .logo {{
                    height: 40px;
                    margin-right: 15px;
                }}
                pre {{
                    background-color: #f5f5f5;
                    padding: 15px;
                    border-radius: 5px;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <img src="/static/logo.png" alt="Logo" class="logo">
                <h1>OCR Result</h1>
            </div>
            <h2>Extracted Text:</h2>
            <pre>{text}</pre>
            <a href="/">Back to Upload</a>
        </body>
        </html>
        '''

def extract_text(file_path):
    try:
        # Check if the file is a PDF
        if file_path.lower().endswith('.pdf'):
            return extract_text_from_pdf(file_path)
        else:
            # For image files
            return pytesseract.image_to_string(Image.open(file_path))
    except Exception as e:
        return f"Error: {str(e)}"

def extract_text_from_pdf(pdf_path):
    try:
        # Convert PDF to a list of PIL images
        images = pdf2image.convert_from_path(pdf_path)
        
        # Extract text from each image
        text = ""
        for i, image in enumerate(images):
            page_text = pytesseract.image_to_string(image)
            text += f"--- Page {i+1} ---\n{page_text}\n\n"
        
        return text
    except Exception as e:
        return f"Error processing PDF: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
