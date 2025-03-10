/**
 * Button Manager for COA Intelligence
 * 
 * This script manages button states based on the application state
 * following the specified button management rules.
 */

// Button elements
const chooseFileBtn = document.getElementById('choose-file-btn');
const extractDataBtn = document.getElementById('extract-data-btn');
const submitToAlchemyBtn = document.getElementById('submit-to-alchemy-btn');
const resetBtn = document.getElementById('reset-btn');
const fileInput = document.getElementById('file-input');
const progressContainer = document.getElementById('progress-container');
const progressBar = document.getElementById('progress-bar');
const statusMessage = document.getElementById('status-message');
const resultsCard = document.getElementById('results-card');

// Application state enum
const AppState = {
  INITIAL: 'initial',                // No file uploaded
  UPLOADING: 'uploading',            // File upload in progress
  FILE_UPLOADED: 'file_uploaded',    // File upload complete
  EXTRACTING: 'extracting',          // Data extraction in progress
  EXTRACTED: 'extracted',            // Data extraction complete
  SUBMITTING: 'submitting',          // Submitting to Alchemy in progress
  SUBMITTED: 'submitted'             // Successfully submitted to Alchemy
};

// Current application state
let currentState = AppState.INITIAL;
let currentFile = null;

/**
 * Initialize the button manager
 */
function initButtonManager() {
  // Set initial button states
  updateAppState(AppState.INITIAL);
  
  // Setup event listeners
  setupEventListeners();
}

/**
 * Update application state and button visibility/enabled status
 * @param {string} state - The new application state
 * @param {string} message - Optional status message to display
 */
function updateAppState(state, message = '') {
  currentState = state;
  
  // Update status message if provided
  if (message) {
    statusMessage.textContent = message;
    statusMessage.style.display = 'block';
    
    // Set appropriate alert class based on state
    statusMessage.className = 'alert';
    if (state === AppState.SUBMITTED) {
      statusMessage.classList.add('alert-success');
    } else if (state === AppState.INITIAL) {
      statusMessage.style.display = 'none';
    } else {
      statusMessage.classList.add('alert-info');
    }
  }
  
  // Show/hide progress bar based on state
  progressContainer.style.display = 
    (state === AppState.UPLOADING || state === AppState.EXTRACTING || state === AppState.SUBMITTING) 
    ? 'block' : 'none';
  
  // Update progress bar animation based on state
  if (state === AppState.UPLOADING) {
    animateProgressBar(0, 100, 1500); // 1.5 seconds for upload
  } else if (state === AppState.EXTRACTING) {
    animateProgressBar(0, 100, 2500); // 2.5 seconds for extraction
  } else if (state === AppState.SUBMITTING) {
    animateProgressBar(0, 100, 2000); // 2 seconds for submission
  }
  
  // Update button states based on current application state
  switch(state) {
    case AppState.INITIAL:
      // User did not upload a file
      setButtonState(chooseFileBtn, true, 'secondary', true);
      setButtonState(extractDataBtn, false, 'primary', true);
      setButtonState(submitToAlchemyBtn, false, 'primary', false);
      setButtonState(resetBtn, false, 'secondary', true);
      
      // Hide results
      resultsCard.style.display = 'none';
      break;
      
    case AppState.UPLOADING:
      // User uploaded a file – Uploading in progress
      setButtonState(chooseFileBtn, false, 'secondary', true);
      setButtonState(extractDataBtn, false, 'primary', true);
      setButtonState(submitToAlchemyBtn, false, 'primary', false);
      setButtonState(resetBtn, false, 'secondary', true);
      break;
      
    case AppState.FILE_UPLOADED:
      // File is uploaded
      setButtonState(chooseFileBtn, true, 'secondary', true);
      setButtonState(extractDataBtn, true, 'primary', true);
      setButtonState(submitToAlchemyBtn, false, 'primary', false);
      setButtonState(resetBtn, true, 'secondary', true);
      break;
      
    case AppState.EXTRACTING:
      // User clicks on "Extract Data" – Extracting in progress
      setButtonState(chooseFileBtn, false, 'secondary', true);
      setButtonState(extractDataBtn, false, 'primary', true);
      setButtonState(submitToAlchemyBtn, false, 'primary', false);
      setButtonState(resetBtn, false, 'secondary', true);
      break;
      
    case AppState.EXTRACTED:
      // File is extracted
      setButtonState(chooseFileBtn, true, 'secondary', true);
      setButtonState(extractDataBtn, false, 'primary', false);
      setButtonState(submitToAlchemyBtn, true, 'primary', true);
      setButtonState(resetBtn, true, 'secondary', true);
      
      // Show results
      resultsCard.style.display = 'block';
      break;
      
    case AppState.SUBMITTING:
      // User clicks on "Submit to Alchemy" – Sending data in progress
      setButtonState(chooseFileBtn, false, 'secondary', true);
      setButtonState(extractDataBtn, false, 'primary', false);
      setButtonState(submitToAlchemyBtn, false, 'primary', true);
      setButtonState(resetBtn, false, 'secondary', true);
      break;
      
    case AppState.SUBMITTED:
      // File successfully submitted
      setButtonState(chooseFileBtn, false, 'secondary', true);
      setButtonState(extractDataBtn, false, 'primary', false);
      setButtonState(submitToAlchemyBtn, false, 'primary', true);
      setButtonState(resetBtn, true, 'secondary', true);
      break;
  }
}

