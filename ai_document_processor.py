# Import required libraries
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from transformers import pipeline

class AIDocumentProcessor:
    """AI-enhanced document processor for SDS, TDS, and COA documents"""
    
    def __init__(self, model_path=None):
        """Initialize the document processor with optional pre-trained model"""
        # Document classification model
        self.classifier = pipeline("zero-shot-classification")
        
        # Named entity recognition for chemical documents
        self.ner_extractor = pipeline("token-classification", 
                                      model="jaycode/bert-base-chemical-ner")
        
        # Document schema definitions (can be expanded with training)
        self.document_schemas = {
            'sds': {
                'sections': ['Identification', 'Hazards Identification', 'Composition', 
                             'First-Aid Measures', 'Fire-Fighting Measures', 'Accidental Release',
                             'Handling and Storage', 'Exposure Controls', 'Physical Properties',
                             'Stability and Reactivity', 'Toxicological Information', 
                             'Ecological Information', 'Disposal Considerations'],
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
        
        # Train TF-IDF vectorizer with known document types
        self.tfidf = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))

    def classify_document(self, text):
        """Classify document type using zero-shot classification"""
        # Define possible classes
        candidate_labels = ["Safety Data Sheet", "Technical Data Sheet", 
                            "Certificate of Analysis", "Unknown Document"]
        
        # Use zero-shot classification to determine document type
        result = self.classifier(text[:5000], candidate_labels)
        doc_type = result['labels'][0]
        confidence = result['scores'][0]
        
        # Map to internal document type
        if "Safety Data Sheet" in doc_type:
            return "sds", confidence
        elif "Technical Data Sheet" in doc_type:
            return "tds", confidence
        elif "Certificate of Analysis" in doc_type:
            return "coa", confidence
        else:
            return "unknown", confidence
    
    def extract_sections(self, text, doc_type):
        """Extract sections from document based on document type"""
        sections = {}
        
        if doc_type == "sds":
            # SDS has standardized sections numbered 1-16
            section_pattern = r'(?i)(?:SECTION|)\s*(\d{1,2})[.:)\s]+\s*([^0-9\n]{2,50})'
            matches = re.finditer(section_pattern, text)
            
            current_section = None
            current_content = []
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
                                         r'(?:Application|Storage|Notes|Disclaimer)', text)
            if properties_section:
                sections['technical_properties'] = properties_section.group(1)
            
            # Extract application information
            applications = re.search(r'(?i)(Applications?|Uses?|Recommended\s+for)[\s\S]*?'
                                  r'(?:Storage|Handling|Notes|Disclaimer)', text)
            if applications:
                sections['applications'] = applications.group(1)
                
        return sections
    
    def extract_entities(self, text, doc_type):
        """Extract relevant named entities based on document type"""
        entities = {}
        
        # Extract chemical entities using NER
        ner_results = self.ner_extractor(text)
        chemicals = set()
        
        for entity in ner_results:
            if entity['entity'].startswith('B-CHEM'):
                chemicals.add(entity['word'])
        
        entities['chemicals'] = list(chemicals)
        
        # Common fields across document types
        product_name = self._extract_product_name(text)
        if product_name:
            entities['product_name'] = product_name
            
        # Document-specific field extraction
        if doc_type == "sds":
            # Extract GHS hazard codes
            hazard_codes = re.findall(r'\b(H\d{3})\b', text)
            if hazard_codes:
                entities['hazard_codes'] = list(set(hazard_codes))
                
            # Extract emergency contact
            emergency = re.search(r'(?i)Emergency\s+(?:telephone|phone|contact)(?:\s+number)?\s*[.:]?\s*([0-9()\s\-+]{7,20})', text)
            if emergency:
                entities['emergency_contact'] = emergency.group(1).strip()
                
        elif doc_type == "tds":
            # Extract physical properties
            density = re.search(r'(?i)(?:Density|Specific\s+Gravity)\s*[:.]\s*([\d.,]+\s*(?:g/cm3|kg/m3))', text)
            if density:
                entities['density'] = density.group(1).strip()
                
            viscosity = re.search(r'(?i)Viscosity\s*[:.]\s*([\d.,]+\s*(?:mPas|cP|Pa\.s))', text)
            if viscosity:
                entities['viscosity'] = viscosity.group(1).strip()
                
        elif doc_type == "coa":
            # Extract batch/lot number
            batch = re.search(r'(?i)(?:Batch|Lot)\s+(?:Number|No|#)\s*[:.]\s*([A-Za-z0-9\-]+)', text)
            if batch:
                entities['batch_number'] = batch.group(1).strip()
                
            # Extract test results if in a structured format
            purity_match = re.search(r'(?i)(?:Purity|Assay)\s*[:.]\s*([\d.]+\s*%)', text)
            if purity_match:
                entities['purity'] = purity_match.group(1).strip()
                
        return entities
    
    def _extract_product_name(self, text):
        """Extract product name from document text"""
        # Try several patterns for product name
        patterns = [
            r'(?i)Product\s+name\s*[:.]\s*([^\n]+)',
            r'(?i)Product\s+identifier\s*[:.]\s*([^\n]+)',
            r'(?i)Trade\s+name\s*[:.]\s*([^\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def train_from_example(self, text, doc_type, annotations):
        """Allow the system to learn from new examples"""
        # This would store example document features for future classification
        # In a production system, this would update the models
        
        # For now, we'll just add new patterns to our extraction rules
        if 'extraction_patterns' in annotations:
            # Allow adding custom extraction patterns
            for field, pattern in annotations['extraction_patterns'].items():
                # Add to document schemas
                if doc_type in self.document_schemas:
                    if field not in self.document_schemas[doc_type]['required_fields']:
                        self.document_schemas[doc_type]['required_fields'].append(field)
        
        # Return success message
        return {"status": "success", "message": f"Updated extraction rules for {doc_type}"}
    
    def process_document(self, text):
        """Process document text and extract structured information"""
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
