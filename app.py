# app.py - Complete OCR Application with Admin Functionality

# Standard library imports
import os
import json
import logging
import time
import secrets
import uuid
import re
from datetime import datetime, timedelta

# Third-party imports
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask import redirect, url_for, Response, session
import requests
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import PyPDF2
from pdf2image import convert_from_path

# Import AI Document Processor with error handling
try:
    from app.models.ai_document_processor import AIDocumentProcessor
    ai_available = True
except ImportError:
    ai_available = False
    logging.warning("AI document processor not available, falling back to legacy parser")

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Flask Application Setup
app = Flask(__name__, static_folder='static', template_folder='templates')

# Secret key for sessions
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Set session timeout (1 hour)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# Configuration Constants
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Persistent config paths for cloud hosting
CONFIG_DIR = '/opt/render/project/config'
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.json')

# If local development or the directory doesn't exist, use a local path
if not os.path.exists(CONFIG_DIR):
    CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.json')

# Global Token Cache
token_cache = {}

# Initialize AI processor
ai_processor = None
if ai_available:
    try:
        ai_processor = AIDocumentProcessor()
        logging.info("AI Document Processor initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing AI Document Processor: {e}")

# Configuration Management Functions
def ensure_config_directory():
    """Ensure the configuration directory exists"""
    try:
        # Log detailed filesystem information
        logging.info(f"Current working directory: {os.getcwd()}")
        logging.info(f"Attempting to check {CONFIG_DIR}")
        
        # Ensure the directory exists
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        logging.info(f"Ensuring config directory exists: {CONFIG_DIR}")
    except Exception as e:
        logging.error(f"Error creating config directory: {str(e)}")

def create_default_config():
    """Create a default configuration if the config file is not found"""
    return {
        "default_tenant": "default",
        "default_urls": {
            "refresh_url": "https://core-production.alchemy.cloud/core/api/v2/refresh-token",
            "api_url": "https://core-production.alchemy.cloud/core/api/v2/update-record",
            "filter_url": "https://core-production.alchemy.cloud/core/api/v2/filter-records",
            "find_records_url": "https://core-production.alchemy.cloud/core/api/v2/find-records",
            "base_url": "https://app.alchemy.cloud/"
        },
        "tenants": {
            "default": {
                "tenant_name": "productcaseelnlims4uat",
                "display_name": "Product Case ELN&LIMS UAT",
                "description": "Primary Alchemy environment",
                "button_class": "primary",
                "env_token_var": "DEFAULT_REFRESH_TOKEN",
                "use_custom_urls": False
            }
        }
    }

