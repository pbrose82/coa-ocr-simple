#!/usr/bin/env python3
"""
AI Model Management Utility

This script provides tools to manage, review, and modify AI document processing models.
It allows you to view model schemas, training history, export configurations, and
make targeted adjustments to improve extraction performance.

Usage:
  python model_manager.py [command] [options]

Commands:
  info             Display information about the current model
  export           Export model configuration to a file
  import           Import model configuration from a file
  reset            Reset a document schema to default
  add-rule         Add an extraction rule for a field
  history          Show training history
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from ai_document_processor import AIDocumentProcessor
    ai_available = True
except ImportError:
    ai_available = False
    logging.error("AI document processor module not available. Please ensure ai_document_processor.py is in the same directory.")
    sys.exit(1)

def initialize_processor():
    """Initialize the AI document processor"""
    try:
        processor = AIDocumentProcessor()
        logging.info("AI Document Processor initialized successfully")
        return processor
    except Exception as e:
        logging.error(f"Error initializing AI Document Processor: {e}")
        sys.exit(1)

def display_model_info(processor):
    """Display information about the current model"""
    schemas = processor.get_document_schemas()
    history = processor.get_training_history()
    
    print("\n===== MODEL INFORMATION =====\n")
    
    # Display document schemas
    print("Document Schemas:")
    for doc_type, schema in schemas.items():
        print(f"\n  {doc_type.upper()}:")
        print(f"    Required fields: {', '.join(schema['required_fields'])}")
        if schema.get('sections'):
            print(f"    Sections: {', '.join(schema['sections'])}")
    
    # Display training history summary
    if history:
        print("\nTraining History:")
        print(f"  Total training events: {len(history)}")
        
        # Group by document type
        doc_type_counts = {}
        for entry in history:
            doc_type = entry.get('doc_type', 'unknown')
            doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1
        
        print("  Training by document type:")
        for doc_type, count in doc_type_counts.items():
            print(f"    {doc_type}: {count} training events")
        
        # Display last 3 training entries
        print("\n  Latest training events:")
        for entry in history[-3:]:
            timestamp = entry.get('timestamp', 'unknown')
            doc_type = entry.get('doc_type', 'unknown')
            field_count = entry.get('annotation_count', 0)
            fields = entry.get('fields', [])
            
            print(f"    {timestamp} - {doc_type} - {field_count} fields: {', '.join(fields[:3])}{' ...' if len(fields) > 3 else ''}")
    else:
        print("\nNo training history available.")

def export_model_config(processor, output_file):
    """Export model configuration to a file"""
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"model_config_{timestamp}.json"
    
    try:
        result = processor.export_model_config(output_file)
        print(f"\nModel configuration exported to: {output_file}")
        
        # Show a summary of what was exported
        with open(output_file, 'r') as f:
            config = json.load(f)
            
        print(f"Exported {len(config.get('document_schemas', {}))} document schemas")
        print(f"Exported {len(config.get('training_history', []))} training events")
        
        return True
    except Exception as e:
        logging.error(f"Error exporting model configuration: {e}")
        return False

def import_model_config(processor, input_file):
    """Import model configuration from a file"""
    if not os.path.exists(input_file):
        logging.error(f"File not found: {input_file}")
        return False
    
    try:
        # First make a backup of the current configuration
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"model_config_backup_{timestamp}.json"
        processor.export_model_config(backup_file)
        print(f"Created backup of current configuration: {backup_file}")
        
        # Import the new configuration
        result = processor.import_model_config(input_file)
        print(f"\nModel configuration imported from: {input_file}")
        
        # Show a summary of what was imported
        with open(input_file, 'r') as f:
            config = json.load(f)
            
        print(f"Imported {len(config.get('document_schemas', {}))} document schemas")
        print(f"Imported {len(config.get('training_history', []))} training events")
        
        return True
    except Exception as e:
        logging.error(f"Error importing model configuration: {e}")
        return False

def reset_schema(processor, doc_type):
    """Reset a document schema to default"""
    try:
        result = processor.reset_document_schema(doc_type)
        if result.get('status') == 'success':
            print(f"\nSuccessfully reset schema for '{doc_type}' to default")
            return True
        else:
            logging.error(f"Failed to reset schema: {result.get('message')}")
            return False
    except Exception as e:
        logging.error(f"Error resetting schema: {e}")
        return False

def add_extraction_rule(processor, doc_type, field, pattern):
    """Add an extraction rule for a field"""
    try:
        result = processor.add_extraction_rule(doc_type, field, pattern)
        if result.get('status') == 'success':
            print(f"\nSuccessfully added extraction rule for '{field}' in '{doc_type}'")
            return True
        else:
            logging.error(f"Failed to add rule: {result.get('message')}")
            return False
    except Exception as e:
        logging.error(f"Error adding rule: {e}")
        return False

def show_training_history(processor):
    """Show detailed training history"""
    history = processor.get_training_history()
    
    if not history:
        print("\nNo training history available.")
        return
    
    print("\n===== TRAINING HISTORY =====\n")
    print(f"Total training events: {len(history)}")
    
    # Group by document type
    doc_types = set()
    for entry in history:
        doc_types.add(entry.get('doc_type', 'unknown'))
    
    # Display history by document type
    for doc_type in sorted(doc_types):
        print(f"\nDocument Type: {doc_type.upper()}")
        
        doc_history = [entry for entry in history if entry.get('doc_type') == doc_type]
        for i, entry in enumerate(doc_history, 1):
            timestamp = entry.get('timestamp', 'unknown')
            field_count = entry.get('annotation_count', 0)
            fields = entry.get('fields', [])
            action = entry.get('action', 'training')
            
            print(f"  {i}. [{timestamp}] {action.capitalize()}")
            
            if action == 'add_rule':
                print(f"     Field: {entry.get('field', 'unknown')}")
                print(f"     Pattern: {entry.get('pattern', 'unknown')}")
            else:
                print(f"     Fields ({field_count}): {', '.join(fields)}")
                
            if entry.get('new_doc_type'):
                print("     Created new document type")

def main():
    parser = argparse.ArgumentParser(description='AI Model Management Utility')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Display information about the current model')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export model configuration to a file')
    export_parser.add_argument('-o', '--output', help='Output file path')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import model configuration from a file')
    import_parser.add_argument('input_file', help='Input file path')
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset a document schema to default')
    reset_parser.add_argument('doc_type', help='Document type (sds, tds, coa)')
    
    # Add rule command
    rule_parser = subparsers.add_parser('add-rule', help='Add an extraction rule for a field')
    rule_parser.add_argument('doc_type', help='Document type (sds, tds, coa)')
    rule_parser.add_argument('field', help='Field name')
    rule_parser.add_argument('pattern', help='Regex pattern for extraction')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show training history')
    
    args = parser.parse_args()
    
    # Initialize AI document processor
    processor = initialize_processor()
    
    # Execute command
    if args.command == 'info':
        display_model_info(processor)
    elif args.command == 'export':
        export_model_config(processor, args.output)
    elif args.command == 'import':
        import_model_config(processor, args.input_file)
    elif args.command == 'reset':
        reset_schema(processor, args.doc_type)
    elif args.command == 'add-rule':
        add_extraction_rule(processor, args.doc_type, args.field, args.pattern)
    elif args.command == 'history':
        show_training_history(processor)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
