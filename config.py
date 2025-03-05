"""
Configuration settings for the OCR application.
Edit this file to customize your application.
"""

# Application settings
APP_TITLE = "OCR Image Text Extractor"
COMPANY_NAME = "Your Company"
LOGO_PATH = "/static/logo.png"

# File upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'tif', 'tiff', 'bmp', 'pdf'}

# Server settings
DEBUG = True
HOST = '0.0.0.0'
PORT = 5000

# UI Customization
PRIMARY_COLOR = "#4CAF50"  # Green
SECONDARY_COLOR = "#f5f5f5"  # Light gray
FONT_FAMILY = "Arial, sans-serif"
