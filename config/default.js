// config/default.js
module.exports = {
  app: {
    port: process.env.PORT || 3000,
    environment: process.env.NODE_ENV || 'development',
  },
  ocr: {
    // OCR specific settings
    tempDir: process.env.OCR_TEMP_DIR || './temp',
    outputDir: process.env.OCR_OUTPUT_DIR || './output',
    // Add any Tesseract or other OCR engine settings here
    tesseractOptions: {
      lang: process.env.OCR_LANG || 'eng',
    },
  },
  api: {
    // API integration settings
    coaEndpoint: process.env.COA_API_ENDPOINT || 'https://api.example.com',
    apiKey: process.env.COA_API_KEY,
    timeout: parseInt(process.env.API_TIMEOUT || '30000', 10),
    retries: parseInt(process.env.API_RETRIES || '3', 10),
    // Add fields that will be sent to the API
    fields: {
      requiredFields: ['field1', 'field2', 'field3'],
      optionalFields: ['optionalField1', 'optionalField2'],
    },
  },
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    logToFile: process.env.LOG_TO_FILE === 'true',
    logFilePath: process.env.LOG_FILE_PATH || './logs/app.log',
  },
};
