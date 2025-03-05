// src/utils/logger.js
const winston = require('winston');
const path = require('path');
const fs = require('fs');
const config = require('../../config/default');

// Ensure log directory exists
if (config.logging.logToFile) {
  const logDir = path.dirname(config.logging.logFilePath);
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
}

// Define log format
const logFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.errors({ stack: true }),
  winston.format.splat(),
  winston.format.json()
);

// Configure transports
const transports = [
  new winston.transports.Console({
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.printf(({ level, message, timestamp, ...metadata }) => {
        let msg = `${timestamp} [${level}]: ${message}`;
        
        // Add metadata if present
        if (Object.keys(metadata).length > 0 && metadata.stack !== undefined) {
          msg += ` - ${metadata.stack}`;
        } else if (Object.keys(metadata).length > 0) {
          msg += ` ${JSON.stringify(metadata)}`;
        }
        
        return msg;
      })
    ),
  }),
];

// Add file transport if enabled
if (config.logging.logToFile) {
  transports.push(
    new winston.transports.File({
      filename: config.logging.logFilePath,
      format: logFormat,
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    })
  );
}

// Create the logger
const logger = winston.createLogger({
  level: config.logging.level,
  format: logFormat,
  defaultMeta: { service: 'coa-ocr' },
  transports,
  exitOnError: false,
});

// Add a method for logging application startup
logger.startup = function(version) {
  this.info(`===== COA OCR Application v${version} starting up =====`);
  this.info(`Environment: ${config.app.environment}`);
  this.info(`Log level: ${config.logging.level}`);
};

module.exports = logger;
