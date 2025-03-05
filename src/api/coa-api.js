// src/api/coa-api.js
const axios = require('axios');
const config = require('../../config/default');
const logger = require('../utils/logger');

/**
 * COA API client for sending extracted data
 */
class CoaApiClient {
  constructor(options = {}) {
    this.options = {
      ...config.api,
      ...options,
    };

    // Create axios instance with default configuration
    this.client = axios.create({
      baseURL: this.options.coaEndpoint,
      timeout: this.options.timeout,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.options.apiKey}`,
      },
    });

    // Add response interceptor for logging
    this.client.interceptors.response.use(
      response => {
        logger.debug(`API response status: ${response.status}`);
        return response;
      },
      error => {
        if (error.response) {
          logger.error(`API error: ${error.response.status} - ${JSON.stringify(error.response.data)}`);
        } else if (error.request) {
          logger.error(`API request error: ${error.message}`);
        } else {
          logger.error(`API setup error: ${error.message}`);
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * Send extracted data to the COA API
   * @param {Object} data - The extracted data to send
   * @returns {Promise<Object>} - API response
   */
  async sendData(data) {
    logger.info('Sending data to COA API');
    
    // Format the data according to the API requirements
    const formattedData = this.formatDataForApi(data);
    
    // Validate the data before sending
    const { isValid, missingFields } = this.validateData(formattedData);
    if (!isValid) {
      const error = new Error(`Missing required fields: ${missingFields.join(', ')}`);
      logger.error(error.message);
      throw error;
    }
    
    try {
      // Implement retry logic
      let lastError;
      for (let attempt = 1; attempt <= this.options.retries; attempt++) {
        try {
          logger.info(`API request attempt ${attempt}/${this.options.retries}`);
          const response = await this.client.post('/submit', formattedData);
          logger.info('Data successfully sent to COA API');
          return response.data;
        } catch (error) {
          lastError = error;
          
          // Check if we should retry
          const shouldRetry = this.shouldRetryRequest(error, attempt);
          if (!shouldRetry) {
            throw error;
          }
          
          // Wait before retrying
          const delayMs = this.getRetryDelay(attempt);
          logger.info(`Retrying in ${delayMs}ms...`);
          await new Promise(resolve => setTimeout(resolve, delayMs));
        }
      }
      
      // If we've exhausted all retries
      throw lastError;
    } catch (error) {
      logger.error(`Failed to send data to COA API: ${error.message}`);
      throw error;
    }
  }

  /**
   * Format extracted data for the API
   * @param {Object} data - Extracted data from OCR
   * @returns {Object} - Formatted data for API
   */
  formatDataForApi(data) {
    // This method maps the extracted OCR data to the format expected by the API
    // Customize this based on your API's requirements
    
    const { requiredFields, optionalFields } = config.api.fields;
    const formattedData = {
      timestamp: new Date().toISOString(),
      source: 'OCR',
      data: {},
    };
    
    // Add required fields
    requiredFields.forEach(field => {
      if (data.extractedFields[field]) {
        formattedData.data[field] = data.extractedFields[field];
      }
    });
    
    // Add optional fields if they exist
    optionalFields.forEach(field => {
      if (data.extractedFields[field]) {
        formattedData.data[field] = data.extractedFields[field];
      }
    });
    
    return formattedData;
  }

  /**
   * Validate the data against API requirements
   * @param {Object} data - The formatted data
   * @returns {Object} - Validation result
   */
  validateData(data) {
    const { requiredFields } = config.api.fields;
    const missingFields = [];
    
    requiredFields.forEach(field => {
      if (!data.data[field]) {
        missingFields.push(field);
      }
    });
    
    return {
      isValid: missingFields.length === 0,
      missingFields,
    };
  }

  /**
   * Determine if a failed request should be retried
   * @param {Error} error - The error that occurred
   * @param {number} attempt - Current attempt number
   * @returns {boolean} - Whether to retry the request
   */
  shouldRetryRequest(error, attempt) {
    // Don't retry if we've reached max retries
    if (attempt >= this.options.retries) {
      return false;
    }
    
    // Retry on network errors or specific HTTP status codes
    if (!error.response) {
      // Network error, timeout, etc.
      return true;
    }
    
    // Retry on 429 (Too Many Requests) or 5xx server errors
    const status = error.response.status;
    return status === 429 || (status >= 500 && status < 600);
  }

  /**
   * Calculate delay before retry using exponential backoff
   * @param {number} attempt - Current attempt number
   * @returns {number} - Delay in milliseconds
   */
  getRetryDelay(attempt) {
    // Implement exponential backoff with jitter
    const baseDelay = 1000; // 1 second
    const maxDelay = 30000; // 30 seconds
    
    // Calculate exponential backoff
    let delay = baseDelay * Math.pow(2, attempt - 1);
    
    // Add jitter (±20%)
    const jitter = delay * 0.2 * (Math.random() - 0.5);
    delay += jitter;
    
    // Cap at maximum delay
    return Math.min(delay, maxDelay);
  }
}

module.exports = CoaApiClient;
