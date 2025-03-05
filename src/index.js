// src/index.js
const path = require('path');
const fs = require('fs').promises;
const config = require('../config/default');
const logger = require('./utils/logger');
const OCRProcessor = require('./ocr/processor');
const CoaApiClient = require('./api/coa-api');
const { version } = require('../package.json');

// Log application startup
logger.startup(version);

/**
 * Main application function
 * @param {string} inputDir - Directory with images to process
 * @returns {Promise<void>}
 */
async function main(inputDir) {
  logger.info(`Starting OCR processing for directory: ${inputDir}`);
  
  // Initialize components
  const ocrProcessor = new OCRProcessor();
  const apiClient = new CoaApiClient();
  
  try {
    // Validate input directory
    try {
      await fs.access(inputDir);
    } catch (error) {
      logger.error(`Input directory does not exist: ${inputDir}`);
      process.exit(1);
    }
    
    // Initialize OCR processor
    await ocrProcessor.initialize();
    
    // Process all images in the directory
    const results = await ocrProcessor.processDirectory(inputDir);
    logger.info(`Processed ${results.length} files`);
    
    // Send each result to the API
    let successCount = 0;
    let failureCount = 0;
    
    for (const result of results) {
      try {
        // Validate data before sending
        const validation = ocrProcessor.validateData(result.data);
        
        if (!validation.isValid) {
          logger.warn(`Skipping file ${result.filename} due to missing fields: ${validation.missingFields.join(', ')}`);
          failureCount++;
          continue;
        }
        
        // Send data to API
        await apiClient.sendData(result.data);
        logger.info(`Successfully sent data for file: ${result.filename}`);
        successCount++;
      } catch (error) {
        logger.error(`Failed to process file ${result.filename}: ${error.message}`);
        failureCount++;
      }
    }
    
    // Log summary
    logger.info('Processing complete');
    logger.info(`Success: ${successCount}, Failures: ${failureCount}`);
  } catch (error) {
    logger.error(`Application error: ${error.message}`);
    process.exit(1);
  } finally {
    // Clean up resources
    await ocrProcessor.terminate();
  }
}

// Run the application if called directly
if (require.main === module) {
  // Get input directory from command line arguments
  const inputDir = process.argv[2] || path.resolve(process.cwd(), 'input');
  
  // Run the application
  main(inputDir).catch(error => {
    logger.error(`Unhandled error: ${error.message}`);
    process.exit(1);
  });
}

// Export for testing or programmatic use
module.exports = {
  main,
};
