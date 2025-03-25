# ai_document_processor.py
# 
# This enhanced document processor adds:
# 1. Semi-automated field detection - scans documents for potential field-value pairs
# 2. Fully automated field inference - automatically identifies key-value pairs and field patterns
# 3. Transfer learning - applies knowledge from similar documents
# 4. Specialized COA document processing - formats Certificate of Analysis documents clearly
#
# Features:
# - Automatic field discovery and training
# - Context-aware pattern creation
# - Document similarity detection
# - Persistent field patterns storage
# - Dynamic field extraction for any trained field
# - Clean formatting for COA documents

import re
import os
import logging
import pickle
import json
import time
import hashlib
from collections import defaultdict, Counter
from datetime import datetime

# Optional scientific and transformer imports
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
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
        self.document_examples = {}  # Store examples of processed documents for transfer learning
        self.field_patterns = {}     # Store custom patterns for specific fields
        self.auto_trained_fields = defaultdict(set)  # Track automatically trained fields by doc type
        
        # Common field names and their patterns for automatic detection
        self.common_fields = {
            'product_name': [
                r'(?i)Product\s+Name\s*[:.]\s*([^\n]+)',
                r'(?i)Product\s+identifier\s*[:.]\s*([^\n]+)',
                r'(?i)Trade\s+name\s*[:.]\s*([^\n]+)',
            ],
            'cas_number': [
                r'(?i)CAS\s+(?:Number|No|#)\s*[:.]\s*([0-9\-]+)',
                r'(?i)CAS[:.]\s*([0-9\-]+)',
                r'\b(\d{2,7}-\d{2}-\d)\b'
            ],
            'batch_number': [
                r'(?i)(?:Batch|Lot)\s+(?:Number|No|#)\s*[:.]\s*([A-Za-z0-9\-]+)',
                r'(?i)(?:Batch|Lot)[:.]\s*([A-Za-z0-9\-]+)'
            ],
            'appearance': [
                r'(?i)Appearance\s+Visual\s+[-–]\s+([^\n]+)',
                r'(?i)Appearance[:.]\s*([^\n]+)'
            ],
            'density': [
                r'(?i)Density\s+@\s+20[^\s]*\s+ASTM\s+D\s+1298\s+g/ml\s+(\d+\.\d+)',
                r'(?i)Density[:.]\s*(\d+\.\d+\s*(?:g/cm3|kg/m3|g/mL)?)'
            ],
            'purity': [
                r'(?i)Purity\s+ASTM\s+D\s+3545\s+%\s+wt\s+\d+(?:[^%]+)(\d+\.\d+AC)',
                r'(?i)(?:Purity|Assay)\s*[:.]\s*([\d.]+\s*%)',
                r'(?i)(?:Purity|Assay)(?:\s+Result)?\s*[:.]\s*([\d.]+)'
            ],
            'manufacturer': [
                r'(?i)(?:Manufacturer|Supplier|Company)(?:\s+name)?\s*[.:]?\s*([^\n]+)'
            ],
            'date': [
                r'(?i)(?:Date\s+of\s+(?:Analysis|Test|Manufacture)|Release\s+Date|Analysis\s+Date)\s*[:.]\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})',
                r'(?i)(?:Date\s+of\s+(?:Analysis|Test|Manufacture)|Release\s+Date|Analysis\s+Date)\s*[:.]\s*(\w+\s+\d{1,2},?\s+\d{4})'
            ]
        }
        
        try:
            self.load_model_state()
        except:
            logging.info("No saved model state found, initializing new model")

    def save_model_state(self):
        try:
            model_path = os.environ.get('MODEL_STATE_PATH', 'model_state.pkl')
            with open(model_path, "wb") as f:
                pickle.dump({
                    "document_schemas": self.document_schemas,
                    "training_history": self.training_history,
                    "document_examples": self.document_examples,
                    "field_patterns": self.field_patterns,
                    "auto_trained_fields": self.auto_trained_fields
                }, f)
            logging.info(f"Model state saved to {model_path}")
            return "Model state saved"
        except Exception as e:
            logging.error(f"Error saving model state: {e}")
            return f"Error saving model state: {e}"

    def load_model_state(self):
        try:
            model_path = os.environ.get('MODEL_STATE_PATH', 'model_state.pkl')
            if os.path.exists(model_path):
                with open(model_path, "rb") as f:
                    state = pickle.load(f)
                    self.document_schemas = state.get("document_schemas", {})
                    self.training_history = state.get("training_history", [])
                    self.document_examples = state.get("document_examples", {})
                    self.field_patterns = state.get("field_patterns", {})
                    self.auto_trained_fields = state.get("auto_trained_fields", defaultdict(set))
                logging.info(f"Model state loaded from {model_path}")
            else:
                logging.info("No saved model state found at startup")
        except Exception as e:
            logging.error(f"Error loading model state: {e}")

    def get_training_history(self):
        return getattr(self, 'training_history', [])

    def get_document_schemas(self):
        return getattr(self, 'document_schemas', {})
    
    def get_auto_trained_fields(self):
        return dict(getattr(self, 'auto_trained_fields', defaultdict(set)))

    def export_model_config(self, output_file=None):
        if not output_file:
            output_file = 'model_config.json'

        try:
            training_history = getattr(self, 'training_history', [])
            document_schemas = getattr(self, 'document_schemas', {})
            field_patterns = getattr(self, 'field_patterns', {})
            auto_trained_fields = {k: list(v) for k, v in getattr(self, 'auto_trained_fields', defaultdict(set)).items()}

            config = {
                'document_schemas': document_schemas,
                'training_history': training_history,
                'field_patterns': field_patterns,
                'auto_trained_fields': auto_trained_fields,
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
                
            if 'field_patterns' in config:
                self.field_patterns = config['field_patterns']
                
            if 'auto_trained_fields' in config:
                self.auto_trained_fields = defaultdict(set)
                for doc_type, fields in config['auto_trained_fields'].items():
                    self.auto_trained_fields[doc_type] = set(fields)

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
            # Extract GHS hazard codes
            hazard_codes = re.findall(r'\b(H\d{3}[A-Za-z]?)\b', text)
            if hazard_codes:
                entities['hazard_codes'] = list(set(hazard_codes))
                
            # Extract emergency contact
            emergency = re.search(r'(?i)Emergency\s+(?:telephone|phone|contact)(?:\s+number)?\s*[.:]?\s*([0-9()\s\-+]{7,20})', text)
            if emergency:
                entities['emergency_contact'] = emergency.group(1).strip()
                
            # Extract manufacturer/supplier
            manufacturer = re.search(r'(?i)(?:Manufacturer|Supplier|Company)(?:\s+name)?\s*[.:]?\s*([^\n]+)', text)
            if manufacturer:
                entities['manufacturer'] = manufacturer.group(1).strip()
                
            # Extract CAS numbers
            cas_numbers = re.findall(r'\b(\d{2,7}-\d{2}-\d)\b', text)
            if cas_numbers:
                entities['cas_numbers'] = list(set(cas_numbers))
                
        elif doc_type == "tds":
            # Extract physical properties
            density = re.search(r'(?i)(?:Density|Specific\s+Gravity)\s*[:.]\s*([\d.,]+\s*(?:g/cm3|kg/m3|g/mL))', text)
            if density:
                entities['density'] = density.group(1).strip()
                
            viscosity = re.search(r'(?i)Viscosity\s*[:.]\s*([\d.,]+\s*(?:mPas|cP|Pa\.s))', text)
            if viscosity:
                entities['viscosity'] = viscosity.group(1).strip()
                
            flash_point = re.search(r'(?i)Flash\s+Point\s*[:.]\s*([\d.,]+\s*(?:°C|°F))', text)
            if flash_point:
                entities['flash_point'] = flash_point.group(1).strip()
                
            # Extract storage conditions
            storage = re.search(r'(?i)Storage(?:\s+conditions?)?\s*[:.]\s*([^\n]+)', text)
            if storage:
                entities['storage_conditions'] = storage.group(1).strip()
                
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
                    batch_value = batch_match.group(1).strip()
                    entities['batch_number'] = batch_value
                    entities['lot_number'] = batch_value  # Store in both fields for compatibility
                    break
                    
            # Extract CAS number
            cas_patterns = [
                r'(?i)CAS\s+(?:Number|No|#)\s*[:.]\s*([0-9\-]+)',
                r'(?i)CAS[:.]\s*([0-9\-]+)',
                r'\b(\d{2,7}-\d{2}-\d)\b'  # General CAS pattern
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
                    if field not in entities:
                        # Check if we have a custom pattern for this field
                        if field in self.field_patterns.get(doc_type, {}):
                            # Use custom pattern
                            pattern = self.field_patterns[doc_type][field]
                            field_match = re.search(pattern, text)
                            if field_match:
                                entities[field] = field_match.group(1).strip()
                        else:
                            # Use default pattern
                            field_pattern = r'(?i)' + field.replace('_', '\\s+') + r'\s*[:.]\s*([^\n]+)'
                            field_match = re.search(field_pattern, text)
                            if field_match:
                                entities[field] = field_match.group(1).strip()
            
            # Extract test results
            test_results = self._extract_test_results(text)
            if test_results:
                entities.update(test_results)
                
        # Run dynamic discovery for auto-training on any document type
        if hasattr(self, 'auto_trained_fields'):
            # Find fields we've already auto-trained on this doc type
            auto_trained = self.auto_trained_fields.get(doc_type, set())
            
            # Discover new fields automatically if we have auto-discovery enabled
            auto_discovered = self._discover_fields(text, doc_type, auto_trained)
            
            # Add newly discovered fields to entities if not already present
            for field, value in auto_discovered.items():
                if field not in entities:
                    entities[field] = value
                    
                    # Mark this field as auto-trained for this document type
                    if doc_type not in self.auto_trained_fields:
                        self.auto_trained_fields[doc_type] = set()
                    self.auto_trained_fields[doc_type].add(field)
                
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
    
    def _extract_coa_results(self, text):
        """
        Extract test results from COA documents with better formatting
        Returns a structured dictionary of test specifications and results
        """
        test_results = {}
        
        # Look for table structure in the document
        table_pattern = r'(?i)(?:Test|Parameter)(?:\s+Specification)?(?:\s+Result)?'
        table_match = re.search(table_pattern, text)
        
        if table_match:
            # Find the start of the test results section
            section_start = text.find("Test Specification Result")
            if section_start == -1:
                section_start = text.find("Test", table_match.start())
            
            # Find the end of the test results section
            end_markers = [
                "Recommended Retest Period",
                "Quality Control",
                "Sigma-Aldrich warrants",
                "________"
            ]
            
            section_end = len(text)
            for marker in end_markers:
                marker_pos = text.find(marker, section_start)
                if marker_pos != -1 and marker_pos < section_end:
                    section_end = marker_pos
            
            # Extract the test results section
            test_section = text[section_start:section_end]
            
            # Split into lines
            lines = test_section.split('\n')
            current_test = None
            
            # Process each line
            for line in lines:
                # Skip header or empty lines
                if not line.strip() or "Test Specification Result" in line or "_____" in line:
                    continue
                
                # Check if this line starts a new test
                test_match = re.match(r'^([A-Za-z][\w\s]+\(?[\w]*\)?)\s+(<[^<]+>|[\d\.\-\s]+%|\w+)\s+([^<]+)$', line.strip())
                if not test_match:
                    test_match = re.match(r'^([A-Za-z][\w\s]+\(?[\w]*\)?)\s+(<.+)$', line.strip())
                
                if test_match:
                    # New test with specification and result on same line
                    test_name = test_match.group(1).strip()
                    current_test = test_name
                    
                    if len(test_match.groups()) >= 3:
                        specification = test_match.group(2).strip()
                        result = test_match.group(3).strip()
                        test_results[test_name] = {
                            "specification": specification,
                            "result": result
                        }
                    elif len(test_match.groups()) == 2:
                        specification = test_match.group(2).strip()
                        # Look in the next part of the text for the result
                        result_match = re.search(rf"{re.escape(specification)}\s+([^_\n]+)", text[section_start:])
                        result = result_match.group(1).strip() if result_match else ""
                        test_results[test_name] = {
                            "specification": specification,
                            "result": result
                        }
                elif current_test and line.strip():
                    # This might be a continuation of the previous test or a result
                    if ":" not in line and re.search(r'^\s+', line):
                        # This is a continuation of the previous test description
                        if current_test in test_results:
                            test_results[current_test]["description"] = test_results[current_test].get("description", "") + " " + line.strip()
    
        return test_results

    def format_coa_output(self, entities):
        """
        Format COA output to be more readable and structured
        """
        if not entities:
            return "No information extracted"
        
        # Organize the data
        product_info = {}
        test_results = {}
        
        # Categorize fields
        for key, value in entities.items():
            if isinstance(value, dict) and "specification" in value:
                test_results[key] = value
            else:
                product_info[key] = value
        
        # Format product information
        formatted_output = "## Product Information\n\n"
        
        # Define the order of fields to display
        field_order = [
            "product_name", "cas_number", "product_number", "batch_number", 
            "brand", "mdl_number", "quality_release_date", "recommended_retest_date"
        ]
        
        # Add fields in specified order
        for field in field_order:
            if field in product_info:
                formatted_output += f"**{field.replace('_', ' ').title()}:** {product_info[field]}\n"
        
        # Add any other fields not in the predefined order
        for field, value in product_info.items():
            if field not in field_order and field != "test_results":
                formatted_output += f"**{field.replace('_', ' ').title()}:** {value}\n"
        
        # Add test results
        if test_results:
            formatted_output += "\n## Test Results\n\n"
            formatted_output += "| Test | Specification | Result |\n"
            formatted_output += "|-----|---------------|--------|\n"
            
            for test, data in test_results.items():
                spec = data.get("specification", "")
                result = data.get("result", "")
                formatted_output += f"| {test} | {spec} | {result} |\n"
        
        return formatted_output

    def process_coa_document(self, text):
        """
        Special processing for Certificate of Analysis documents
        """
        # First, identify the document type
        doc_type, confidence = self.classify_document(text)
        
        # If it's a COA document with high confidence, use specialized extraction
        if doc_type == "coa" and confidence > 0.7:
            # Extract basic metadata
            entities = {}
            
            # Product name
            product_name = re.search(r'Product\s+Name:?\s*([^\n]+)', text)
            if product_name:
                entities['product_name'] = product_name.group(1).strip()
            
            # Product number
            product_number = re.search(r'Product\s+Number:?\s*([A-Z0-9]+)', text)
            if product_number:
                entities['product_number'] = product_number.group(1).strip()
            
            # Batch number
            batch_number = re.search(r'Batch\s+Number:?\s*([A-Z0-9]+)', text)
            if batch_number:
                entities['batch_number'] = batch_number.group(1).strip()
            
            # Brand
            brand = re.search(r'Brand:?\s*([A-Z0-9]+)', text)
            if brand:
                entities['brand'] = brand.group(1).strip()
            
            # CAS number
            cas_number = re.search(r'CAS\s+Number:?\s*([0-9\-]+)', text)
            if cas_number:
                entities['cas_number'] = cas_number.group(1).strip()
            
            # MDL number
            mdl_number = re.search(r'MDL\s+Number:?\s*([A-Z0-9]+)', text)
            if mdl_number:
                entities['mdl_number'] = mdl_number.group(1).strip()
            
            # Quality release date
            release_date = re.search(r'Quality\s+Release\s+Date:?\s*([^\n]+)', text)
            if release_date:
                entities['quality_release_date'] = release_date.group(1).strip()
            
            # Recommended retest date
            retest_date = re.search(r'Recommended\s+Retest\s+Date:?\s*([^\n]+)', text)
            if retest_date:
                entities['recommended_retest_date'] = retest_date.group(1).strip()
            
            # Get test results with the specialized method
            test_results = self._extract_coa_results(text)
            if test_results:
                entities.update(test_results)
            
            # Format the output
            formatted_output = self.format_coa_output(entities)
            
            return {
                "document_type": "Certificate of Analysis",
                "confidence": confidence,
                "entities": entities,
                "formatted_output": formatted_output
            }
        
        # Otherwise, use the standard processing
        return self.process_document(text)
    
    def _create_context_pattern(self, text, field_name, value):
        """Create a context-aware pattern for a field based on its value and surroundings"""
        if not text or not value:
            return None
            
        # Try to find the value in the text
        value_pos = text.find(value)
        if value_pos == -1:
            # Try case insensitive search
            value_pos = text.lower().find(value.lower())
            if value_pos == -1:
                # Could not find the value, create a generic pattern
                replacement = '\\s+'
                pattern = "(?i)" + field_name.replace('_', replacement) + "\\s*[:.=]\\s*([^\\n]+)"
                return pattern
        
        # Get context before the value (look for field name or nearby text)
        context_start = max(0, value_pos - 100)
        context_before = text[context_start:value_pos].strip()
        
        # Look for field name or common pattern before value
        field_text = field_name.replace('_', ' ')
        pattern_parts = []
        
        # Try to find the field name before the value
        field_pos = context_before.lower().find(field_text.lower())
        if field_pos >= 0:
            # Found field name, use it in the pattern
            context_part = context_before[field_pos:].strip()
            pattern_parts.append(re.escape(context_part))
        else:
            # Try other common separators
            for sep in [':', '-', '=']:
                if context_before.endswith(sep):
                    pattern_parts.append(re.escape(context_before[-20:].strip()))
                    break
        
        # Build the pattern
        if pattern_parts:
            # Use context before for more specific extraction
            pattern = "(?i)" + pattern_parts[0] + "\\s*([^\\n]+)"
        else:
            # Fallback to simpler pattern
            # Avoid using backslashes in f-string expressions
            replacement = '\\s+'
            pattern = "(?i)" + field_name.replace('_', replacement) + "\\s*[:.=]\\s*([^\\n]+)"
            
        return pattern
    
    def _discover_fields(self, text, doc_type, already_trained_fields):
        """Discover new fields automatically using patterns and heuristics"""
        discovered_fields = {}
        
        # Skip if text is too short
        if not text or len(text) < 50:
            return discovered_fields
            
        # Try to find fields using common patterns
        # Look for patterns like "Field Name: Value" throughout the document
        key_value_patterns = [
            r'(?im)^([A-Z][A-Za-z0-9\s\-]{2,30})\s*[:.]\s*([^\n]+)$',  # Line starting with capitalized word(s) followed by : or .
            r'(?i)([A-Za-z][A-Za-z0-9\s\-]{2,30})\s*[:.]\s+([^\n\r]{1,100}(?:\n|\r|$))'  # More general pattern
        ]
        
        for pattern in key_value_patterns:
            for match in re.finditer(pattern, text):
                key = match.group(1).strip()
                value = match.group(2).strip()
                
                # Skip if empty value or too short
                if not value or len(value) < 2:
                    continue
                    
                # Convert key to field name format (lowercase, underscores)
                field_name = key.lower().replace(' ', '_').replace('-', '_')
                
                # Skip common words that aren't likely to be fields
                if field_name in ['the', 'and', 'for', 'this', 'with', 'from']:
                    continue
                    
                # Skip if this field is already trained
                if field_name in already_trained_fields:
                    continue
                    
                # Skip fields we already extracted
                if field_name in discovered_fields:
                    continue
                    
                # Add to discovered fields
                discovered_fields[field_name] = value
                
        # Try to find fields based on common document structure patterns
        for field_name, patterns in self.common_fields.items():
            # Skip if we already have this field or it's already trained
            if field_name in discovered_fields or field_name in already_trained_fields:
                continue
                
            # Try each pattern for this common field
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    value = match.group(1).strip()
                    discovered_fields[field_name] = value
                    break
                    
        # Try to detect table structures for test results or specifications
        if 'test_results' not in discovered_fields and 'test_results' not in already_trained_fields:
            table_detected = False
            table_headers = [
                r'(?i)(?:Test|Parameter|Property)\s+(?:Specification|Spec|Limit)\s+(?:Result|Value|Reading)',
                r'(?i)(?:Attribute|Characteristic)\s+(?:Specification|Requirement)\s+(?:Result|Observation)',
                r'(?i)(?:Parameter|Test)\s+(?:Method|Standard)\s+(?:Unit)\s+(?:Specification)\s+(?:Result)'
            ]
            
            for header_pattern in table_headers:
                if re.search(header_pattern, text):
                    table_detected = True
                    break
                    
            if table_detected:
                test_results = self._extract_test_results(text)
                if test_results:
                    discovered_fields['test_results'] = test_results
        
        return discovered_fields
        
    def get_similar_documents(self, text, doc_type):
        """Find similar documents to help with transfer learning"""
        if not text or doc_type not in self.document_examples:
            return []
            
        # Compute fingerprint for current document
        current_fingerprint = self._compute_document_fingerprint(text)
        
        # Calculate similarity with stored examples
        similar_docs = []
        
        for field, examples in self.document_examples[doc_type].items():
            for example in examples:
                fingerprint = example.get("fingerprint")
                if fingerprint and fingerprint == current_fingerprint:
                    # Exact match
                    similar_docs.append({
                        "field": field,
                        "value": example.get("value"),
                        "similarity": 1.0
                    })
                elif fingerprint and self._compute_fingerprint_similarity(current_fingerprint, fingerprint) > 0.7:
                    # Similar document
                    similar_docs.append({
                        "field": field,
                        "value": example.get("value"),
                        "similarity": 0.8
                    })
                    
        return similar_docs

    def auto_train_all_fields(self, text, doc_type):
        """Automatically train all detectable fields in a document"""
        if not text or not doc_type:
            return {"status": "error", "message": "Missing text or document type"}
        
        # Detect fields automatically
        existing_fields = set()
        if doc_type in self.document_schemas:
            existing_fields = set(self.document_schemas[doc_type].get('required_fields', []))
        
        # Find new fields
        auto_fields = self._discover_fields(text, doc_type, existing_fields)
        
        if not auto_fields:
            return {"status": "warning", "message": "No new fields found for auto-training"}
        
        # Add these fields to the schema
        updated = False
        
        # Create document type if it doesn't exist
        if doc_type not in self.document_schemas:
            self.document_schemas[doc_type] = {
                'sections': [],
                'required_fields': [],
                'auto_trained': []
            }
        
        # Make sure auto_trained list exists
        if 'auto_trained' not in self.document_schemas[doc_type]:
            self.document_schemas[doc_type]['auto_trained'] = []
            
        # Add each field to the schema
        for field_name, value in auto_fields.items():
            if field_name not in self.document_schemas[doc_type]['required_fields']:
                self.document_schemas[doc_type]['required_fields'].append(field_name)
                self.document_schemas[doc_type]['auto_trained'].append(field_name)
                updated = True
                
                # Create a pattern for this field
                pattern = self._create_context_pattern(text, field_name, value)
                
                # Store the field pattern for future extraction
                if doc_type not in self.field_patterns:
                    self.field_patterns[doc_type] = {}
                self.field_patterns[doc_type][field_name] = pattern
                
                # Mark field as auto-trained
                if doc_type not in self.auto_trained_fields:
                    self.auto_trained_fields[doc_type] = set()
                self.auto_trained_fields[doc_type].add(field_name)
                
                # Add to training history
                training_record = {
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "doc_type": doc_type,
                    "field": field_name,
                    "action": "auto_train",
                    "pattern": pattern,
                    "value": value
                }
                self.training_history.append(training_record)
        
        # Save model state
        if updated:
            self.save_model_state()
            return {
                "status": "success", 
                "message": f"Auto-trained {len(auto_fields)} fields",
                "fields": list(auto_fields.keys())
            }
        else:
            return {"status": "warning", "message": "No new fields were added"}
    
    def _compute_document_fingerprint(self, text):
        """
        Create a fingerprint of the document for similarity comparison
        This helps with transfer learning between similar documents
        """
        # Basic fingerprint based on document structure
        lines = text.split('\n')
        short_lines = [line.strip()[:50] for line in lines if len(line.strip()) > 0][:20]
        
        # Create a simple fingerprint from the first 20 non-empty lines
        fingerprint = "".join([line[:2] for line in short_lines])
        
        # Add length information
        fingerprint += f"_L{len(text)//100}"
        
        return fingerprint
    
    def _compute_fingerprint_similarity(self, fp1, fp2):
        """
        Calculate similarity between two document fingerprints
        Returns a value between 0.0 and 1.0
        """
        # Simple string similarity for now
        # Could be enhanced with more sophisticated algorithms
        if not fp1 or not fp2:
            return 0.0
            
        # Compare the first parts (document structure)
        min_len = min(len(fp1), len(fp2))
        if min_len == 0:
            return 0.0
            
        matches = sum(1 for i in range(min_len) if fp1[i] == fp2[i])
        return matches / min_len
    
    def train_from_example(self, *args, **kwargs):
        """
        Train the model with a specific example - supports two calling conventions:
        
        Convention 1 (original):
        train_from_example(self, text, doc_type, annotations)
        
        Convention 2 (enhanced):
        train_from_example(self, doc_type, field_name, text_example, value, context_before="", context_after="")
        """
        # Determine which calling convention is being used based on args
        if len(args) == 2 and 'annotations' in kwargs:
            # Original calling convention: (text, doc_type, annotations)
            return self._train_from_annotations(args[0], args[1], kwargs['annotations'])
        elif len(args) == 3 and isinstance(args[2], dict):
            # Original calling convention: (text, doc_type, annotations)
            return self._train_from_annotations(args[0], args[1], args[2])
        elif len(args) >= 4:
            # Enhanced calling convention: (doc_type, field_name, text_example, value, ...)
            doc_type = args[0]
            field_name = args[1]
            text_example = args[2]
            value = args[3]
            context_before = args[4] if len(args) > 4 else ""
            context_after = args[5] if len(args) > 5 else ""
            return self._train_from_field_value(doc_type, field_name, text_example, value, context_before, context_after)
        else:
            # Not enough arguments or unrecognized pattern
            return {"status": "error", "message": "Invalid arguments for train_from_example"}
            
    def _train_from_annotations(self, text, doc_type, annotations):
        """Allow the system to learn from new examples with enhanced pattern creation"""
        if not text or not doc_type:
            return {"status": "error", "message": "Missing text or document type"}
            
        updated = False
        
        # Initialize document fingerprint to help with transfer learning
        doc_fingerprint = self._compute_document_fingerprint(text)
        
        # Log training attempt
        training_record = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "doc_type": doc_type,
            "annotation_count": len(annotations.get('field_mappings', {})),
            "fields": list(annotations.get('field_mappings', {}).keys()),
            "document_fingerprint": doc_fingerprint
        }
        
        # Add custom extraction patterns for fields
        if 'extraction_patterns' in annotations:
            for field, pattern in annotations['extraction_patterns'].items():
                # Store pattern for this field in field_patterns
                if doc_type not in self.field_patterns:
                    self.field_patterns[doc_type] = {}
                self.field_patterns[doc_type][field] = pattern
                
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
                    # Try to find this value in the text to create context-aware pattern
                    context_pattern = self._create_context_pattern(text, field, value)
                    
                    # Store the pattern
                    if context_pattern:
                        if doc_type not in self.field_patterns:
                            self.field_patterns[doc_type] = {}
                        self.field_patterns[doc_type][field] = context_pattern
                    
                    # Add to document schemas
                    if doc_type in self.document_schemas:
                        if field not in self.document_schemas[doc_type]['required_fields']:
                            self.document_schemas[doc_type]['required_fields'].append(field)
                            updated = True
                            
                    # Store example for transfer learning
                    if doc_type not in self.document_examples:
                        self.document_examples[doc_type] = {}
                    if field not in self.document_examples[doc_type]:
                        self.document_examples[doc_type][field] = []
                    
                    self.document_examples[doc_type][field].append({
                        "value": value,
                        "fingerprint": doc_fingerprint,
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        
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
        
        # Save model state
        if updated:
            self.save_model_state()
            
        return {"status": "success", "updated": updated}
            
    def _train_from_field_value(self, doc_type, field_name, text_example, value, context_before="", context_after=""):
        """
        Train the model with a specific example
        Args:
            doc_type (str): Document type (e.g., 'coa', 'sds')
            field_name (str): Name of the field to extract
            text_example (str): Example text containing the value
            value (str): The actual value to extract
            context_before (str): Text before the value for context-aware extraction
            context_after (str): Text after the value for context-aware extraction
        """
        if not doc_type or not field_name or not text_example:
            return {"status": "error", "message": "Missing required parameters"}
            
        # Normalize field name
        field_name = field_name.lower().strip()
        
        # Make sure document type exists in schemas
        if doc_type not in self.document_schemas:
            self.document_schemas[doc_type] = {
                'required_fields': [],
                'auto_trained': [],
                'field_patterns': {},
                'sections': []
            }
            
        # Add to required fields if not already there
        if field_name not in self.document_schemas[doc_type]['required_fields']:
            self.document_schemas[doc_type]['required_fields'].append(field_name)
            
        # Create a regex pattern from this example
        pattern = self._create_extraction_pattern(text_example, value, context_before, context_after)
        
        # Store the training example
        if doc_type not in self.document_examples:
            self.document_examples[doc_type] = {}
            
        if field_name not in self.document_examples[doc_type]:
            self.document_examples[doc_type][field_name] = []
            
        # Add fingerprint for transfer learning
        doc_fingerprint = self._compute_document_fingerprint(text_example)
        
        # Store the example with pattern and fingerprint
        self.document_examples[doc_type][field_name].append({
            "text": text_example,
            "value": value,
            "pattern": pattern,
            "context_before": context_before,
            "context_after": context_after,
            "fingerprint": doc_fingerprint,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # Store the field pattern for future extraction
        if doc_type not in self.field_patterns:
            self.field_patterns[doc_type] = {}
            
        # Use the new pattern or combine with existing patterns
        if field_name in self.field_patterns[doc_type]:
            existing_pattern = self.field_patterns[doc_type][field_name]
            # Combine patterns with OR for more robust extraction
            combined_pattern = "(?:" + existing_pattern + ")|(?:" + pattern + ")"
            self.field_patterns[doc_type][field_name] = combined_pattern
        else:
            self.field_patterns[doc_type][field_name] = pattern
            
        # Add to training history
        training_record = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "doc_type": doc_type,
            "field": field_name,
            "action": "manual_train",
            "pattern": pattern,
            "value": value
        }
        self.training_history.append(training_record)
        
        # Save the updated state
        self.save_model_state()
        
        return {
            "status": "success", 
            "message": f"Field '{field_name}' trained successfully",
            "pattern": pattern
        }
        
    def _create_extraction_pattern(self, text, value, context_before="", context_after=""):
        """
        Create a regex pattern for extracting values based on an example
        Uses context before and after the value for more accurate extraction
        """
        if not text or not value:
            return None
            
        # Escape special regex characters in the value
        escaped_value = re.escape(value)
        
        # Find the value in the text
        value_pos = text.find(value)
        if value_pos == -1:
            # If exact value not found, try case-insensitive search
            value_pos = text.lower().find(value.lower())
            if value_pos == -1:
                # If still not found, create a generic pattern
                return "([^\\n]+)"
                
        # Get context before and after the value
        if not context_before:
            # Find the nearest line break or start of text
            start_pos = text.rfind('\n', 0, value_pos)
            if start_pos == -1:
                start_pos = 0
            else:
                start_pos += 1  # Skip the newline
                
            context_before = text[start_pos:value_pos]
        
        if not context_after:
            # Find the nearest line break or end of text
            end_pos = text.find('\n', value_pos + len(value))
            if end_pos == -1:
                end_pos = len(text)
                
            context_after = text[value_pos + len(value):end_pos]
        
        # Clean up and escape the contexts
        context_before = context_before.strip()
        context_after = context_after.strip()
        
        escaped_before = re.escape(context_before) if context_before else ""
        escaped_after = re.escape(context_after) if context_after else ""
        
        # Build the pattern
        if escaped_before and escaped_after:
            # With both before and after context
            pattern = escaped_before + "\\s*([^\\n]+?)\\s*" + escaped_after
        elif escaped_before:
            # Only before context
            pattern = escaped_before + "\\s*([^\\n]+)"
        elif escaped_after:
            # Only after context
            pattern = "([^\\n]+?)\\s*" + escaped_after
        else:
            # Generic pattern as fallback
            pattern = "([^\\n]+)"
            
        # Make the pattern case-insensitive
        pattern = "(?i)" + pattern
        
        return pattern
    
    def extract_entities_with_patterns(self, text, doc_type):
        """
        Extract entities using trained patterns specific to the document type
        This complements the rule-based extraction in extract_entities
        """
        entities = {}
        
        if not text or not doc_type or doc_type not in self.document_schemas:
            return entities
            
        # Get the patterns for this document type
        field_patterns = self.field_patterns.get(doc_type, {})
        
        # Extract values using each pattern
        for field, pattern in field_patterns.items():
            try:
                match = re.search(pattern, text)
                if match:
                    entities[field] = match.group(1).strip()
            except Exception as e:
                logging.error(f"Error extracting {field} with pattern {pattern}: {e}")
                
        return entities
    
    def process_document(self, text):
        """
        Process document text and extract structured information
        Enhanced with auto-training and transfer learning
        """
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
        
        # For COA documents, use specialized processing
        if doc_type == "coa" and confidence > 0.7:
            return self.process_coa_document(text)
            
        # Extract document sections
        sections = self.extract_sections(text, doc_type)
        
        # First pass: extract entities with rule-based methods
        entities = self.extract_entities(text, doc_type)
        
        # Second pass: use trained patterns
        pattern_entities = self.extract_entities_with_patterns(text, doc_type)
        
        # Merge, giving preference to rule-based extraction
        for field, value in pattern_entities.items():
            if field not in entities:
                entities[field] = value
                
        # Auto-train if confidence is high
        if confidence > 0.7 and doc_type != "unknown":
            self.auto_train_all_fields(text, doc_type)
            
        # Get similar documents for reference
        similar_docs = self.get_similar_documents(text, doc_type)
        
        # Return the combined results
        result = {
            "document_type": doc_type,
            "confidence": confidence,
            "entities": entities,
            "sections": sections,
            "full_text": text
        }
        
        # Include similar documents data if any found
        if similar_docs:
            result["similar_documents"] = similar_docs
            
        return result

    def reset_document_schema(self, doc_type):
        """Reset the schema for a document type to its default state"""
        if doc_type not in self.document_schemas:
            return {"status": "error", "message": f"Document type '{doc_type}' not found"}
            
        # Remove from document schemas
        self.document_schemas.pop(doc_type, None)
        
        # Remove from field patterns
        self.field_patterns.pop(doc_type, None)
        
        # Remove from document examples
        self.document_examples.pop(doc_type, None)
        
        # Remove from auto-trained fields
        self.auto_trained_fields.pop(doc_type, None)
        
        # Add reset event to training history
        training_record = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "doc_type": doc_type,
            "action": "reset_schema"
        }
        self.training_history.append(training_record)
        
        # Save the updated state
        self.save_model_state()
        
        return {
            "status": "success",
            "message": f"Schema for document type '{doc_type}' has been reset"
        }