/**
 * Helper function to set button state
 * @param {HTMLElement} button - The button element
 * @param {boolean} enabled - Whether the button is enabled
 * @param {string} type - The button type ('primary' or 'secondary')
 * @param {boolean} visible - Whether the button is visible
 */
function setButtonState(button, enabled, type, visible) {
  if (!button) return;
  
  // Set visibility
  button.style.display = visible ? 'inline-block' : 'none';
  
  // Set enabled/disabled state
  if (enabled) {
    button.removeAttribute('disabled');
    button.classList.remove('disabled');
  } else {
    button.setAttribute('disabled', 'disabled');
    button.classList.add('disabled');
  }
  
  // Set button type
  button.classList.remove('btn-primary', 'btn-secondary');
  button.classList.add(type === 'primary' ? 'btn-primary' : 'btn-secondary');
}

/**
 * Setup event listeners for buttons
 */
function setupEventListeners() {
  // Choose File button click
  chooseFileBtn.addEventListener('click', () => {
    fileInput.click();
  });
  
  // File input change
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      currentFile = e.target.files[0];
      
      // Start file upload process
      startFileUpload(currentFile);
    }
  });
  
  // Extract Data button click
  extractDataBtn.addEventListener('click', () => {
    // Start extraction process
    startExtraction();
  });
  
  // Submit to Alchemy button click
  submitToAlchemyBtn.addEventListener('click', () => {
    // Start submission process
    startSubmission();
  });
  
  // Reset button click
  resetBtn.addEventListener('click', () => {
    // Reset the application
    resetApplication();
  });
}

/**
 * Start file upload process
 * @param {File} file - The file to upload
 */
function startFileUpload(file) {
  // Update state to uploading
  updateAppState(AppState.UPLOADING, `Uploading ${file.name}...`);
  
  // In a real implementation, you would upload the file to your server
  // For this implementation, we'll simulate the upload with a timeout
  setTimeout(() => {
    // Update state to file uploaded
    updateAppState(AppState.FILE_UPLOADED, `File "${file.name}" uploaded successfully. Click "Extract Data" to process.`);
  }, 1500);
  
  // Integration point: Replace this with your actual file upload code
  // When the upload is complete, call:
  // updateAppState(AppState.FILE_UPLOADED, 'File uploaded successfully');
}

/**
 * Start extraction process
 */
function startExtraction() {
  // Update state to extracting
  updateAppState(AppState.EXTRACTING, 'Extracting data from document...');
  
  // In a real implementation, you would call your OCR service
  // For this implementation, we'll simulate the extraction with a timeout
  setTimeout(() => {
    // Example extracted data
    const extractedData = {
      productName: 'Sample Product',
      thc: '0.3%',
      cbd: '15.2%',
      batchNumber: 'BATCH123',
      testDate: '2025-03-01'
    };
    
    // Display the extracted data
    displayResults(extractedData);
    
    // Update state to extracted
    updateAppState(AppState.EXTRACTED, 'Data extraction complete. Ready to submit to Alchemy.');
  }, 2500);
  
  // Integration point: Replace this with your actual extraction code
  // When the extraction is complete, call:
  // updateAppState(AppState.EXTRACTED, 'Data extraction complete');
}

/**
 * Start submission to Alchemy
 */
function startSubmission() {
  // Update state to submitting
  updateAppState(AppState.SUBMITTING, 'Submitting data to Alchemy...');
  
  // In a real implementation, you would submit to your Alchemy service
  // For this implementation, we'll simulate the submission with a timeout
  setTimeout(() => {
    // Update state to submitted
    updateAppState(AppState.SUBMITTED, 'Data successfully submitted to Alchemy!');
  }, 2000);
  
  // Integration point: Replace this with your actual submission code
  // When the submission is complete, call:
  // updateAppState(AppState.SUBMITTED, 'Submission complete');
}

/**
 * Reset the application to its initial state
 */
function resetApplication() {
  // Clear file input
  fileInput.value = '';
  currentFile = null;
  
  // Clear results
  document.getElementById('results-container').innerHTML = '';
  
  // Reset to initial state
  updateAppState(AppState.INITIAL);
}

/**
 * Display the extracted results
 * @param {Object} data - The extracted data
 */
function displayResults(data) {
  const resultsContainer = document.getElementById('results-container');
  
  // Create a table to display the results
  let html = '<table class="table table-striped">';
  html += '<thead><tr><th>Field</th><th>Value</th></tr></thead>';
  html += '<tbody>';
  
  // Add each field to the table
  for (const [key, value] of Object.entries(data)) {
    // Convert camelCase to Title Case
    const fieldName = key.replace(/([A-Z])/g, ' $1')
      .replace(/^./, str => str.toUpperCase());
    
    html += `<tr><td>${fieldName}</td><td>${value}</td></tr>`;
  }
  
  html += '</tbody></table>';
  
  // Set the HTML
  resultsContainer.innerHTML = html;
}

/**
 * Animate the progress bar
 * @param {number} start - Start percentage
 * @param {number} end - End percentage
 * @param {number} duration - Duration in milliseconds
 */
function animateProgressBar(start, end, duration) {
  const startTime = Date.now();
  
  const updateProgress = () => {
    const currentTime = Date.now();
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const percentage = start + progress * (end - start);
    
    progressBar.style.width = `${percentage}%`;
    
    if (progress < 1) {
      requestAnimationFrame(updateProgress);
    }
  };
  
  updateProgress();
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', initButtonManager);

// Export functions for external use
window.buttonManager = {
  updateAppState,
  resetApplication,
  AppState
};
