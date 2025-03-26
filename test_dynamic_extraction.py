#!/usr/bin/env python3
"""
Test script for dynamic field extraction
"""

from ai_document_processor import AIDocumentProcessor

# Sample COA text
coa_text = """Certificate of Analysis
Acetone
Propan-2-one/ Dimethyl ketone (C3H6O)
HS Code: 29141100
CAS Number: 67-64-1
Date of Issue: 98.03.07
Test Method Units Specification
Limits Results
Min Max
Appearance Visual - Colorless, Clear liquid Colorless, Clear liquid
Density @ 20֯ C ASTM D 1298 g/ml 0.79 0.79
Water ASTM D 1364 % wt 0.5 0.33
Acidity as acetic acid ASTM D 1613 % wt - 0.01 0.005
Purity ASTM D 3545 % wt 97 0.13 MOH 97.01AC 2.53 Uk
"""

def main():
    # Initialize the processor
    processor = AIDocumentProcessor()
    
    # Process the text
    result = processor.process_document(coa_text)
    
    # Print the results
    print("Document Type:", result["document_type"])
    print("Confidence:", result["confidence"])
    print("\nExtracted Entities:")
    for key, value in result["entities"].items():
        print(f"  {key}: {value}")
    
    # Check if specific fields are extracted
    fields_to_check = ['appearance', 'density', 'purity', 'cas_number']
    missing_fields = [field for field in fields_to_check if field not in result["entities"]]
    
    if missing_fields:
        print("\nWARNING: The following fields were not extracted:", ", ".join(missing_fields))

if __name__ == "__main__":
    main()
