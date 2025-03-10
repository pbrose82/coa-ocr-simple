/**
 * Button Manager for COA Intelligence
 * 
 * This script manages button states based on the application state
 * following the specified button management rules.
 */

// Button Manager Module
const ButtonManager = (function() {
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

    // Button elements (will be initialized in init function)
    let chooseFileBtn;
    let extractDataBtn;
    let submitToAlchemyBtn;
    let resetBtn;
    let fileInput;
    let statusMessage;

    /**
     * Initialize the button manager
     */
    function init() {
        // Get button elements
        chooseFileBtn = document.getElementById('choose-file-btn');
        extractDataBtn = document.getElementById('extract-button');
        submitToAlchemyBtn = document.getElementById('submit-button');
        resetBtn = document.getElementById('reset-button');
        fileInput = document.getElementById('file-input');
        statusMessage = document.getElementById('upload-message');

        // Set initial button states
        updateState(AppState.INITIAL);

        console.log('Button Manager initialized');
    }

    /**
     * Update button states based on application state
     * @param {string} state - The new application state
     * @param {string} message - Optional status message to display
     */
    function updateState(state, message = '') {
        currentState = state;
        
        // Update status message if provided and element exists
        if (message && statusMessage) {
            statusMessage.textContent = message;
            statusMessage.style.display = 'block';
        }
        
        // Update button states based on current application state
        switch(state) {
            case AppState.INITIAL:
                // User did not upload a file
                setButtonState(chooseFileBtn, true, 'secondary', true);
                setButtonState(extractDataBtn, false, 'primary', true);
                setButtonState(submitToAlchemyBtn, false, 'primary', false);
                setButtonState(resetBtn, false, 'secondary', true);
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
        
        // Set button type if needed
        // Note: Only modify classes if your buttons use these classes
        if (type === 'primary' && !button.classList.contains('btn-primary')) {
            button.classList.remove('btn-secondary');
            button.classList.add('btn-primary');
        } else if (type === 'secondary' && !button.classList.contains('btn-secondary')) {
            button.classList.remove('btn-primary');
            button.classList.add('btn-secondary');
        }
    }

    /**
     * Get the current application state
     * @returns {string} The current state
     */
    function getCurrentState() {
        return currentState;
    }

    // Public API
    return {
        init: init,
        updateState: updateState,
        getCurrentState: getCurrentState,
        AppState: AppState
    };
})();

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    ButtonManager.init();
});
