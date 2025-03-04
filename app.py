from flask import Flask, request, jsonify, render_template_string
import os
import pytesseract
from PIL import Image
import re
import json
import requests
from werkzeug.utils import secure_filename
import uuid
import logging
import time
from pdf2image import convert_from_path
import PyPDF2

# Import the new token management utility
from utils.alchemy_token import send_to_alchemy_with_token_management

# Rest of your existing app.py code...

@app.route('/send-to-alchemy', methods=['POST'])
def send_to_alchemy():
    data = request.json
    
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    # Extract tenant from request if needed (default to 'default')
    tenant_key = data.get('tenant', 'default')
    
    try:
        # Extract the data received from the client
        extracted_data = data.get('data', {})
        
        # Format purity value - extract just the numeric part
        purity_value = format_purity_value(extracted_data.get('purity', ""))
        
        # Format data for Alchemy API - exactly matching the Postman structure
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
                                        "value": extracted_data.get('product_name', "Unknown Product"),
                                        "valuePreview": ""
                                    }
                                ]
                            }
                        ]
                    },
                    # Add other properties similar to the existing code
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
                    # Add more properties as needed
                ]
            }
        ]
        
        # Use the token manager to send data
        result = send_to_alchemy_with_token_management(alchemy_payload, tenant_key)
        
        return jsonify(result)
    
    except Exception as e:
        logging.error(f"Error processing Alchemy submission: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
