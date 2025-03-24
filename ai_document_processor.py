# Import required libraries
import re
import os
import logging
import pickle
import json
import time
from collections import defaultdict
from datetime import datetime

# Conditional imports to handle missing dependencies gracefully
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    AI_IMPORTS_AVAILABLE = True
except ImportError:
    AI_IMPORTS_AVAILABLE = False
    logging.warning("Scientific Python libraries not available, running in limited mode")

# Try to import transformer libraries, but have fallbacks
TRANSFORMERS_AVAILABLE = False
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logging.warning("Transformers library not available, using pattern matching only")

class AIDocumentProcessor:
    # ... your existing code ...
    
    def get_training_history(self):
        """Get training history for review"""
        # If training_history exists as an attribute, return it
        if hasattr(self, 'training_history'):
            return self.training_history
        # Otherwise return an empty list
        return []

    def get_document_schemas(self):
        """Get current document schemas for review"""
        # If document_schemas exists as an attribute, return it
        if hasattr(self, 'document_schemas'):
            return self.document_schemas
        # Otherwise return an empty dict
        return {}

    def export_model_config(self, output_file=None):
        """Export the model configuration in readable JSON format for review"""
        if not output_file:
            output_file = 'model_config.json'
        
        try:
            # Create a simplified config if training_history doesn't exist
            if hasattr(self, 'training_history'):
                training_history = self.training_history
            else:
                training_history = []
                
            # Get document schemas
            if hasattr(self, 'document_schemas'):
                document_schemas = self.document_schemas
            else:
                document_schemas = {}
                
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
        """Import model configuration from a JSON file"""
        try:
            with open(input_file, 'r') as f:
                config = json.load(f)
                
            if 'document_schemas' in config:
                self.document_schemas = config['document_schemas']
                
            if 'training_history' in config:
                self.training_history = config['training_history']
                
            # Save the updated state
            self.save_model_state()
            
            return f"Model configuration imported from {input_file}"
        except Exception as e:
            logging.error(f"Error importing model configuration: {e}")
            return f"Error importing model configuration: {e}"
    
    def lazy_load_classifier(self):
    """Lazy load the classifier only when needed"""
    if not self.classifier and TRANSFORMERS_AVAILABLE:
        try:
            self.classifier = pipeline("zero-shot-classification", 
                                       model="facebook/bart-large-mnli",
                                       device=-1)  # Force CPU usage
            logging.info("Zero-shot classifier loaded successfully.")
            return True
        except Exception as e:
            logging.error(f"Failed to load classifier: {e}")
            self.classifier = None
            return False
    return self.classifier is not None


    
    def classify_document(self, text):
        """Classify document type using patterns or zero-shot classification if available"""
        # First try pattern-based classification (always works, even without AI)
        doc_type, confidence = self.pattern_based_classification(text)
        
        # If confident with patterns, return that result
        if confidence > 0.8:
            return doc_type, confidence
            
        # Otherwise, try AI classification if available
        if self.lazy_load_classifier() and text:
            try:
                # Limit text to first 2000 chars to save processing time
                sample_text = text[:2000]
                
                # Define possible classes
                candidate_labels = ["Safety Data Sheet", "Technical Data Sheet", 
                                   "Certificate of Analysis", "Unknown Document"]
                
                # Use zero-shot classification
                result = self.classifier(sample_text, candidate_labels)
                best_match = result['labels'][0]
                best_confidence = result['scores'][0]
                
                # Map to internal document type
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
                # Fall back to pattern-based classification
                return doc_type, confidence
        
        # Return pattern-based results if AI not available
        return doc_type, confidence
    
    def pattern_based_classification(self, text):
        """Classify document based on text patterns - faster than AI approach"""
        if not text:
            return "unknown", 0.0
            
        text_lower = text.lower()
        
        # SDS patterns
        sds_patterns = [
            r'safety\s+data\s+sheet',
            r'material\s+safety\s+data\s+sheet',
            r'msds',
            r'sds\s+number',
            r'section\s+[1-9][0-6]?[\s:]+\w+',  # SDS has 16 numbered sections
            r'hazard(s)?\s+identification'
        ]
        
        # TDS patterns
        tds_patterns = [
            r'technical\s+data\s+sheet',
            r'product\s+specification',
            r'technical\s+specification',
            r'physical\s+properties',
            r'application\s+guide',
            r'technical\s+bulletin'
        ]
        
        # COA patterns - enhanced to catch more varieties
        coa_patterns = [
            r'certificate\s+of\s+analysis',
            r'c\.?o\.?a\.?',
            r'analytical\s+result',
            r'test\s+result',
            r'batch\s+analysis',
            r'quality\s+release',
            r'purity\s+analysis',
            r'lot\s+number',
            r'batch\s+number',
            r'certified\s+purity'
        ]
        
        # Count matches for each document type
        sds_count = sum(1 for pattern in sds_patterns if re.search(pattern, text_lower))
        tds_count = sum(1 for pattern in tds_patterns if re.search(pattern, text_lower))
        coa_count = sum(1 for pattern in coa_patterns if re.search(pattern, text_lower))
        
        # Calculate confidence based on match count
        total_matches = sds_count + tds_count + coa_count
        
        if total_matches == 0:
            return "unknown", 0.1
        
        # Determine document type
        if sds_count > tds_count and sds_count > coa_count:
            confidence = sds_count / len(sds_patterns)
            return "sds", min(confidence, 0.95)  # Cap at 0.95
            
        elif tds_count > sds_count and tds_count > coa_count:
            confidence = tds_count / len(tds_patterns)
            return "tds", min(confidence, 0.95)
            
        elif coa_count > sds_count and coa_count > tds_count:
            confidence = coa_count / len(coa_patterns)
            return "coa", min(confidence, 0.95)

        else:
            # If there's a tie or unclear results
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
            # Enhanced COA extraction
            
            # Extract batch/lot number (support multiple formats)
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
                
            # Extract purity
            purity_patterns = [
                r'(?i)(?:Purity|Assay)\s*[:.]\s*([\d.]+\s*%)',
                r'(?i)Certified\s+purity\s*[:.]\s*([\d.]+\s*[±\+\-]\s*[\d.]+\s*%)',
                r'(?i)(?:Purity|Assay)(?:\s+Result)?\s*[:.]\s*([\d.]+)',
                r'(?i)(?:Purity|Assay)[\s\S]{1,50}([\d.]+\s*%)'
            ]
            
            for pattern in purity_patterns:
                purity_match = re.search(pattern, text)
                if purity_match:
                    entities['purity'] = purity_match.group(1).strip()
                    break
                
            # Extract manufacturing/test date
            date_patterns = [
                r'(?i)(?:Date\s+of\s+(?:Analysis|Test|Manufacture)|Release\s+Date|Analysis\s+Date)\s*[:.]\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})',
                r'(?i)(?:Date\s+of\s+(?:Analysis|Test|Manufacture)|Release\s+Date|Analysis\s+Date)\s*[:.]\s*(\w+\s+\d{1,2},?\s+\d{4})'
            ]
            
            for pattern in date_patterns:
                date_match = re.search(pattern, text)
                if date_match:
                    entities['analysis_date'] = date_match.group(1).strip()
                    break
            
            # Extract test results
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
