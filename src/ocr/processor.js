// src/ocr/processor.js
const fs = require('fs').promises;
const path = require('path');
const { createWorker } = require('tesseract.js');
const config = require('../../config/default');
const logger = require('../utils/logger');

/**
 * OCR Processor class to handle document processing
 */
class OCRProcessor {
  constructor(options = {}) {
    this.options = {
      ...config.ocr,
      ...options,
    };
    this.worker = null;
  }

  /**
   * Initialize the OCR processor
   */
  async initialize() {
    logger.info('Initializing OCR processor');
    this.worker = await createWorker({
      logger: progress => {
        if (progress.status === 'recognizing text') {
          logger.debug(`OCR Progress: ${progress.progress * 100}%`);
        }
      },
    });
    
    await this.worker.loadLanguage(this.options.tesseractOptions.lang);
    await this.worker.initialize(this.options.tesseractOptions.lang);
    logger.info('OCR processor initialized');
    return this;
  }

  /**
   * Process a single image file
   * @param {string} imagePath - Path to the image file
   * @returns {Promise<Object>} - Extracted data
   */
  async processImage(imagePath) {
    if (!this.worker) {
      await this.initialize();
    }

    logger.info(`Processing image: ${imagePath}`);
    
    try {
      // Perform OCR
      const { data } = await this.worker.recognize(imagePath);
      
      // Extract and structure the data
      const extractedData = this.extractStructuredData(data);
      
      logger.info(`Successfully processed image: ${imagePath}`);
      return extractedData;
    } catch (error) {
      logger.error(`Error processing image ${imagePath}: ${error.message}`);
      throw error;
    }
  }

  /**
   * Extract structured data from OCR result
   * @param {Object} ocrData - Raw OCR data
   * @returns {Object} - Structured data
   */
  extractStructuredData(ocrData) {
    // This is where you would implement your specific data extraction logic
    // based on the format of your documents
    
    // Example implementation:
    const text = ocrData.text;
    const lines = text.split('\n').filter(line => line.trim());
    
    // Parse the extracted text into structured data
    // This is a simplistic example - you would customize this based on your document format
    const result = {
      rawText: text,
      extractedFields: {},
    };

    // Example field extraction (modify based on your document structure)
    const fieldPatterns = {
      field1: /Field1:\s*([^\n]+)/i,
      field2: /Field2:\s*([^\n]+)/i,
      field3: /Field3:\s*([^\n]+)/i,
      optionalField1: /OptField1:\s*([^\n]+)/i,
      optionalField2: /OptField2:\s*([^\n]+)/i,
    };

    // Extract fields using regex patterns
    Object.entries(fieldPatterns).forEach(([fieldName, pattern]) => {
      const match = text.match(pattern);
      if (match && match[1]) {
        result.extractedFields[fieldName] = match[1].trim();
      }
    });

    return result;
  }

  /**
   * Process multiple images in a directory
   * @param {string} dirPath - Directory containing images
   * @returns {Promise<Array<Object>>} - Array of extracted data
   */
  async processDirectory(dirPath) {
    logger.info(`Processing directory: ${dirPath}`);
    
    try {
      const files = await fs.readdir(dirPath);
      const imageFiles = files.filter(file => {
        const ext = path.extname(file).toLowerCase();
        return ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.pdf'].includes(ext);
      });
      
      logger.info(`Found ${imageFiles.length} image files to process`);
      
      const results = [];
      for (const file of imageFiles) {
        const imagePath = path.join(dirPath, file);
        const result = await this.processImage(imagePath);
        results.push({
          filename: file,
          data: result,
        });
      }
      
      return results;
    } catch (error) {
      logger.error(`Error processing directory ${dirPath}: ${error.message}`);
      throw error;
    }
  }

  /**
   * Validate the extracted data against required fields
   * @param {Object} data - Extracted data
   * @returns {Object} - Validation result
   */
  validateData(data) {
    const { requiredFields } = config.api.fields;
    const missingFields = [];
    
    requiredFields.forEach(field => {
      if (!data.extractedFields[field]) {
        missingFields.push(field);
      }
    });
    
    return {
      isValid: missingFields.length === 0,
      missingFields,
    };
  }

  /**
   * Clean up resources
   */
  async terminate() {
    if (this.worker) {
      logger.info('Terminating OCR processor');
      await this.worker.terminate();
      this.worker = null;
    }
  }
}

module.exports = OCRProcessor;
