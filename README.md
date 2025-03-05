# Simple OCR Web Application

A clean, easy-to-configure OCR (Optical Character Recognition) web application built with Flask and Tesseract OCR.

## Features

- Upload and process images to extract text
- Clean, responsive user interface
- Easy to configure through a central config file
- Simple Python-based templating system (no separate HTML files needed)

## Setup Instructions

### Prerequisites

1. Python 3.6 or higher
2. Tesseract OCR installed on your system
   - For Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
   - For macOS: `brew install tesseract`
   - For Windows: Download and install from https://github.com/UB-Mannheim/tesseract/wiki

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/coa-ocr-simple.git
   cd coa-ocr-simple
   ```

2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Add your logo:
   - Place your logo image in the `static` folder (create the folder if it doesn't exist)
   - Name it `logo.png` or update the `LOGO_PATH` in `config.py`

4. Run the application:
   ```
   python app.py
   ```

5. Open your browser and go to `http://127.0.0.1:5000/`

## Configuration

All configuration options are in the `config.py` file:

- **APP_TITLE**: The title of your application
- **COMPANY_NAME**: Your company or organization name
- **LOGO_PATH**: Path to your logo image
- **UPLOAD_FOLDER**: Where uploaded images are stored
- **DEBUG**: Enable/disable debug mode
- **HOST**: The host address to bind to
- **PORT**: The port to listen on
- **UI Colors**: Customize the look and feel

## Project Structure

- `app.py`: The main Flask application
- `config.py`: Configuration settings
- `templates.py`: HTML templates as Python functions
- `static/`: Folder for static files (logo, CSS, etc.)
- `uploads/`: Folder where uploaded images are stored

## Customization

You can easily customize the application by:

1. Editing `config.py` to change basic settings
2. Modifying `templates.py` to change the HTML structure
3. Adding your own logo to the `static` folder

## License

This project is licensed under the MIT License - see the LICENSE file for details.
