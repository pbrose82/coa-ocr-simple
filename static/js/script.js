/**
 * Main script for Alchemy OCR Intelligence application
 * This script handles file uploads, OCR processing, and form submissions
 */

// Wait for the DOM to be fully loaded before executing
document.addEventListener('DOMContentLoaded', function() {
    // Define variables for various HTML elements
    const fileInput = document.getElementById('fileInput');
    const fileName = document.getElementById('fileName');
    const fileNameText = document.getElementById('fileNameText');
    const extractButton = document.getElementById('extractButton');
    const results = document.getElementById('results');
    const dataTable = document.getElementById('dataTable');
    const rawText = document.getElementById('rawText');
    const sendToAlchemy = document.getElementById('sendToAlchemy');
    const processingStatus = document.getElementById('processingStatus');
    const statusText = document.getElementById('statusText');
    const progressBar = document.getElementById('progressBar');
    const alchemyRecordLink = document.getElementById('alchemyRecordLink');
    const recordLink = document.getElementById('recordLink');
    const resetButton = document.getElementById('resetButton');
    const dropZone = document.getElementById('dropZone');
    const fileFormat = document.getElementById('fileFormat');
    
    // Initialize UI state
    updateUIState();
    
    // Reset button - refresh the entire page
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            window.location.reload();
        });
    }
    
    // File input change handler
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            // Reset the page state completely when a new file is selected
            resetResults();
            
            // Show file name and update UI state
            if (fileInput.files.length > 0) {
                if (fileNameText) {
                    fileNameText.textContent = fileInput.files[0].name;
                }
                if (fileName) {
                    fileName.style.display = 'flex';
                }
                if (dropZone) {
                    dropZone.classList.add('file-selected');
                }
                
                updateUIState();
            }
        });
    }
    
    // File format change handler
    if (fileFormat) {
        fileFormat.addEventListener('change', function() {
            if (fileFormat.value === 'image') {
                fileInput.accept = ".jpg,.jpeg,.png,.tiff";
            } else {
                fileInput.accept = ".pdf";
            }
        });
    }
    
    // Extract button click handler
    if (extractButton) {
        extractButton.addEventListener('click', function() {
            extractDocument();
        });
    }
    
    // Send to Alchemy button click handler
    if (sendToAlchemy) {
        sendToAlchemy.addEventListener('click', function() {
            sendDataToAlchemy();
        });
    }
    
    // Reset results state
    function resetResults() {
        // Hide results section
        if (results) {
            results.style.display = 'none';
        }
        if (alchemyRecordLink) {
            alchemyRecordLink.style.display = 'none';
        }
        
        // Clear data table and raw text
        if (dataTable) {
            dataTable.innerHTML = '';
        }
        if (rawText) {
            rawText.textContent = '';
        }
        
        // Reset UI state
        updateUIState();
    }
    
    // Update UI state based on current inputs
    function updateUIState() {
        const hasFile = fileInput && fileInput.files && fileInput.files.length > 0;
        
        // Extract button state
        if (extractButton) {
            if (hasFile) {
                extractButton.classList.remove('disabled');
                extractButton.classList.add('active');
                extractButton.disabled = false;
            } else {
                extractButton.classList.add('disabled');
                extractButton.classList.remove('active');
                extractButton.disabled = true;
            }
        }
        
        // Send to Alchemy button
        if (sendToAlchemy) {
            // Only enable if we have extraction results
            const hasResults = results && results.style.display !== 'none';
            
            if (hasResults) {
                sendToAlchemy.classList.add('active');
                sendToAlchemy.disabled = false;
            } else {
                sendToAlchemy.classList.remove('active');
                sendToAlchemy.disabled = true;
            }
        }
    }
    
    // Extract document data
    function extractDocument() {
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            showNotification('Please select a file to extract', 'warning');
            return;
        }
        
        const file = fileInput.files[0];
        const fileTypeMatch = fileFormat && (
            (fileFormat.value === 'image' && file.type.startsWith('image/')) ||
            (fileFormat.value === 'pdf' && file.type === 'application/pdf')
        );
        
        if (fileFormat && !fileTypeMatch) {
            showNotification(`Selected file doesn't match the chosen file type (${fileFormat.value})`, 'error');
            return;
        }
        
        // Clear previous results
        resetResults();
        
        // Show processing status
        if (processingStatus) {
            processingStatus.style.display = 'block';
        }
        if (statusText) {
            statusText.textContent = 'Uploading document...';
        }
        if (progressBar) {
            progressBar.style.width = '10%';
        }
        
        // Set up simulated progress for user feedback
        let progress = 10;
        const progressInterval = setInterval(() => {
            if (progress < 90 && progressBar) {
                progress += Math.random() * 5;
                progressBar.style.width = `${progress}%`;
                
                // Update status text based on progress
                if (statusText) {
                    if (progress > 20 && progress < 40) {
                        statusText.textContent = 'Processing document...';
                    } else if (progress > 40 && progress < 60) {
                        statusText.textContent = 'Extracting text...';
                    } else if (progress > 60 && progress < 80) {
                        statusText.textContent = 'Analyzing data...';
                    }
                }
            }
        }, 1000);
        
        // Prepare form data
        const formData = new FormData();
        formData.append('file', file);
        
        // Send request to extract endpoint
        fetch('/extract', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            clearInterval(progressInterval);
            
            if (!response.ok) {
                throw new Error(`Error: ${response.status} ${response.statusText}`);
            }
            
            return response.json();
        })
        .then(data => {
            // Complete progress bar
            if (progressBar) {
                progressBar.style.width = '100%';
            }
            if (statusText) {
                statusText.textContent = 'Processing complete!';
            }
            
            // Hide processing after delay
            setTimeout(() => {
                if (processingStatus) {
                    processingStatus.style.display = 'none';
                }
            }, 1000);
            
            // Handle error in response
            if (data.error) {
                showNotification(`Error: ${data.error}`, 'error');
                return;
            }
            
            // Display the results
            displayResults(data);
            
            // Update UI state
            updateUIState();
        })
        .catch(error => {
            // Clear interval
            clearInterval(progressInterval);
            
            // Hide processing status
            if (processingStatus) {
                processingStatus.style.display = 'none';
            }
            
            console.error('Error during extraction:', error);
            showNotification(`Error: ${error.message}`, 'error');
        });
    }
    
    // Display extraction results
    function displayResults(data) {
        if (!dataTable || !rawText || !results) {
            console.error('Results elements not found');
            return;
        }
        
        // Clear previous data
        dataTable.innerHTML = '';
        
        // Check if we have any data other than full_text
        const hasData = Object.keys(data).filter(key => key !== 'full_text').length > 0;
        
        if (!hasData) {
            // Create a message row
            const messageRow = document.createElement('tr');
            messageRow.innerHTML = `
                <td colspan="2" class="text-center">
                    <div class="alert alert-warning m-0">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        No structured data could be extracted. See the raw text below.
                    </div>
                </td>
            `;
            dataTable.appendChild(messageRow);
        } else {
            // Loop through data fields (excluding full_text)
            for (const key in data) {
                if (key !== 'full_text') {
                    const value = data[key];
                    
                    // Skip null/undefined values or empty strings
                    if (value === null || value === undefined || value === '') {
                        continue;
                    }
                    
                    // Format the label
                    const formattedKey = key.replace(/_/g, ' ')
                                           .replace(/\b\w/g, l => l.toUpperCase());
                    
                    if (typeof value === 'object') {
                        // Handle nested objects like test_results
                        const row = document.createElement('tr');
                        
                        let objectHtml = '';
                        
                        // Build nested table
                        if (Object.keys(value).length > 0) {
                            objectHtml = '<table class="table table-sm table-bordered mt-2 mb-0">';
                            
                            for (const subKey in value) {
                                const subValue = value[subKey];
                                const subRow = `
                                    <tr>
                                        <td class="fw-medium">${subKey}</td>
                                        <td>${typeof subValue === 'object' ? JSON.stringify(subValue) : subValue}</td>
                                    </tr>
                                `;
                                objectHtml += subRow;
                            }
                            
                            objectHtml += '</table>';
                        } else {
                            objectHtml = '<div class="text-muted">No data available</div>';
                        }
                        
                        row.innerHTML = `
                            <td class="fw-medium">${formattedKey}</td>
                            <td>${objectHtml}</td>
                        `;
                        
                        dataTable.appendChild(row);
                    } else {
                        // Handle simple values
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td class="fw-medium">${formattedKey}</td>
                            <td>${value}</td>
                        `;
                        dataTable.appendChild(row);
                    }
                }
            }
        }
        
        // Set raw text
        if (data.full_text) {
            rawText.textContent = data.full_text;
        } else {
            rawText.textContent = 'No raw text available';
        }
        
        // Show results
        results.style.display = 'block';
    }
    
    // Send extraction data to Alchemy
    function sendDataToAlchemy() {
        if (processingStatus) {
            processingStatus.style.display = 'block';
        }
        if (statusText) {
            statusText.textContent = 'Sending data to Alchemy...';
        }
        if (progressBar) {
            progressBar.style.width = '50%';
        }
        
        // Get the data from the page (using the original data saved from extraction)
        fetch('/send-to-alchemy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({}) // The server already has the data from the last extraction
        })
        .then(response => response.json())
        .then(result => {
            // Hide processing status
            if (processingStatus) {
                processingStatus.style.display = 'none';
            }
            
            if (result.status === 'success') {
                // Show the record link if available
                if (result.record_url && alchemyRecordLink && recordLink) {
                    recordLink.href = result.record_url;
                    recordLink.textContent = `View record ${result.record_id} in Alchemy`;
                    alchemyRecordLink.style.display = 'block';
                } else {
                    showNotification('Data successfully sent to Alchemy!', 'success');
                }
                
                // Disable the send button
                if (sendToAlchemy) {
                    sendToAlchemy.disabled = true;
                    sendToAlchemy.classList.remove('active');
                }
            } else {
                showNotification(`Error: ${result.message || 'Failed to send data to Alchemy'}`, 'error');
            }
        })
        .catch(error => {
            // Hide processing status
            if (processingStatus) {
                processingStatus.style.display = 'none';
            }
            
            console.error('Error sending to Alchemy:', error);
            showNotification(`Error: ${error.message}`, 'error');
        });
    }
    
    // Show notification
    function showNotification(message, type) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : 
                                          type === 'warning' ? 'warning' : 'success'} 
                                  position-fixed`;
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.style.maxWidth = '300px';
        notification.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
        notification.style.animation = 'fadeIn 0.3s ease-out';
        
        // Add icon based on type
        let icon = '';
        if (type === 'error') {
            icon = '<i class="fas fa-exclamation-circle me-2"></i>';
        } else if (type === 'warning') {
            icon = '<i class="fas fa-exclamation-triangle me-2"></i>';
        } else {
            icon = '<i class="fas fa-check-circle me-2"></i>';
        }
        
        notification.innerHTML = icon + message;
        
        // Add to document
        document.body.appendChild(notification);
        
        // Remove after delay
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.5s';
            
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 500);
        }, 4000);
    }
});

// Add keyframe animation to stylesheet
document.addEventListener('DOMContentLoaded', function() {
    const style = document.createElement('style');
    style.innerHTML = `
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    `;
    document.head.appendChild(style);
});
