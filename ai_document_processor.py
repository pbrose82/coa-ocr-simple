# ai_document_processor.py

import re
import os
import logging
import pickle
import json
import time
from collections import defaultdict
from datetime import datetime

# Optional scientific and transformer imports
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    AI_IMPORTS_AVAILABLE = True
except ImportError:
    AI_IMPORTS_AVAILABLE = False
    logging.warning("Scientific Python libraries not available, running in limited mode")

TRANSFORMERS_AVAILABLE = False
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logging.warning("Transformers library not available, using pattern matching only")

class AIDocumentProcessor:
    def __init__(self):
        self.classifier = None
        self.document_schemas = {}
        self.training_history = []

        try:
            self.load_model_state()
        except:
            logging.info("No saved model state found, initializing new model")

    def save_model_state(self):
        try:
            with open("model_state.pkl", "wb") as f:
                pickle.dump({
                    "document_schemas": self.document_schemas,
                    "training_history": self.training_history
                }, f)
            logging.info("Model state saved to model_state.pkl")
            return "Model state saved"
        except Exception as e:
            logging.error(f"Error saving model state: {e}")
            return f"Error saving model state: {e}"

    def load_model_state(self):
        try:
            if os.path.exists("model_state.pkl"):
                with open("model_state.pkl", "rb") as f:
                    state = pickle.load(f)
                    self.document_schemas = state.get("document_schemas", {})
                    self.training_history = state.get("training_history", [])
                logging.info("Model state loaded from model_state.pkl")
            else:
                logging.info("No saved model state found at startup")
        except Exception as e:
            logging.error(f"Error loading model state: {e}")

    def get_training_history(self):
        return getattr(self, 'training_history', [])

    def get_document_schemas(self):
        return getattr(self, 'document_schemas', {})

    def export_model_config(self, output_file=None):
        if not output_file:
            output_file = 'model_config.json'

        try:
            training_history = getattr(self, 'training_history', [])
            document_schemas = getattr(self, 'document_schemas', {})

            config = {
                'document_schemas': document_schemas,
                'training_history': training_history,
                'model_info': {
                    'export_date': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            }

            with open(output_file, 'w') as f:
                json.dump(config, f, indent=2)

            return f"Model configuration exported to {output_file}"
        except Exception as e:
            logging.error(f"Error exporting model configuration: {e}")
            return f"Error exporting model configuration: {e}"

    def import_model_config(self, input_file):
        try:
            with open(input_file, 'r') as f:
                config = json.load(f)

            if 'document_schemas' in config:
                self.document_schemas = config['document_schemas']

            if 'training_history' in config:
                self.training_history = config['training_history']

            self.save_model_state()
            return f"Model configuration imported from {input_file}"
        except Exception as e:
            logging.error(f"Error importing model configuration: {e}")
            return f"Error importing model configuration: {e}"

    def lazy_load_classifier(self):
        if not self.classifier and TRANSFORMERS_AVAILABLE:
            try:
                self.classifier = pipeline(
                    "zero-shot-classification",
                    model="typeform/distilbert-base-uncased-mnli",
                    device=-1
                )
                return True
            except Exception as e:
                logging.error(f"Failed to load classifier: {e}")
                return False
        return self.classifier is not None

    def classify_document(self, text):
        doc_type, confidence = self.pattern_based_classification(text)

        if confidence > 0.8:
            return doc_type, confidence

        if self.lazy_load_classifier() and text:
            try:
                sample_text = text[:2000]
                candidate_labels = ["Safety Data Sheet", "Technical Data Sheet", "Certificate of Analysis", "Unknown Document"]
                result = self.classifier(sample_text, candidate_labels)
                best_match = result['labels'][0]
                best_confidence = result['scores'][0]

                if "Safety Data Sheet" in best_match:
                    return "sds", best_confidence
                elif "Technical Data Sheet" in best_match:
                    return "tds", best_confidence
                elif "Certificate of Analysis" in best_match:
                    return "coa", best_confidence
                else:
                    return "unknown", best_confidence

            except Exception as e:
                logging.error(f"AI classification failed: {e}")
                return doc_type, confidence

        return doc_type, confidence

    def pattern_based_classification(self, text):
        if not text:
            return "unknown", 0.0

        text_lower = text.lower()
        sds_patterns = [
            r'safety\s+data\s+sheet', r'material\s+safety\s+data\s+sheet', r'msds', r'sds\s+number',
            r'section\s+[1-9][0-6]?[\s:]+\w+', r'hazard(s)?\s+identification'
        ]
        tds_patterns = [
            r'technical\s+data\s+sheet', r'product\s+specification', r'technical\s+specification',
            r'physical\s+properties', r'application\s+guide', r'technical\s+bulletin'
        ]
        coa_patterns = [
            r'certificate\s+of\s+analysis', r'c\.?o\.?a\.?', r'analytical\s+result',
            r'test\s+result', r'batch\s+analysis', r'quality\s+release',
            r'purity\s+analysis', r'lot\s+number', r'batch\s+number', r'certified\s+purity'
        ]

        sds_count = sum(1 for p in sds_patterns if re.search(p, text_lower))
        tds_count = sum(1 for p in tds_patterns if re.search(p, text_lower))
        coa_count = sum(1 for p in coa_patterns if re.search(p, text_lower))

        total = sds_count + tds_count + coa_count
        if total == 0:
            return "unknown", 0.1

        if sds_count > tds_count and sds_count > coa_count:
            return "sds", min(sds_count / len(sds_patterns), 0.95)
        elif tds_count > sds_count and tds_count > coa_count:
            return "tds", min(tds_count / len(tds_patterns), 0.95)
        elif coa_count > sds_count and coa_count > tds_count:
            return "coa", min(coa_count / len(coa_patterns), 0.95)

        return "unknown", 0.3



    def __init__(self):
        """Initialize the document processor with default settings"""
        self.classifier = None  # Initialize classifier as None
        self.document_schemas = {}  # Initialize empty schemas
        self.training_history = []  # Initialize empty training history

        # Attempt to load saved model state if it exists
        try:
            self.load_model_state()
        except:
            logging.info("No saved model state found, initializing new model")


    def extract_sections(self, text, doc_type):
        """Extract sections from document based on document type"""
        sections = {}

        
        if not text:
            return sections
        
        if doc_type == "sds":
            # SDS has standardized sections numbered 1-16
            section_pattern = r'(?i)(?:SECTION|)\s*(\d{1,2})[.:)\s]+\s*([^0-9\n]{2,50})'
            matches = re.finditer(section_pattern, text)
            
            section_starts = []
            
            # Find all section headings and their positions
            for match in matches:
                section_num = match.group(1)
                section_title = match.group(2).strip()
                section_starts.append((int(section_num), section_title, match.start()))
            
            # Sort sections by their position in the document
            section_starts.sort(key=lambda x: x[2])
            
            # Extract content between section headings
            for i in range(len(section_starts)):
                start_pos = section_starts[i][2]
                end_pos = section_starts[i+1][2] if i < len(section_starts) - 1 else len(text)
                section_content = text[start_pos:end_pos].strip()
                
                # Store with section number as key for easy reference
                sections[f"section_{section_starts[i][0]}"] = {
                    "title": section_starts[i][1],
                    "content": section_content
                }
                
        elif doc_type == "tds":
            # TDS often has product properties in a table format
            # Extract technical properties section
            properties_section = re.search(r'(?i)(Technical\s+(?:Data|Properties|Information)[\s\S]*?)'
                                         r'(?:Application|Storage|Notes|Disclaimer|$)', text)
            if properties_section:
                sections['technical_properties'] = {
                    "title": "Technical Properties",
                    "content": properties_section.group(1)
                }
            
            # Extract application information
            applications = re.search(r'(?i)(Applications?|Uses?|Recommended\s+for)[\s\S]*?'
                                  r'(?:Storage|Handling|Notes|Disclaimer|$)', text)
            if applications:
                sections['applications'] = {
                    "title": "Applications",
                    "content": applications.group(1)
                }
                
        elif doc_type == "coa":
            # Improved COA section extraction
            
            # Extract test results section (multiple patterns to match different formats)
            results_patterns = [
                r'(?i)((?:Test|Analytical)\s+(?:Results|Data)[\s\S]*?)'
                r'(?:Conclusion|Release|Approval|Authorized|$)',
                
                r'(?i)(TEST\s+RESULTS[\s\S]*?)'
                r'(?:This lot|Analysis|Conclusion|$)',
                
                r'(?i)((?:Parameter|Test|Property)[\s\n]+(?:Specification|Spec|Limit)[\s\n]+(?:Result|Value)[\s\S]*?)'
                r'(?:This lot|Analysis|Conclusion|$)'
            ]
            
            for pattern in results_patterns:
                results_section = re.search(pattern, text)
                if results_section:
                    sections['test_results'] = {
                        "title": "Test Results",
                        "content": results_section.group(1)
                    }
                    break
                
            # Extract specifications section
            specs_patterns = [
                r'(?i)((?:Specifications?|Requirements|Limits)[\s\S]*?)'
                r'(?:Test|Analytical|Conclusion|$)',
                
                r'(?i)((?:Specifications?[\s\n]+)(?:[\s\S]*?))'
                r'(?:Test|Analytical|Conclusion|$)'
            ]
            
            for pattern in specs_patterns:
                specs_section = re.search(pattern, text)
                if specs_section:
                    sections['specifications'] = {
                        "title": "Specifications",
                        "content": specs_section.group(1)
                    }
                    break
                    
            # Extract product information section
            product_info_patterns = [
                r'(?i)(Product(?:\s+Name|:)[\s\S]*?)'
                r'(?:TEST|Analytical|Specifications|$)',
                
                r'(?:^|[\n\r]+)((?:Product|Catalog|Lot|Batch|CAS)[\s\S]*?)'
                r'(?:TEST|Analytical|Specifications|$)'
            ]
            
            for pattern in product_info_patterns:
                product_section = re.search(pattern, text)
                if product_section:
                    sections['product_information'] = {
                        "title": "Product Information",
                        "content": product_section.group(1)
                    }
                    break
                
        return sections
    
    def extract_entities(self, text, doc_type):
    """Extract relevant named entities based on document type"""
    entities = {}
    
    if not text:
        return entities
    
    # Common fields across document types
    product_name = self._extract_product_name(text)
    if product_name:
        entities['product_name'] = product_name
            
    # Document-specific field extraction
    if doc_type == "sds":
        # SDS extraction code (unchanged)
        # ...
        
    elif doc_type == "tds":
        # TDS extraction code (unchanged)
        # ...
        
    elif doc_type == "coa":
        # Enhanced COA extraction with dynamic field support
        
        # Standard field extractions (batch number, lot number, etc.)
        batch_patterns = [
            r'(?i)(?:Batch|Lot)\s+(?:Number|No|#)\s*[:.]\s*([A-Za-z0-9\-]+)',
            r'(?i)(?:Batch|Lot)[:.]\s*([A-Za-z0-9\-]+)',
            r'(?i)(?:Batch|Lot)\s*(?:Number|No|#)?\s*[:.]\s*([A-Za-z0-9\-]+)'
        ]
        
        for pattern in batch_patterns:
            batch_match = re.search(pattern, text)
            if batch_match:
                entities['batch_number'] = batch_match.group(1).strip()
                entities['lot_number'] = batch_match.group(1).strip()
                break
        
        # CAS number extraction
        cas_patterns = [
            r'(?i)CAS\s+(?:Number|No|#)\s*[:.]\s*([0-9\-]+)',
            r'(?i)CAS[:.]\s*([0-9\-]+)',
            r'\b(\d{2,7}-\d{2}-\d)\b'
        ]
        
        for pattern in cas_patterns:
            cas_match = re.search(pattern, text)
            if cas_match:
                entities['cas_number'] = cas_match.group(1).strip()
                break
        
        # Appearance extraction
        appearance_patterns = [
            r'(?i)Appearance\s+Visual\s+[-–]\s+([^\n]+)',
            r'(?i)Appearance[:.]\s*([^\n]+)'
        ]
        
        for pattern in appearance_patterns:
            appearance_match = re.search(pattern, text)
            if appearance_match:
                entities['appearance'] = appearance_match.group(1).strip()
                break
        
        # Density extraction
        density_patterns = [
            r'(?i)Density\s+@\s+20[^\s]*\s+ASTM\s+D\s+1298\s+g/ml\s+(\d+\.\d+)',
            r'(?i)Density[:.]\s*(\d+\.\d+)'
        ]
        
        for pattern in density_patterns:
            density_match = re.search(pattern, text)
            if density_match:
                entities['density'] = density_match.group(1).strip()
                break
        
        # Purity extraction with improved patterns
        purity_patterns = [
            r'(?i)Purity\s+ASTM\s+D\s+3545\s+%\s+wt\s+\d+(?:[^%]+)(\d+\.\d+AC)',
            r'(?i)(?:Purity|Assay)\s*[:.]\s*([\d.]+\s*%)',
            r'(?i)(?:Purity|Assay)(?:\s+Result)?\s*[:.]\s*([\d.]+)'
        ]
        
        for pattern in purity_patterns:
            purity_match = re.search(pattern, text)
            if purity_match:
                entities['purity'] = purity_match.group(1).strip()
                break
        
        # Dynamic extraction based on trained fields
        # Check if we have document schemas
        if hasattr(self, 'document_schemas') and doc_type in self.document_schemas:
            schema = self.document_schemas[doc_type]
            
            # Go through trained fields that we haven't extracted yet
            for field in schema.get('required_fields', []):
                if field not in entities and field not in ['batch_number', 'lot_number', 'cas_number', 'purity', 'appearance', 'density']:
                    # Simple pattern based on field name
                    field_pattern = r'(?i)' + field.replace('_', '\s+') + r'\s*[:.]\s*([^\n]+)'
                    field_match = re.search(field_pattern, text)
                    if field_match:
                        entities[field] = field_match.group(1).strip()
                        
        # Get test results if needed (unchanged)
        test_results = self._extract_test_results(text)
        if test_results:
            entities['test_results'] = test_results
            
    return entities

    def _extract_product_name(self, text):
        """Extract product name from document text"""
        # Try several patterns for product name
        patterns = [
            r'(?i)Product\s+Name\s*[:.]\s*([^\n]+)',
            r'(?i)Product\s+identifier\s*[:.]\s*([^\n]+)',
            r'(?i)Trade\s+name\s*[:.]\s*([^\n]+)',
            r'(?i)Material\s+name\s*[:.]\s*([^\n]+)',
            r'(?i)Product:\s*([^\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_test_results(self, text):
        """Extract test results from COA documents"""
        test_results = {}
        
        # Look for common test result formats
        
        # Format 1: Parameter/Specification/Result table pattern
        table_pattern = r'(?i)(?:Parameter|Test|Property|Description)\s+(?:Specification|Spec|Limit)\s+(?:Result|Value|Reading)'
        table_match = re.search(table_pattern, text)
        
        if table_match:
            # Find the start of the table
            table_start = table_match.start()
            
            # Find the end of the table (look for empty lines or certain phrases)
            end_markers = [
                r'\n\s*\n',
                r'(?:This lot|Analysis|Conclusion)',
                r'(?:for laboratory use|store at)'
            ]
            
            table_end = len(text)
            for marker in end_markers:
                end_match = re.search(marker, text[table_start:], re.IGNORECASE)
                if end_match:
                    potential_end = table_start + end_match.start()
                    if potential_end < table_end:
                        table_end = potential_end
            
            # Extract table content
            table_content = text[table_start:table_end]
            
            # Parse lines to extract test results
            lines = table_content.split('\n')
            current_parameter = None
            
            for i, line in enumerate(lines):
                if i == 0:  # Skip header row
                    continue
                    
                # Skip empty lines
                if not line.strip():
                    continue
                
                # Try to parse as "Parameter Specification Result"
                parts = re.split(r'\s{2,}|\t', line.strip())
                
                # Clean parts and remove any empty strings
                parts = [p.strip() for p in parts if p.strip()]
                
                if len(parts) >= 2:
                    # Found a test result
                    test_name = parts[0]
                    
                    # Handle different formats
                    if len(parts) >= 3:
                        specification = parts[1]
                        result = parts[2]
                    else:
                        specification = ""
                        result = parts[1]
                    
                    test_results[test_name] = {
                        "specification": specification,
                        "result": result
                    }
        
        # Format 2: Key-value pairs for test results
        if not test_results:
            # Look for patterns like "Test Name: Result" or "Test Name: Spec - Result"
            test_pattern = r'(?i)([A-Za-z0-9\s\-]+):\s*((?:[\d\.<>]+\s*(?:ppm|%|mg|g)){0,1}(?:[A-Za-z]+\s*)?(?:-\s*)?)((?:[\d\.<>]+\s*(?:ppm|%|mg|g))(?:\s*[A-Za-z]+)?|PASS|FAIL|Conforms)'
            
            for match in re.finditer(test_pattern, text):
                test_name = match.group(1).strip()
                specification = match.group(2).strip()
                result = match.group(3).strip()
                
                if result and (not specification or specification == "-" or specification == result):
                    specification = ""
                
                test_results[test_name] = {
                    "specification": specification,
                    "result": result
                }
        
        return test_results
    
    def train_from_example(self, text, doc_type, annotations):
        """Allow the system to learn from new examples - lightweight version"""
        if not text or not doc_type:
            return {"status": "error", "message": "Missing text or document type"}
            
        updated = False
        
        # Log training attempt
        training_record = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "doc_type": doc_type,
            "annotation_count": len(annotations.get('field_mappings', {})),
            "fields": list(annotations.get('field_mappings', {}).keys())
        }
        
        # Add custom extraction patterns for fields
        if 'extraction_patterns' in annotations:
            for field, pattern in annotations['extraction_patterns'].items():
                # Add to document schemas
                if doc_type in self.document_schemas:
                    if field not in self.document_schemas[doc_type]['required_fields']:
                        self.document_schemas[doc_type]['required_fields'].append(field)
                        updated = True
        
        # Update field mappings
        if 'field_mappings' in annotations:
            for field, value in annotations['field_mappings'].items():
                # Create pattern for exact match (simplified)
                if value and len(value) > 3:  # Only create patterns for substantial text
                    # Add to document schemas
                    if doc_type in self.document_schemas:
                        if field not in self.document_schemas[doc_type]['required_fields']:
                            self.document_schemas[doc_type]['required_fields'].append(field)
                            updated = True
        
        # Add new document type if it doesn't exist
        if doc_type not in self.document_schemas:
            self.document_schemas[doc_type] = {
                'sections': [],
                'required_fields': list(annotations.get('field_mappings', {}).keys())
            }
            updated = True
            training_record["new_doc_type"] = True
        
        # Add to training history
        self.training_history.append(training_record)
        
        # Save model state if updates were made
        if updated:
            save_result = self.save_model_state()
            return {"status": "success", "message": f"Updated extraction rules for {doc_type}", "details": save_result}
        else:
            return {"status": "warning", "message": "No updates were made to the model"}
    
    def reset_document_schema(self, doc_type):
        """Reset a document schema to default (for troubleshooting)"""
        if doc_type == "sds":
            self.document_schemas["sds"] = {
                'sections': ['Identification', 'Hazards Identification', 'Composition', 
                            'First-Aid Measures', 'Fire-Fighting Measures', 'Accidental Release',
                            'Handling and Storage', 'Exposure Controls', 'Physical Properties',
                            'Stability and Reactivity', 'Toxicological Information'],
                'required_fields': ['product_identifier', 'manufacturer', 'emergency_phone']
            }
        elif doc_type == "tds":
            self.document_schemas["tds"] = {
                'sections': ['Product Description', 'Features', 'Applications', 
                            'Technical Data', 'Processing', 'Storage', 'Packaging'],
                'required_fields': ['product_name', 'manufacturer', 'physical_properties']
            }
        elif doc_type == "coa":
            self.document_schemas["coa"] = {
                'sections': ['Product Information', 'Test Results', 'Specifications'],
                'required_fields': ['product_name', 'batch_number', 'lot_number', 'test_results', 'purity']
            }
        else:
            return {"status": "error", "message": f"Unknown document type: {doc_type}"}
            
        # Save the updated schema
        self.save_model_state()
        return {"status": "success", "message": f"Reset schema for {doc_type} to default"}
    
    def add_extraction_rule(self, doc_type, field, pattern):
        """Add a custom extraction rule"""
        if doc_type not in self.document_schemas:
            return {"status": "error", "message": f"Unknown document type: {doc_type}"}
            
        # Add field to required fields if not present
        if field not in self.document_schemas[doc_type]['required_fields']:
            self.document_schemas[doc_type]['required_fields'].append(field)
            
        # In a more advanced implementation, we would store patterns here
        # For this simplified version, we just record the change
        training_record = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "doc_type": doc_type,
            "action": "add_rule",
            "field": field,
            "pattern": pattern
        }
        
        self.training_history.append(training_record)
        
        # Save model state
        self.save_model_state()
        
        return {"status": "success", "message": f"Added extraction rule for {field} in {doc_type}"}
    
    def process_document(self, text):
        """Process document text and extract structured information"""
        if not text:
            return {
                "document_type": "unknown",
                "confidence": 0.0,
                "entities": {},
                "sections": {},
                "full_text": ""
            }
            
        # First, classify the document
        doc_type, confidence = self.classify_document(text)
        
        # Extract document sections based on type
        sections = self.extract_sections(text, doc_type)
        
        # Extract named entities
        entities = self.extract_entities(text, doc_type)
        
        # Combine results
        result = {
            "document_type": doc_type,
            "confidence": confidence,
            "entities": entities,
            "sections": sections,
            "full_text": text
        }
        
        return result
