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
    let uploadArea;

    /**
     * Initialize the button manager
     */
    function init() {
        // Get button elements - using your existing IDs
        chooseFileBtn = document.querySelector('.custom-file-upload'); // This is your file select label
        extractDataBtn = document.getElementById('extractButton');
        submitToAlchemyBtn = document.getElementById('sendToAlchemy');
        resetBtn = document.getElementById('resetButton');
        fileInput = document.getElementById('fileInput');
        uploadArea = document.getElementById('dropZone');

        // Set initial button states
        updateState(AppState.INITIAL);

        console.log('Button Manager initialized');
    }

    /**
     * Update button states based on application state
     * @param {string} state - The new application state
     */
    function updateState(state) {
        currentState = state;
        
        // Update button states based on current application state
        switch(state) {
            case AppState.INITIAL:
                // User did not upload a file
                setButtonState(chooseFileBtn, true, 'secondary', true);
                setButtonState(extractDataBtn, false, 'primary', true);
                setButtonState(submitToAlchemyBtn, false, 'primary', false);
                setButtonState(resetBtn, false, 'secondary', true);
                
                // Additional UI state changes
                if (uploadArea) uploadArea.classList.remove('file-selected');
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
        button.style.display = visible ? 'block' : 'none';
        
        // Set enabled/disabled state
        if (enabled) {
            button.removeAttribute('disabled');
            button.classList.remove('disabled');
            
            // For extract and submit buttons, add active class to make them blue
            if ((button === extractDataBtn || button === submitToAlchemyBtn) && type === 'primary') {
                button.classList.add('active');
            }
        } else {
            button.setAttribute('disabled', 'disabled');
            button.classList.add('disabled');
            button.classList.remove('active');
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
    // Initialize button manager after a short delay to ensure all elements are loaded
    setTimeout(function() {
        ButtonManager.init();
    }, 100);
});