def load_config():
    """Load configuration with diagnostics"""
    try:
        # Ensure directory exists
        ensure_config_directory()
        
        # Log file existence and details
        logging.info(f"Config path exists: {os.path.exists(CONFIG_PATH)}")
        
        if os.path.exists(CONFIG_PATH) and os.path.isfile(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r') as f:
                    file_contents = f.read()
                
                # Parse the contents
                config = json.loads(file_contents)
                
                # Validate config structure
                if config and 'tenants' in config:
                    logging.info("Successfully loaded configuration")
                    return config
            except Exception as read_error:
                logging.error(f"Error reading config file: {read_error}")
        
        # If no config found, create and save default
        logging.warning("No existing configuration found. Creating default configuration.")
        default_config = create_default_config()
        save_config(default_config)
        
        return default_config
    
    except Exception as e:
        logging.error(f"Unexpected error in load_config: {str(e)}")
        default_config = create_default_config()
        save_config(default_config)
        return default_config

def save_config(config):
    """Save configuration to file"""
    try:
        # Ensure directory exists
        ensure_config_directory()
        
        # Check if the configuration is valid
        if not config or 'tenants' not in config or len(config.get('tenants', {})) == 0:
            logging.error("Attempted to save invalid configuration")
            return False
        
        # Log the directory and file path
        logging.info(f"Attempting to save config to: {CONFIG_PATH}")
        
        # Save the file
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        
        logging.info(f"Configuration successfully saved to {CONFIG_PATH}")
        return True
    except Exception as e:
        logging.error(f"Unexpected error saving configuration: {str(e)}")
        return False

def get_tenant_config(tenant_id):
    """Get tenant configuration from config file"""
    if tenant_id not in CONFIG["tenants"]:
        logging.error(f"Tenant {tenant_id} not found in configuration")
        tenant_id = DEFAULT_TENANT
    
    tenant = CONFIG["tenants"][tenant_id]
    
    # Build the complete tenant configuration
    tenant_config = {
        "tenant_id": tenant_id,
        "tenant_name": tenant.get("tenant_name"),
        "display_name": tenant.get("display_name", tenant.get("tenant_name")),
        "description": tenant.get("description", ""),
        "button_class": tenant.get("button_class", "primary"),
    }
    
    # Check for a directly stored refresh token first
    if "stored_refresh_token" in tenant and tenant["stored_refresh_token"]:
        tenant_config["refresh_token"] = tenant["stored_refresh_token"]
    else:
        # Fall back to environment variable
        tenant_config["refresh_token"] = os.getenv(tenant.get("env_token_var"))
    
    # Add URLs based on config
    if tenant.get("use_custom_urls") and "custom_urls" in tenant:
        tenant_config.update({
            "refresh_url": tenant["custom_urls"].get("refresh_url"),
            "api_url": tenant["custom_urls"].get("api_url"),
            "filter_url": tenant["custom_urls"].get("filter_url"),
            "find_records_url": tenant["custom_urls"].get("find_records_url"),
            "base_url": tenant["custom_urls"].get("base_url")
        })
    else:
        tenant_config.update({
            "refresh_url": DEFAULT_URLS["refresh_url"],
            "api_url": DEFAULT_URLS["api_url"],
            "filter_url": DEFAULT_URLS["filter_url"],
            "find_records_url": DEFAULT_URLS["find_records_url"],
            "base_url": DEFAULT_URLS["base_url"]
        })
    
    return tenant_config

def refresh_alchemy_token(tenant):
    """Refresh the Alchemy API token for a specific tenant"""
    global token_cache
    
    # Get tenant configuration
    tenant_config = get_tenant_config(tenant)
    refresh_token = tenant_config.get('refresh_token')
    refresh_url = tenant_config.get('refresh_url')
    tenant_name = tenant_config.get('tenant_name')
    
    # Create token cache entry for tenant if it doesn't exist
    if tenant not in token_cache:
        token_cache[tenant] = {
            "access_token": None,
            "expires_at": 0
        }
    
    current_time = time.time()
    if (token_cache[tenant]["access_token"] and 
        token_cache[tenant]["expires_at"] > current_time + 300):
        logging.info(f"Using cached Alchemy token for tenant: {tenant}")
        return token_cache[tenant]["access_token"]
    
    if not refresh_token:
        logging.error(f"Missing refresh token for tenant: {tenant}")
        return None
    
    try:
        logging.info(f"Refreshing Alchemy API token for tenant: {tenant}")
        response = requests.put(
            refresh_url, 
            json={"refreshToken": refresh_token},
            headers={"Content-Type": "application/json"}
        )
        
        if not response.ok:
            logging.error(f"Failed to refresh token for tenant {tenant}. Status: {response.status_code}, Response: {response.text}")
            return None
        
        data = response.json()
        
        # Find token for the specified tenant
        tenant_token = next((token for token in data.get("tokens", []) 
                            if token.get("tenant") == tenant_name), None)
        
        if not tenant_token:
            logging.error(f"Tenant '{tenant_name}' not found in refresh response")
            return None
        
        # Cache the token
        access_token = tenant_token.get("accessToken")
        expires_in = tenant_token.get("expiresIn", 3600)
        
        token_cache[tenant] = {
            "access_token": access_token,
            "expires_at": current_time + expires_in
        }
        
        logging.info(f"Successfully refreshed Alchemy token for tenant {tenant}, expires in {expires_in} seconds")
        return access_token
        
    except Exception as e:
        logging.error(f"Error refreshing Alchemy token for tenant {tenant}: {str(e)}")
        return None

# Utility Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf_without_ocr(pdf_path):
    """Try to extract text directly from PDF without OCR"""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(min(5, len(reader.pages))):  # Only process first 5 pages on free tier
                page_text = reader.pages[page_num].extract_text() or ""
                if page_text:
                    text += f"--- Page {page_num+1} ---\n{page_text}\n\n"
        
        return text if len(text.strip()) > 100 else None
    except Exception as e:
        logging.error(f"Error extracting text directly from PDF: {e}")
        return None

def preprocess_text_for_tables(text):
    """Preprocess text to better handle table structures"""
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        if re.search(r"\s{3,}", line):
            processed_line = re.sub(r"\s{3,}", "\t", line)
            processed_lines.append(processed_line)
        else:
            processed_lines.append(line)
    
    return "\n".join(processed_lines)

# Authentication for admin routes
def authenticate(username, password):
    """Validate admin credentials"""
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
    return username == admin_username and password == admin_password

@app.before_request
def require_auth():
    """
    Require authentication for admin routes with session timeout
    Sessions expire after 1 hour of inactivity
    """
    if request.path.startswith('/admin') and not request.path.startswith('/admin/login'):
        # Skip authentication for the login page itself
        if request.path == '/admin/login':
            return None
            
        # Check if user is already authenticated and session is still valid
        if 'admin_authenticated' in session and session['admin_authenticated']:
            # Check if last activity was recorded 
            if 'last_activity' in session:
                # If more than 1 hour since last activity, invalidate the session
                last_activity = datetime.fromisoformat(session['last_activity'])
                if datetime.utcnow() - last_activity > timedelta(hours=1):
                    session.pop('admin_authenticated', None)
                    session.pop('last_activity', None)
                    return redirect(url_for('admin_login'))
                
            # Update last activity time
            session['last_activity'] = datetime.utcnow().isoformat()
            return None
        else:
            # Not authenticated, redirect to login page
            return redirect(url_for('admin_login'))

# Load configuration
ensure_config_directory()
CONFIG = load_config()
DEFAULT_URLS = CONFIG["default_urls"]
DEFAULT_TENANT = CONFIG["default_tenant"]

# Route Handlers
@app.route('/')
def index():
    """Main route that shows tenant selector"""
    return render_template('tenant_selector.html', tenants=CONFIG["tenants"])

@app.route('/tenant/<tenant>')
def process_tenant(tenant):
    """Process a specific tenant"""
    # Validate tenant
    if tenant not in CONFIG["tenants"]:
        return render_template('error.html', message=f"Unknown tenant: {tenant}"), 404
    
    tenant_config = get_tenant_config(tenant)
    
    app.logger.info(f"Rendering index.html for tenant: {tenant} ({tenant_config['tenant_name']})")
    # Store the tenant in session for future requests
    session['tenant'] = tenant
    return render_template('index.html', tenant=tenant, tenant_name=tenant_config['display_name'])

@app.route('/healthz')
def health():
    """Health check endpoint"""
    return "ok"

@app.route('/training')
def training():
    """Route for the training page"""
    return render_template('training.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)

# Model Management Routes
@app.route('/model-info')
def model_info():
    """View information about the AI model for debugging"""
    if not ai_processor:
        return jsonify({"status": "error", "message": "AI processor not available"}), 500
    
    try:
        # Get model information
        document_schemas = ai_processor.get_document_schemas()
        training_history = ai_processor.get_training_history()
        
        # Export the model configuration
        export_result = ai_processor.export_model_config('model_config.json')
        
        return jsonify({
            "status": "success", 
            "document_schemas": document_schemas,
            "training_history": training_history,
            "export_result": export_result
        })
    except Exception as e:
        logging.error(f"Error getting model info: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/model-explorer')
def model_explorer():
    """Display the AI model explorer page"""
    return render_template('model_explorer.html')

@app.route('/api/model-data')
def get_model_data():
    """API endpoint to get model data for the explorer interface"""
    if not ai_processor:
        return jsonify({"status": "error", "message": "AI processor not available"}), 500
    
    try:
        # Force reload the model state from disk to get latest changes
        try:
            if hasattr(ai_processor, 'load_model_state'):
                ai_processor.load_model_state()
                logging.info("Reloaded model state from disk")
        except Exception as e:
            logging.warning(f"Unable to reload model state: {e}")
        
        # Get model information - handle missing methods
        document_schemas = {}
        try:
            if hasattr(ai_processor, 'get_document_schemas'):
                document_schemas = ai_processor.get_document_schemas()
            elif hasattr(ai_processor, 'document_schemas'):
                document_schemas = ai_processor.document_schemas
        except Exception as e:
            logging.error(f"Error getting document schemas: {e}")
            document_schemas = {
                "sds": {"required_fields": ["product_name", "cas_number", "hazard_codes"]},
                "tds": {"required_fields": ["product_name", "physical_properties"]},
                "coa": {"required_fields": ["product_name", "batch_number", "lot_number", "purity"]}
            }
        
        # Try to get training history, but handle case where method doesn't exist
        training_history = []
        try:
            if hasattr(ai_processor, 'get_training_history'):
                training_history = ai_processor.get_training_history()
            elif hasattr(ai_processor, 'training_history'):
                training_history = ai_processor.training_history
        except Exception as e:
            logging.warning(f"Unable to get training history: {e}")
        
        # Group training history by document type
        history_by_type = {}
        for entry in training_history:
            doc_type = entry.get('doc_type', 'unknown')
            if doc_type not in history_by_type:
                history_by_type[doc_type] = []
            history_by_type[doc_type].append(entry)
        
        # Count fields trained for each document type
        field_counts = {}
        for doc_type, schema in document_schemas.items():
            # Count fields from schema
            required_fields = schema.get('required_fields', [])
            field_counts[doc_type] = len(required_fields)
        
        # Build extraction examples
        extraction_examples = {}
        for doc_type, schema in document_schemas.items():
            extraction_examples[doc_type] = {
                "fields": schema.get("required_fields", []),
                "examples": get_extraction_examples(doc_type)
            }
        
        # Log the response for debugging
        logging.info(f"Model data response: {len(document_schemas)} schemas, {len(training_history)} training events")
        
        return jsonify({
            "status": "success",
            "document_schemas": document_schemas,
            "training_history": history_by_type,
            "field_counts": field_counts,
            "extraction_examples": extraction_examples,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Add timestamp for debugging
        })
    except Exception as e:
        logging.error(f"Error getting model data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def get_extraction_examples(doc_type):
    """Get sample extraction patterns for the given document type"""
    examples = {}
    
    if doc_type == "sds":
        examples = {
            "product_name": {
                "pattern": r"Product\s+Name\s*[:.]\s*([^\n]+)",
                "example": "Product Name: Acetone"
            },
            "cas_number": {
                "pattern": r"CAS\s+Number\s*[:.]\s*([0-9\-]+)",
                "example": "CAS Number: 67-64-1"
            },
            "hazard_codes": {
                "pattern": r"\b(H\d{3}[A-Za-z]?)\b",
                "example": "Hazard Codes: H225, H319, H336"
            }
        }
    elif doc_type == "tds":
        examples = {
            "product_name": {
                "pattern": r"Product\s+Name\s*[:.]\s*([^\n]+)",
                "example": "Product Name: TechBond Adhesive X-500"
            },
            "density": {
                "pattern": r"(?:Density|Specific\s+Gravity)\s*[:.]\s*([\d.,]+\s*(?:g/cm3|kg/m3|g/mL))",
                "example": "Density: 1.05 g/cm3"
            },
            "storage_conditions": {
                "pattern": r"Storage(?:\s+conditions?)?\s*[:.]\s*([^\n]+)",
                "example": "Storage conditions: Store at 5-25°C"
            }
        }
    elif doc_type == "coa":
        examples = {
            "batch_number": {
                "pattern": r"(?:Batch|Lot)\s+(?:Number|No|#)\s*[:.]\s*([A-Za-z0-9\-]+)",
                "example": "Batch Number: ABC123"
            },
            "purity": {
                "pattern": r"(?:Purity|Assay)\s*[:.]\s*([\d.]+\s*%)",
                "example": "Purity: 99.8%"
            },
            "test_results": {
                "pattern": "Complex extraction logic",
                "example": "Test Results: multiple fields extracted as objects"
            }
        }
    
    return examples

# Route for File Extraction
@app.route('/extract', methods=['POST'])
def extract():
    # Get current tenant from session or use default
    current_tenant = session.get('tenant', DEFAULT_TENANT)
    tenant_config = get_tenant_config(current_tenant)
    
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    # If the user does not select a file, the browser submits an empty file
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        try:
            # Start timing
            start_time = time.time()
            logging.info(f"Starting processing for {filename}")
            
            # Save the file temporarily
            file.save(filepath)
            logging.info(f"File saved at {filepath}")
            
            # Process based on file type
            if filepath.lower().endswith('.pdf'):
                logging.info("Processing PDF file")
                
                # First try to extract text directly (for text-based PDFs)
                text = extract_text_from_pdf_without_ocr(filepath)
                
                if text:
                    logging.info(f"Successfully extracted text directly from PDF in {time.time() - start_time:.2f} seconds")
                else:
                    logging.info("Direct text extraction failed, falling back to OCR")
                    # Convert PDF to images with highly optimized settings
                    images = convert_from_path(
                        filepath,
                        dpi=100,  # Very low DPI for speed on free tier
                        first_page=1,
                        last_page=2,  # Only process first 2 pages for free tier
                        thread_count=1,  # Single thread to reduce memory
                        grayscale=True  # Grayscale for faster processing
                    )
                    logging.info(f"Converted PDF to {len(images)} images in {time.time() - start_time:.2f} seconds")
                    
                    # OCR the first page only
                    if images:
                        text = ""
                        for i, img in enumerate(images):
                            if i >= 2:  # Limit to first 2 pages on free tier
                                break
                            page_text = pytesseract.image_to_string(img)
                            text += f"--- Page {i+1} ---\n{page_text}\n\n"
                        logging.info(f"OCR completed in {time.time() - start_time:.2f} seconds")
                    else:
                        return jsonify({"error": "Failed to extract pages from PDF"}), 500
            else:
                # For image files, process directly
                logging.info("Processing image file")
                img = Image.open(filepath)
                text = pytesseract.image_to_string(img)
                logging.info(f"Image OCR completed in {time.time() - start_time:.2f} seconds")
            
            # Clean up the file
            try:
                os.remove(filepath)
            except Exception as e:
                logging.warning(f"Failed to remove temp file: {e}")
            
            # Use AI-based processing if available
            if ai_processor is not None:
                logging.info("Using AI Document Processor for enhanced extraction")
                ai_start = time.time()
                
                try:
                    # Process with AI
                    ai_result = ai_processor.process_document(text)
                    logging.info(f"AI processing completed in {time.time() - ai_start:.2f} seconds")
                    
                    # Convert AI result to format compatible with existing UI
                    data = adapt_ai_result_to_legacy_format(ai_result)
                    data['full_text'] = text
                    
                except Exception as e:
                    logging.error(f"AI processing failed, falling back to legacy parser: {e}")
                    # Fall back to legacy processing
                    data = parse_coa_data(text)
                    data['full_text'] = text
            else:
                # Use legacy processing
                logging.info("Using legacy parser (AI not available)")
                parsing_start = time.time()
                data = parse_coa_data(text)
                logging.info(f"Legacy parsing completed in {time.time() - parsing_start:.2f} seconds")
                data['full_text'] = text
            
            # Add tenant information to the data
            data['tenant'] = current_tenant
            data['tenant_name'] = tenant_config['display_name']
            
            # Remove any record fields from the data to ensure they don't display
            if '_record_id' in data:
                del data['_record_id']
            if '_record_url' in data:
                del data['_record_url']
            
            # Save this internally for Alchemy API calls
            app.config['LAST_EXTRACTED_DATA'] = {
                "data": data,
                "internal": {
                    "record_id": "51409",
                    "record_url": f"{tenant_config['base_url']}{tenant_config['tenant_name']}/record/51409",
                    "tenant": current_tenant
                }
            }
            
            total_time = time.time() - start_time
            logging.info(f"Total processing time: {total_time:.2f} seconds")
            
            return jsonify(data)
            
        except Exception as e:
            logging.error(f"Error processing file: {e}")
            # Clean up the file in case of error
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "File type not allowed"}), 400

# Route for Training the AI
@app.route('/train', methods=['POST'])
def train():
    if not ai_processor:
        return jsonify({"status": "error", "message": "AI processor not available"}), 500
        
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
        
    file = request.files['file']
    doc_type = request.form.get('doc_type', 'unknown')
    annotations_json = request.form.get('annotations', '{}')
    
    try:
        annotations = json.loads(annotations_json)
    except:
        annotations = {}
        
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        try:
            # Save the file
            file.save(filepath)
            
            # Extract text from file
            if filepath.lower().endswith('.pdf'):
                text = extract_text_from_pdf_without_ocr(filepath) or ""
                if not text:
                    # Convert just first page for training
                    images = convert_from_path(filepath, dpi=150, first_page=1, last_page=1)
                    if images:
                        text = pytesseract.image_to_string(images[0])
                    else:
                        return jsonify({"status": "error", "message": "Failed to extract text from PDF"}), 500
            else:
                # Process image
                img = Image.open(filepath)
                text = pytesseract.image_to_string(img)
            
            # Clean up file
            try:
                os.remove(filepath)
            except:
                pass
                
            # Train AI processor with extracted text
            result = ai_processor.train_from_example(text, doc_type, annotations)
            return jsonify(result)
            
        except Exception as e:
            logging.error(f"Error in training: {e}")
            # Clean up file on error
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            return jsonify({"status": "error", "message": str(e)}), 500
            
    return jsonify({"status": "error", "message": "File type not allowed"}), 400

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    error = None
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if authenticate(username, password):
            # Set session as authenticated
            session['admin_authenticated'] = True
            session['last_activity'] = datetime.utcnow().isoformat()
            session.permanent = True  # Use the permanent session lifetime
            
            # Redirect to the admin panel
            return redirect(url_for('admin_panel'))
        else:
            error = "Invalid credentials. Please try again."
    
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    session.pop('last_activity', None)
    return redirect(url_for('admin_login'))

@app.route('/admin', methods=['GET'])
def admin_panel():
    """Admin panel to manage tenants"""
    return render_template('admin.html', tenants=CONFIG["tenants"], default_tenant=DEFAULT_TENANT)

# Configuration Management Routes
@app.route('/api/update-tenant-token', methods=['POST'])
def update_tenant_token():
    """Update refresh token for a tenant directly in the config"""
    try:
        data = request.json
        if not data or 'tenant_id' not in data or 'refresh_token' not in data:
            return jsonify({
                "status": "error", 
                "message": "Missing tenant_id or refresh_token"
            }), 400
            
        tenant_id = data['tenant_id']
        refresh_token = data['refresh_token']
        
        # Check if tenant exists
        if tenant_id not in CONFIG["tenants"]:
            return jsonify({
                "status": "error", 
                "message": f"Tenant {tenant_id} not found"
            }), 404
        
        # Verify token by calling Alchemy's token validation/refresh endpoint
        try:
            response = requests.put(
                DEFAULT_URLS['refresh_url'], 
                json={"refreshToken": refresh_token},
                headers={"Content-Type": "application/json"}
            )
            
            # Log full response details
            logging.info(f"Token verification response status: {response.status_code}")
            
            # If response is not successful, log the full text
            if not response.ok:
                logging.error(f"Token verification failed. Response text: {response.text}")
                return jsonify({
                    "status": "error", 
                    "message": f"Token verification failed: {response.text}"
                }), 400
        except Exception as verify_error:
            logging.error(f"Error verifying token: {verify_error}")
            return jsonify({
                "status": "error", 
                "message": f"Token verification error: {str(verify_error)}"
            }), 500
        
        # Update token in config
        try:
            # Directly modify the global CONFIG
            CONFIG["tenants"][tenant_id]["stored_refresh_token"] = refresh_token
            
            # Attempt to save configuration
            save_result = save_config(CONFIG)
            
            if not save_result:
                logging.error(f"Failed to save configuration for tenant {tenant_id}")
                return jsonify({
                    "status": "error", 
                    "message": "Failed to save configuration"
                }), 500
        except Exception as config_error:
            logging.error(f"Error updating configuration: {config_error}")
            return jsonify({
                "status": "error", 
                "message": f"Configuration update error: {str(config_error)}"
            }), 500
        
        # Clear the token cache for this tenant
        if tenant_id in token_cache:
            del token_cache[tenant_id]
        
        return jsonify({
            "status": "success", 
            "message": f"Refresh token updated for tenant {tenant_id}"
        })
        
    except Exception as e:
        logging.error(f"Unexpected error updating tenant token: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin/add-tenant', methods=['POST'])
def add_tenant():
    """Add a new tenant to the configuration"""
    try:
        tenant_id = request.form.get('tenant_id')
        tenant_name = request.form.get('tenant_name')
        display_name = request.form.get('display_name')
        description = request.form.get('description', '')
        button_class = request.form.get('button_class', 'primary')
        env_token_var = request.form.get('env_token_var')
        use_custom_urls = request.form.get('use_custom_urls') == 'on'
        
        # Validate input
        if not tenant_id or not tenant_name or not display_name or not env_token_var:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
        # Check if tenant already exists
        if tenant_id in CONFIG["tenants"]:
            return jsonify({"status": "error", "message": f"Tenant {tenant_id} already exists"}), 400
        
        # Create tenant config
        new_tenant = {
            "tenant_name": tenant_name,
            "display_name": display_name,
            "description": description,
            "button_class": button_class,
            "env_token_var": env_token_var,
            "use_custom_urls": use_custom_urls
        }
        
        # Add custom URLs if needed
        if use_custom_urls:
            new_tenant["custom_urls"] = {
                "refresh_url": request.form.get('refresh_url', DEFAULT_URLS["refresh_url"]),
                "api_url": request.form.get('api_url', DEFAULT_URLS["api_url"]),
                "filter_url": request.form.get('filter_url', DEFAULT_URLS["filter_url"]),
                "find_records_url": request.form.get('find_records_url', DEFAULT_URLS["find_records_url"]),
                "base_url": request.form.get('base_url', DEFAULT_URLS["base_url"])
            }
        
        # Update configuration in memory
        CONFIG["tenants"][tenant_id] = new_tenant
        
        # Save configuration to file
        save_config(CONFIG)
        
        return jsonify({"status": "success", "message": f"Tenant {display_name} added successfully"})
    except Exception as e:
        logging.error(f"Error adding tenant: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin/update-tenant/<tenant_id>', methods=['POST'])
def update_tenant(tenant_id):
    """Update an existing tenant"""
    try:
        # Check if tenant exists
        if tenant_id not in CONFIG["tenants"]:
            return jsonify({"status": "error", "message": f"Tenant {tenant_id} not found"}), 404
        
        tenant_name = request.form.get('tenant_name')
        display_name = request.form.get('display_name')
        description = request.form.get('description', '')
        button_class = request.form.get('button_class', 'primary')
        env_token_var = request.form.get('env_token_var')
        use_custom_urls = request.form.get('use_custom_urls') == 'on'
        
        # Validate input
        if not tenant_name or not display_name or not env_token_var:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
        # Update tenant config
        CONFIG["tenants"][tenant_id].update({
            "tenant_name": tenant_name,
            "display_name": display_name,
            "description": description,
            "button_class": button_class,
            "env_token_var": env_token_var,
            "use_custom_urls": use_custom_urls
        })
        
        # Update custom URLs if needed
        if use_custom_urls:
            CONFIG["tenants"][tenant_id]["custom_urls"] = {
                "refresh_url": request.form.get('refresh_url', DEFAULT_URLS["refresh_url"]),
                "api_url": request.form.get('api_url', DEFAULT_URLS["api_url"]),
                "filter_url": request.form.get('filter_url', DEFAULT_URLS["filter_url"]),
                "find_records_url": request.form.get('find_records_url', DEFAULT_URLS["find_records_url"]),
                "base_url": request.form.get('base_url', DEFAULT_URLS["base_url"])
            }
        elif "custom_urls" in CONFIG["tenants"][tenant_id]:
            del CONFIG["tenants"][tenant_id]["custom_urls"]
        
        # Save configuration to file
        save_config(CONFIG)
        
        return jsonify({"status": "success", "message": f"Tenant {display_name} updated successfully"})
    except Exception as e:
        logging.error(f"Error updating tenant: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin/delete-tenant/<tenant_id>', methods=['POST'])
def delete_tenant(tenant_id):
    """Delete a tenant"""
    try:
        # Check if tenant exists
        if tenant_id not in CONFIG["tenants"]:
            return jsonify({"status": "error", "message": f"Tenant {tenant_id} not found"}), 404
        
        # Can't delete default tenant
        if tenant_id == DEFAULT_TENANT:
            return jsonify({"status": "error", "message": "Cannot delete default tenant"}), 400
        
        # Delete tenant
        display_name = CONFIG["tenants"][tenant_id].get("display_name", tenant_id)
        del CONFIG["tenants"][tenant_id]
        
        # Save configuration to file
        save_config(CONFIG)
        
        return jsonify({"status": "success", "message": f"Tenant {display_name} deleted successfully"})
    except Exception as e:
        logging.error(f"Error deleting tenant: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get-refresh-token', methods=['POST'])
def get_refresh_token():
    """Proxy for Alchemy sign-in API to get refresh tokens"""
    try:
        # Get credentials from request
        data = request.json
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({"status": "error", "message": "Missing email or password"}), 400
            
        # Forward the request to Alchemy API
        alchemy_response = requests.post(
            'https://core-production.alchemy.cloud/core/api/v2/sign-in',
            json={
                "email": data['email'],
                "password": data['password']
            },
            headers={"Content-Type": "application/json"}
        )
        
        # Return the response directly
        return alchemy_response.json(), alchemy_response.status_code
            
    except Exception as e:
        logging.error(f"Error getting refresh token: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Route for Sending Data to Alchemy
@app.route('/send-to-alchemy', methods=['POST'])
def send_to_alchemy():
    # Get current tenant from session or use default
    current_tenant = session.get('tenant', DEFAULT_TENANT)
    tenant_config = get_tenant_config(current_tenant)
    
    data = request.json
    
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    try:
        # Get the saved data from app config
        try:
            saved_data = app.config.get('LAST_EXTRACTED_DATA', {})
            extracted_data = saved_data.get('data', {})
            internal_data = saved_data.get('internal', {})
            
            # Get record ID and URL from internal data
            record_id = internal_data.get('record_id', "51409")
            record_url = internal_data.get('record_url', f"{tenant_config['base_url']}{tenant_config['tenant_name']}/record/51409")
        except:
            # Fallback if something went wrong
            extracted_data = data.get('data', {})
            record_id = "51409"
            record_url = f"{tenant_config['base_url']}{tenant_config['tenant_name']}/record/51409"
        
        # Format data for Alchemy API (customize this based on your needs)
        product_name = extracted_data.get('product_name', "Unknown Product")
        cas_number = extracted_data.get('cas_number', "")
        purity = extracted_data.get('purity', "")
        lot_number = extracted_data.get('lot_number', "")
        
        # Get a fresh access token from Alchemy
        access_token = refresh_alchemy_token(current_tenant)
        
        if not access_token:
            return jsonify({
                "status": "error", 
                "message": "Failed to authenticate with Alchemy API"
            }), 500
        
        # Format data for Alchemy API - match the structure expected by your Alchemy templates
        alchemy_payload = [
            {
                "processId": None,
                "recordTemplate": "exampleParsing",
                "properties": [
                    {
                        "identifier": "RecordName",
                        "rows": [
                            {
                                "row": 0,
                                "values": [
                                    {
                                        "value": product_name,
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
                                        "value": cas_number,
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
                                        "value": purity,
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
                                        "value": lot_number,
                                        "valuePreview": ""
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        
        # Send to Alchemy API
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        logging.info(f"Sending data to Alchemy: {json.dumps(alchemy_payload)}")
        response = requests.post(tenant_config['api_url'], headers=headers, json=alchemy_payload)
        
        # Log response for debugging
        logging.info(f"Alchemy API response status code: {response.status_code}")
        logging.info(f"Alchemy API response: {response.text}")
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Try to extract the record ID from the response
        try:
            response_data = response.json()
            # Extract record ID from response - adjust this based on actual response structure
            if isinstance(response_data, list) and len(response_data) > 0:
                if 'id' in response_data[0]:
                    record_id = response_data[0]['id']
                elif 'recordId' in response_data[0]:
                    record_id = response_data[0]['recordId']
            elif isinstance(response_data, dict):
                if 'id' in response_data:
                    record_id = response_data['id']
                elif 'recordId' in response_data:
                    record_id = response_data['recordId']
                elif 'data' in response_data and isinstance(response_data['data'], list) and len(response_data['data']) > 0:
                    if 'id' in response_data['data'][0]:
                        record_id = response_data['data'][0]['id']
                    elif 'recordId' in response_data['data'][0]:
                        record_id = response_data['data'][0]['recordId']
            
            # If record ID was found, construct the URL
            if record_id:
                record_url = f"{tenant_config['base_url']}{tenant_config['tenant_name']}/record/{record_id}"
                logging.info(f"Created record URL: {record_url}")
            
        except Exception as e:
            logging.warning(f"Could not extract record ID from response: {e}")
        
        # Return success response with record URL if available
        return jsonify({
            "status": "success", 
            "message": "Data successfully sent to Alchemy",
            "response": response.json() if response.text else {"message": "No content in response"},
            "record_id": record_id,
            "record_url": record_url
        })
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error sending to Alchemy: {e}")
        
        # Try to capture response content if available
        error_response = None
        if hasattr(e, 'response') and e.response:
            try:
                error_response = e.response.json()
            except:
                error_response = {"text": e.response.text}
        
        return jsonify({
            "status": "error", 
            "message": str(e),
            "details": error_response
        }), 500
        
    except Exception as e:
        logging.error(f"Error sending to Alchemy: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

# Legacy Data Processing Functions (assuming these exist or need to be implemented)
def adapt_ai_result_to_legacy_format(ai_result):
    """Convert AI processor result to format expected by the UI"""
    # Implementation depends on your AI processor output format
    # This is a placeholder - customize based on your actual needs
    data = {
        "document_type": ai_result.get("document_type", "unknown"),
        "full_text": ai_result.get("full_text", "")
    }
    
    # Map entities to flat structure expected by frontend
    entities = ai_result.get("entities", {})
    for key, value in entities.items():
        if isinstance(value, list) and key not in ["chemicals", "hazard_codes"]:
            data[key] = ", ".join(value)
        else:
            data[key] = value
    
    # Add document-type-specific processing
    doc_type = ai_result.get("document_type")
    if doc_type == "coa" and "test_results" in entities:
        data["test_results"] = entities["test_results"]
    
    return data

def parse_coa_data(text):
    """Parse COA text without AI - legacy fallback"""
    # Implementation depends on your legacy parsing needs
    # This is a placeholder - customize based on your actual needs
    data = {
        "document_type": "unknown",
        "full_text": text
    }
    
    # Look for COA indicators
    if re.search(r"certificate\s+of\s+analysis", text, re.IGNORECASE):
        data["document_type"] = "coa"
        
        # Extract basic fields
        product_match = re.search(r"Product\s+Name\s*[:.]\s*([^\n]+)", text, re.IGNORECASE)
        if product_match:
            data["product_name"] = product_match.group(1).strip()
            
        lot_match = re.search(r"(?:Batch|Lot)\s+(?:Number|No|#)\s*[:.]\s*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
        if lot_match:
            data["lot_number"] = lot_match.group(1).strip()
            
        purity_match = re.search(r"(?:Purity|Assay)\s*[:.]\s*([\d.]+\s*%)", text, re.IGNORECASE)
        if purity_match:
            data["purity"] = purity_match.group(1).strip()
    
    # Look for SDS indicators
    elif re.search(r"(?:safety\s+data\s+sheet|material\s+safety\s+data\s+sheet|msds)", text, re.IGNORECASE):
        data["document_type"] = "sds"
        
        # Extract basic fields
        product_match = re.search(r"Product\s+Name\s*[:.]\s*([^\n]+)", text, re.IGNORECASE)
        if product_match:
            data["product_name"] = product_match.group(1).strip()
            
        cas_match = re.search(r"CAS\s+(?:Number|No|#)\s*[:.]\s*([0-9\-]+)", text, re.IGNORECASE)
        if cas_match:
            data["cas_number"] = cas_match.group(1).strip()
    
    # Look for TDS indicators
    elif re.search(r"(?:technical\s+data\s+sheet|product\s+specification)", text, re.IGNORECASE):
        data["document_type"] = "tds"
        
        # Extract basic fields
        product_match = re.search(r"Product\s+Name\s*[:.]\s*([^\n]+)", text, re.IGNORECASE)
        if product_match:
            data["product_name"] = product_match.group(1).strip()
            
        density_match = re.search(r"(?:Density|Specific\s+Gravity)\s*[:.]\s*([\d.,]+\s*(?:g/cm3|kg/m3|g/mL))", text, re.IGNORECASE)
        if density_match:
            data["density"] = density_match.group(1).strip()
    
    return data

# Main Application Runner
if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
