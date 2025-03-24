# Import required libraries
import re
import os
import logging
import pickle
from collections import defaultdict

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
    """AI-enhanced document processor for SDS, TDS, and COA documents
    Optimized for Render free tier with minimal memory footprint
    """
    
    def __init__(self, model_path=None):
        """Initialize the document processor with lightweight options for free tier"""
        # Document schemas - will always be available even without AI
        self.document_schemas = {
            'sds': {
                'sections': ['Identification', 'Hazards Identification', 'Composition', 
                             'First-Aid Measures', 'Fire-Fighting Measures', 'Accidental Release',
                             'Handling and Storage', 'Exposure Controls', 'Physical Properties',
                             'Stability and Reactivity', 'Toxicological Information'],
                'required_fields': ['product_identifier', 'manufacturer', 'emergency_phone']
            },
            'tds': {
                'sections': ['Product Description', 'Features', 'Applications', 
                             'Technical Data', 'Processing', 'Storage', 'Packaging'],
                'required_fields': ['product_name', 'manufacturer', 'physical_properties']
            },
            'coa': {
                'sections': ['Product Information', 'Test Results', 'Specifications'],
                'required_fields': ['product_name', 'batch_number', 'test_results']
            }
        }
        
        # Try to load saved state if available
        self.load_model_state(model_path)
        
        # Initialize AI components only if available and in lazy loading mode
        self.classifier = None
        self.ner_extractor = None
        self.tfidf = None
        
        if AI_IMPORTS_AVAILABLE:
            self.tfidf = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
        
        # Don't initialize transformers models immediately - they'll be loaded on first use
        # This saves memory until they're actually needed
    
    def load_model_state(self, model_path=None):
        """Load saved model state if available"""
        # Try multiple potential locations
        paths_to_try = [
            model_path,
            os.environ.get('RENDER_DISK_PATH', '/app/models') + '/model_state.pkl',
            'models/model_state.pkl'
        ]
        
        for path in paths_to_try:
            if path and os.path.exists(path):
                try:
                    with open(path, 'rb') as f:
                        state = pickle.load(f)
                        self.document_schemas = state.get('document_schemas', self.document_schemas)
                        
                        # Initialize tfidf with saved vocabulary if available
                        if 'tfidf_vocabulary' in state and state['tfidf_vocabulary'] and AI_IMPORTS_AVAILABLE:
                            self.tfidf = TfidfVectorizer(vocabulary=state['tfidf_vocabulary'])
                            
                    logging.info(f"Loaded model state from {path}")
                    return True
                except Exception as e:
                    logging.warning(f"Failed to load model state from {path}: {e}")
        
        return False
    
    def save_model_state(self):
        """Save model state to a persistent location"""
        # Check if we're on Render
        if os.environ.get('RENDER'):
            # Use Render disk path if available
            disk_path = os.environ.get('RENDER_DISK_PATH', '/app/models')
            os.makedirs(disk_path, exist_ok=True)
            
            # Save model state
            try:
                with open(f"{disk_path}/model_state.pkl", 'wb') as f:
                    pickle.dump({
                        'document_schemas': self.document_schemas,
                        'tfidf_vocabulary': self.tfidf.vocabulary_ if hasattr(self.tfidf, 'vocabulary_') else None
                    }, f)
                logging.info(f"Model saved to {disk_path}/model_state.pkl")
                return f"Model saved to {disk_path}/model_state.pkl"
            except Exception as e:
                logging.error(f"Error saving model: {e}")
                return f"Error saving model: {e}"
        else:
            # Local development save path
            os.makedirs('models', exist_ok=True)
            try:
                with open('models/model_state.pkl', 'wb') as f:
                    pickle.dump({
                        'document_schemas': self.document_schemas,
                        'tfidf_vocabulary': self.tfidf.vocabulary_ if hasattr(self.tfidf, 'vocabulary_') else None
                    }, f)
                logging.info("Model saved locally to models/model_state.pkl")
                return "Model saved locally to models/model_state.pkl"
            except Exception as e:
                logging.error(f"Error saving model locally: {e}")
                return f"Error saving model locally: {e}"
    
    def lazy_load_classifier(self):
        """Lazy load the classifier only when needed"""
        if not self.classifier and TRANSFORMERS_AVAILABLE:
            try:
                # Very lightweight model for Render's free tier
                self.classifier = pipeline("zero-shot-classification", 
                                          model="facebook/bart-large-mnli",
                                          device=-1)  # Force CPU usage
                return True
            except Exception as e:
                logging.error(f"Failed to load classifier: {e}")
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
        
        # COA patterns
        coa_patterns = [
            r'certificate\s+of\s+analysis',
            r'c\.?o\.?a\.?',
            r'analytical\s+result',
            r'test\s+result',
            r'batch\s+analysis',
            r'quality\s+release',
            r'purity\s+analysis'
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
            # COA often has test results in a table
            results_section = re.search(r'(?i)((?:Test|Analytical)\s+(?:Results|Data)[\s\S]*?)'
                                      r'(?:Conclusion|Release|Approval|Authorized|$)', text)
            if results_section:
                sections['test_results'] = {
                    "title": "Test Results",
                    "content": results_section.group(1)
                }
                
            # Extract specifications section
            specs_section = re.search(r'(?i)((?:Specifications?|Requirements|Limits)[\s\S]*?)'
                                    r'(?:Test|Analytical|Conclusion|$)', text)
            if specs_section:
                sections['specifications'] = {
                    "title": "Specifications",
                    "content": specs_section.group(1)
                }
                
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
            # Extract batch/lot number
            batch = re.search(r'(?i)(?:Batch|Lot)\s+(?:Number|No|#)\s*[:.]\s*([A-Za-z0-9\-]+)', text)
            if batch:
                entities['batch_number'] = batch.group(1).strip()
                
            # Extract test results if in a structured format
            purity_match = re.search(r'(?i)(?:Purity|Assay)\s*[:.]\s*([\d.]+\s*%)', text)
            if purity_match:
                entities['purity'] = purity_match.group(1).strip()
                
            # Extract manufacturing/test date
            date_match = re.search(r'(?i)(?:Date\s+of\s+(?:Analysis|Test|Manufacture)|Release\s+Date)\s*[:.]\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})', text)
            if date_match:
                entities['analysis_date'] = date_match.group(1).strip()
                
        return entities
    
    def _extract_product_name(self, text):
        """Extract product name from document text"""
        # Try several patterns for product name
        patterns = [
            r'(?i)Product\s+name\s*[:.]\s*([^\n]+)',
            r'(?i)Product\s+identifier\s*[:.]\s*([^\n]+)',
            r'(?i)Trade\s+name\s*[:.]\s*([^\n]+)',
            r'(?i)Material\s+name\s*[:.]\s*([^\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def train_from_example(self, text, doc_type, annotations):
        """Allow the system to learn from new examples - lightweight version"""
        if not text or not doc_type:
            return {"status": "error", "message": "Missing text or document type"}
            
        updated = False
        
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
        
        # Save model state if updates were made
        if updated:
            save_result = self.save_model_state()
            return {"status": "success", "message": f"Updated extraction rules for {doc_type}", "details": save_result}
        else:
            return {"status": "warning", "message": "No updates were made to the model"}
    
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
            "sections": sections
        }
        
        return result
