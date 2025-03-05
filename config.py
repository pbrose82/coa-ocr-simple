"""
Configuration settings for the OCR application.
Edit this file to customize your application.
"""

# Application settings
APP_TITLE = "OCR Image & PDF Text Extractor"
COMPANY_NAME = "Your Company"
LOGO_PATH = "/static/logo.png"

# File upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'tif', 'tiff', 'bmp', 'pdf'}

# OCR settings
OCR_LANGUAGE = 'eng'  # Use 'eng+fra' for English and French, for example
TESSERACT_CONFIG = '--psm 3'  # Page segmentation mode: 3 = auto with OSD

# PDF settings
PDF_DPI = 300  # Higher DPI for better quality, but larger files and slower processing

# Server settings
DEBUG = True
HOST = '0.0.0.0'
PORT = 5000

# UI Customization
PRIMARY_COLOR = "#4CAF50"  # Green
SECONDARY_COLOR = "#f5f5f5"  # Light gray
FONT_FAMILY = "Arial, sans-serif"
