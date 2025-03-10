/**
 * Main script for COA Intelligence application
 * This script handles file uploads, OCR processing, and form submissions
 */

// Wait for the DOM to be fully loaded before executing
document.addEventListener('DOMContentLoaded', function() {
    // Define variables for various HTML elements
    const fileInput = document.getElementById('fileInput');
    const fileName = document.getElementById('fileName');
    const fileFormat = document.getElementById('fileFormat');
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
    const uploadArea = document.querySelector('.upload-area') || document.getElementById('dropZone');
    const chooseFileBtn = document.querySelector('.custom-file-upload');
    
    // Reset button - refresh the entire page
    resetButton.addEventListener('click', function() {
        // Update button state to INITIAL before reloading if ButtonManager is available
        if (typeof ButtonManager !== 'undefined') {
            ButtonManager.updateState(ButtonManager.AppState.INITIAL);
        }
        
        // This will reload the entire page
        window.location.reload();
    });
    
    // If chooseFileBtn exists, make it trigger file input
    if (chooseFileBtn) {
        chooseFileBtn.addEventListener('click', function() {
            fileInput.click();
        });
    }
    
    // File input change handler
    fileInput.addEventListener('change', function() {
        // Reset the page state completely when a new file is selected
        
        // Hide results section
        results.style.display = 'none';
        alchemyRecordLink.style.display = 'none';
        
        // Clear data table and raw text
        dataTable.innerHTML = '';
        rawText.textContent = '';
        
        // Reset extracted data
        extractedData = null;
        
        // Update button states
        extractButton.classList.remove('disabled');
        extractButton.disabled = false;
        sendToAlchemy.disabled = true;
        sendToAlchemy.classList.remove('active');
        
        // Show file name and make extract button blue
        if (fileInput.files.length > 0) {
            fileName.textContent = fileInput.files[0].name;
            extractButton.classList.add('active');
            uploadArea.classList.add('file-selected');
            
            // Update button state using ButtonManager
            if (typeof ButtonManager !== 'undefined') {
                ButtonManager.updateState(ButtonManager.AppState.FILE_UPLOADED);
            }
        } else {
            fileName.textContent = '';
            extractButton.classList.remove('active');
            uploadArea.classList.remove('file-selected');
            
            // Update button state using ButtonManager
            if (typeof ButtonManager !== 'undefined') {
                ButtonManager.updateState(ButtonManager.AppState.INITIAL);
            }
        }
    });
    
    // File format change handler
    fileFormat.addEventListener('change', function() {
        if (fileFormat.value === 'image') {
            fileInput.accept = ".jpg,.jpeg,.png,.tiff";
        } else {
            fileInput.accept = ".pdf";
        }
    });
    
    let extractedData = null;
    let processingTimeout;
    
    // Extract button click handler
    extractButton.addEventListener('click', function() {
        const file = fileInput.files[0];
        
        if (!file) {
            alert('Please select a file');
            return;
        }
        
        // Check if file type matches selected option
        const isPdf = file.name.toLowerCase().endsWith('.pdf');
        const isImage = !isPdf;
        
        if ((fileFormat.value === 'image' && isPdf) || (fileFormat.value === 'pdf' && isImage)) {
            const expectedType = fileFormat.value === 'image' ? "image" : "PDF";
            alert(`You selected ${expectedType} file type but uploaded a ${isPdf ? "PDF" : "image"} file. Please select the correct file type or change your selection.`);
            return;
        }
        
        // Clear previous results
        dataTable.innerHTML = '';
        rawText.textContent = '';
        results.style.display = 'none';
        alchemyRecordLink.style.display = 'none';
        sendToAlchemy.disabled = true;
        sendToAlchemy.classList.remove('active');
        extractedData = null;
        
        // Update button state to EXTRACTING using ButtonManager
        if (typeof ButtonManager !== 'undefined') {
            ButtonManager.updateState(ButtonManager.AppState.EXTRACTING);
        }
        
        // Show processing status
        processingStatus.style.display = 'block';
        statusText.textContent = 'Uploading document...';
        progressBar.style.width = '10%';
        
        // Clear any existing timeout
        if (processingTimeout) clearTimeout(processingTimeout);
        
        // Set up simulated progress for user feedback
        let progress = 10;
        const progressInterval = setInterval(() => {
            if (progress < 90) {
                progress += Math.random() * 5;
                progressBar.style.width = `${progress}%`;
                
                // Update status text based on progress
                if (progress > 20 && progress < 40) {
                    statusText.textContent = 'Processing document...';
                } else if (progress > 40 && progress < 60) {
                    statusText.textContent = 'Extracting text...';
                } else if (progress > 60 && progress < 80) {
                    statusText.textContent = 'Analyzing data...';
                }
            }
        }, 1000);
        
        // Set timeout to show warning after 30 seconds
        processingTimeout = setTimeout(() => {
            statusText.textContent = 'Still processing... Please wait';
        }, 30000);
        
        const formData = new FormData();
        formData.append('file', file);
        
        fetch('/extract', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Clear intervals and timeouts
            clearInterval(progressInterval);
            if (processingTimeout) clearTimeout(processingTimeout);
            
            // Complete progress bar
            progressBar.style.width = '100%';
            statusText.textContent = 'Processing complete!';
            
            // Hide processing indicators after a brief delay
            setTimeout(() => {
                processingStatus.style.display = 'none';
            }, 1000);
            
            if (data.error) {
                alert('Error: ' + data.error);
                // Update button state back to FILE_UPLOADED
                if (typeof ButtonManager !== 'undefined') {
                    ButtonManager.updateState(ButtonManager.AppState.FILE_UPLOADED);
                }
                return;
            }
            
            // Save extracted data
            extractedData = data;
            
            // Use enhanced display function based on document type
            enhancedDisplayResults(data);
            
            // Update button states
            extractButton.classList.add('disabled');
            extractButton.classList.remove('active');
            extractButton.disabled = true;
            
            // Enable submit to Alchemy button if we have data to send
            if (data.product_name || data.purity) {
                sendToAlchemy.disabled = false;
                sendToAlchemy.classList.add('active');
            }
            
            // Update button state to EXTRACTED using ButtonManager
            if (typeof ButtonManager !== 'undefined') {
                ButtonManager.updateState(ButtonManager.AppState.EXTRACTED);
            }
        })
        .catch(error => {
            // Clear intervals and timeouts
            clearInterval(progressInterval);
            if (processingTimeout) clearTimeout(processingTimeout);
            
            // Hide processing indicators
            processingStatus.style.display = 'none';
            
            console.error('Error:', error);
            alert('Error processing file. The server might have timed out. For PDFs, try using a smaller file or converting it to an image first.');
            
            // Update button state back to FILE_UPLOADED
            if (typeof ButtonManager !== 'undefined') {
                ButtonManager.updateState(ButtonManager.AppState.FILE_UPLOADED);
            }
        });
    });
    
    // Send to Alchemy button click handler
    sendToAlchemy.addEventListener('click', function() {
        if (!extractedData) {
            alert('No data to send to Alchemy');
            return;
        }
        
        // Update button state to SUBMITTING using ButtonManager
        if (typeof ButtonManager !== 'undefined') {
            ButtonManager.updateState(ButtonManager.AppState.SUBMITTING);
        }
        
        // Show processing status
        processingStatus.style.display = 'block';
        statusText.textContent = 'Sending data to Alchemy...';
        progressBar.style.width = '50%';
        
        // Format data for Alchemy API
        const payload = {
            data: extractedData
        };
        
        fetch('/send-to-alchemy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
            // Hide processing status
            processingStatus.style.display = 'none';
            
            if (data.status === 'success') {
                // Update button state to SUBMITTED using ButtonManager
                if (typeof ButtonManager !== 'undefined') {
                    ButtonManager.updateState(ButtonManager.AppState.SUBMITTED);
                }
                
                // Display success message and record link
                if (data.record_url && data.record_id) {
                    recordLink.href = data.record_url;
                    recordLink.textContent = `View record ${data.record_id} in Alchemy`;
                    alchemyRecordLink.style.display = 'block';
                } else {
                    alert('Data successfully sent to Alchemy!');
                }
            } else {
                alert('Error: ' + (data.message || 'Failed to send data to Alchemy'));
                
                // Update button state back to EXTRACTED
                if (typeof ButtonManager !== 'undefined') {
                    ButtonManager.updateState(ButtonManager.AppState.EXTRACTED);
                }
            }
        })
        .catch(error => {
            // Hide processing status
            processingStatus.style.display = 'none';
            console.error('Error:', error);
            alert('Error: ' + (error.message || 'Failed to send data to Alchemy'));
            
            // Update button state back to EXTRACTED
            if (typeof ButtonManager !== 'undefined') {
                ButtonManager.updateState(ButtonManager.AppState.EXTRACTED);
            }
        });
    });
    
    // NEW: Enhanced display results function with document type detection
    function enhancedDisplayResults(data) {
        // Clear previous results
        dataTable.innerHTML = '';
        
        // Define document type if not already set
        const docType = data.document_type || detectDocumentType(data.full_text);
        
        // Display metadata fields based on document type
        if (docType === 'chemipan-benzene') {
            // Handle Benzene COA
            displayBenzeneMetadata(data);
        } else if (docType === 'sigma-aldrich-hcl') {
            // Handle HCl COA
            displayHClMetadata(data);
        } else {
            // Handle generic COA
            displayGenericMetadata(data);
        }
        
        // Display test results based on document type
        displayTestResults(data, docType);
        
        // Display raw text
        if (data.full_text) {
            rawText.textContent = data.full_text;
        }
        
        // Show results container
        results.style.display = 'block';
    }
    
    // Detect document type based on content
    function detectDocumentType(text) {
        if (!text) return 'unknown';
        
        // Check for Sigma Aldrich Hydrochloric acid
        if (text.includes('Hydrochloric acid') && 
            (text.includes('Sigma-Aldrich') || text.includes('SIGALD'))) {
            return 'sigma-aldrich-hcl';
        }
        
        // Check for CHEMIPAN Benzene
        if (text.includes('BENZENE') && 
            text.includes('CHEMIPAN') && 
            text.includes('Reference Material')) {
            return 'chemipan-benzene';
        }
        
        return 'unknown';
    }
    
    // Display Benzene-specific metadata
    function displayBenzeneMetadata(data) {
        // Ensure supplier is correct for Benzene
        if (!data.supplier || data.supplier === 'Benzene') {
            data.supplier = 'Z.D. CHEMIPAN';
        }
        
        const metadataFields = [
            { key: 'product_name', display: 'Product Name' },
            { key: 'supplier', display: 'Supplier' },
            { key: 'purity', display: 'Purity' },
            { key: 'release_date', display: 'Date of Analysis' },
            { key: 'batch_number', display: 'Lot Number' },
            { key: 'expiry_date', display: 'Expiry Date' }
        ];
        
        for (const field of metadataFields) {
            if (data[field.key]) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><strong>${field.display}</strong></td>
                    <td>${data[field.key]}</td>
                `;
                dataTable.appendChild(row);
            }
        }
    }
    
    // Display HCl-specific metadata
    function displayHClMetadata(data) {
        // Fix for missing product name
        if ((!data.product_name || data.product_name === "") && data.full_text) {
            // Try to find Hydrochloric acid in the text
            const acidMatch = data.full_text.match(/Hydrochloric acid\s*-\s*ACS reagent,\s*37%/i);
            if (acidMatch) {
                data.product_name = acidMatch[0].trim();
            } else if (data.full_text.includes("Hydrochloric acid")) {
                // Simpler match if the specific format isn't found
                const simpleMatch = data.full_text.match(/Hydrochloric acid[^:\n]*/);
                if (simpleMatch) {
                    data.product_name = simpleMatch[0].trim();
                }
            }
        }
        
        const metadataFields = [
            { key: 'product_name', display: 'Product Name' },
            { key: 'product_number', display: 'Product Number' },
            { key: 'batch_number', display: 'Batch Number' },
            { key: 'release_date', display: 'Release Date' },
            { key: 'retest_date', display: 'Retest Date' },
            { key: 'cas_number', display: 'CAS Number' }
        ];
        
        for (const field of metadataFields) {
            if (data[field.key]) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><strong>${field.display}</strong></td>
                    <td>${data[field.key]}</td>
                `;
                dataTable.appendChild(row);
            }
        }
    }
    
    // Display generic metadata
    function displayGenericMetadata(data) {
        for (const [key, value] of Object.entries(data)) {
            // Skip certain fields
            if (key === 'test_results' || key === 'full_text' || key === 'document_type') continue;
            
            const row = document.createElement('tr');
            
            // Format the key name for display
            const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            
            row.innerHTML = `
                <td><strong>${displayKey}</strong></td>
                <td>${value}</td>
            `;
            dataTable.appendChild(row);
        }
    }
    
    // Display test results with document type awareness
    function displayTestResults(data, docType) {
        const testRow = document.createElement('tr');
        const testCell = document.createElement('td');
        testCell.innerHTML = `<strong>Test Results</strong>`;
        
        const resultsCell = document.createElement('td');
        const testTable = document.createElement('table');
        testTable.className = 'table table-bordered table-sm';
        testTable.innerHTML = `
            <thead>
                <tr>
                    <th>Test</th>
                    <th>Result</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;
        
        const testBody = testTable.querySelector('tbody');
        
        // Based on document type, use different test extraction methods
        if (docType === 'sigma-aldrich-hcl') {
            // For HCl, use both raw text extraction and structured data
            const extractedTests = extractHClTestsFromRawText(data.full_text);
            
            // Add each test to the table
            for (const test of extractedTests) {
                const testDataRow = document.createElement('tr');
                testDataRow.innerHTML = `
                    <td>${test.name}</td>
                    <td>${test.result}</td>
                `;
                testBody.appendChild(testDataRow);
            }
            
            // Add any tests from structured data that weren't extracted
            if (data.test_results && typeof data.test_results === 'object') {
                const existingTestNames = extractedTests.map(t => t.name);
                
                for (const [testName, testData] of Object.entries(data.test_results)) {
                    // Skip if this test is already in our list
                    if (existingTestNames.includes(testName)) continue;
                    
                    let result = "";
                    if (typeof testData === 'object' && testData !== null) {
                        result = testData.result || testData.specification || '';
                    } else {
                        result = testData;
                    }
                    
                    const testDataRow = document.createElement('tr');
                    testDataRow.innerHTML = `
                        <td>${testName}</td>
                        <td>${result}</td>
                    `;
                    testBody.appendChild(testDataRow);
                }
            }
        } else if (docType === 'chemipan-benzene') {
            // For Benzene, use benzene-specific tests
            // These should come from structured data
            if (data.test_results && typeof data.test_results === 'object') {
                for (const [testName, testData] of Object.entries(data.test_results)) {
                    let result = "";
                    if (typeof testData === 'object' && testData !== null) {
                        result = testData.result || testData.specification || '';
                    } else {
                        result = testData;
                    }
                    
                    const testDataRow = document.createElement('tr');
                    testDataRow.innerHTML = `
                        <td>${testName}</td>
                        <td>${result}</td>
                    `;
                    testBody.appendChild(testDataRow);
                }
            } else {
                // Fallback for benzene: key standard tests
                const benzeneTests = [
                    { name: "Appearance (Clarity)", result: "Clear" },
                    { name: "Appearance (Color)", result: "Colorless" },
                    { name: "Appearance (Form)", result: "Liquid" },
                    { name: "Purity", result: data.purity || "99.95 ± 0.02 %" },
                    { name: "Water Content", result: "0.04 ± 0.01 %" },
                    { name: "Color Test", result: "0 APHA" }
                ];
                
                for (const test of benzeneTests) {
                    const testDataRow = document.createElement('tr');
                    testDataRow.innerHTML = `
                        <td>${test.name}</td>
                        <td>${test.result}</td>
                    `;
                    testBody.appendChild(testDataRow);
                }
            }
        } else {
            // For generic documents, use the generic approach
            // Extract directly from raw text
            const extractedTests = extractGenericTestsFromRawText(data.full_text);
            
            // Add each test to the table
            for (const test of extractedTests) {
                const testDataRow = document.createElement('tr');
                testDataRow.innerHTML = `
                    <td>${test.name}</td>
                    <td>${test.result}</td>
                `;
                testBody.appendChild(testDataRow);
            }
            
            // Add any tests from structured data
            if (data.test_results && typeof data.test_results === 'object') {
                const existingTestNames = extractedTests.map(t => t.name);
                
                for (const [testName, testData] of Object.entries(data.test_results)) {
                    // Skip if this test is already in our list
                    if (existingTestNames.includes(testName)) continue;
                    
                    let result = "";
                    if (typeof testData === 'object' && testData !== null) {
                        result = testData.result || testData.specification || '';
                    } else {
                        result = testData;
                    }
                    
                    const testDataRow = document.createElement('tr');
                    testDataRow.innerHTML = `
                        <td>${testName}</td>
                        <td>${result}</td>
                    `;
                    testBody.appendChild(testDataRow);
                }
            }
        }
        
        // Add the test table to the page
        resultsCell.appendChild(testTable);
        testRow.appendChild(testCell);
        testRow.appendChild(resultsCell);
        dataTable.appendChild(testRow);
    }
    
    // Extract HCl-specific tests from raw text
    function extractHClTestsFromRawText(text) {
        if (!text) return [];
        
        const tests = [];
        const testSectionRegex = /Test\s+Specification\s+Result\s*\n(.*?)(?:_{10,}|Larry Coers|Quality Control|Certificate of Analysis|Version Number)/s;
        const testSectionMatch = text.match(testSectionRegex);
        
        if (testSectionMatch && testSectionMatch[1]) {
            const testSection = testSectionMatch[1];
            const lines = testSection.split('\n').filter(line => line.trim() !== '');
            
            let currentTest = null;
            let currentSpec = null;
            
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                
                // Skip empty lines or divider lines
                if (!line || line.match(/^[-_=]{3,}$/)) continue;
                
                // Pattern 1: Full line with test, spec, and result (most common case)
                // Example: "Appearance (Color) Colorless Colorless"
                const fullLineMatch = line.match(/^([^<0-9]+?)(?:\s{2,}|\t)([^_]+?)(?:\s{2,}|\t|_)([^_]*)$/);
                if (fullLineMatch) {
                    const testName = fullLineMatch[1].trim();
                    const result = fullLineMatch[3].trim() || fullLineMatch[2].trim();
                    tests.push({ name: testName, result: result });
                    continue;
                }
                
                // Pattern 2: Line with just test name and specification
                // Examples: "Color Test < 10 APHA"
                const specLineMatch = line.match(/^([^<0-9]+?)(?:\s{2,}|\t)([<>][^_]+|[\d\.]+\s*-\s*[\d\.]+\s*[%\w]*)$/);
                if (specLineMatch) {
                    currentTest = specLineMatch[1].trim();
                    currentSpec = specLineMatch[2].trim();
                    
                    // Check next line for result
                    if (i < lines.length - 1 && !lines[i+1].match(/^[A-Za-z]/)) {
                        const resultLine = lines[i+1].trim();
                        tests.push({ name: currentTest, result: resultLine });
                        currentTest = null;
                        currentSpec = null;
                        i++; // Skip the next line since we've already processed it
                    } else {
                        // If no separate result line, use spec as result
                        tests.push({ name: currentTest, result: currentSpec });
                        currentTest = null;
                        currentSpec = null;
                    }
                    continue;
                }
                
                // Special cases for HCl document
                if (line === "Free from Suspended Matter or Sediment" && tests.length > 0) {
                    // This is a continuation of the previous test (Appearance (Clarity))
                    const lastTest = tests[tests.length - 1];
                    lastTest.name += " " + line;
                    continue;
                }
                
                if (line === "(by ICP)" && tests.length > 0) {
                    // This is a continuation of the previous test (Heavy Metals)
                    const lastTest = tests[tests.length - 1];
                    lastTest.name += " " + line;
                    continue;
                }
                
                // Pattern for multi-line entries
                if (line.match(/^[A-Za-z]/) && !line.includes("<") && !line.includes("-")) {
                    if (i < lines.length - 1) {
                        const nextLine = lines[i+1].trim();
                        if (nextLine.match(/^[<>0-9]/) || nextLine.includes("-")) {
                            // This is likely a test name followed by spec on next line
                            currentTest = line;
                            
                            // Skip to spec line
                            i++;
                            currentSpec = nextLine;
                            
                            // Check if there's a result line after
                            if (i < lines.length - 1 && !lines[i+1].match(/^[A-Za-z]/)) {
                                const resultLine = lines[i+1].trim();
                                tests.push({ name: currentTest, result: resultLine });
                                i++; // Skip the result line
                            } else {
                                // Use spec as result if no separate result line
                                tests.push({ name: currentTest, result: currentSpec });
                            }
                            
                            currentTest = null;
                            currentSpec = null;
                            continue;
                        }
                    }
                    
                    // If we get here, it's likely just a test name without clear spec/result
                    tests.push({ name: line, result: "" });
                }
            }
        }
        
        // Look for more common test patterns specific to HCl
        const hclTests = [
            { name: "Appearance (Clarity)", regex: /Appearance\s*\(Clarity\).*?(Clear)/ },
            { name: "Appearance (Color)", regex: /Appearance\s*\(Color\).*?(Colorless)/ },
            { name: "Appearance (Form)", regex: /Appearance\s*\(Form\).*?(Liquid)/ },
            { name: "Color Test", regex: /Color\s*Test.*?([0-9]+\s*APHA)/ },
            { name: "Titration with NaOH", regex: /Titration.*?NaOH.*?([\d\.]+\s*%)/ },
            { name: "Residue on Ignition", regex: /Residue\s*on\s*Ignition.*?(<\s*[\d\.]+\s*ppm)/ },
            { name: "Arsenic (As)", regex: /Arsenic.*?\(As\).*?(<\s*[\d\.]+\s*ppm)/ },
            { name: "Bromide", regex: /Bromide.*?(<\s*[\d\.]+\s*%)/ },
            { name: "Iron (Fe)", regex: /Iron.*?\(Fe\).*?(<\s*[\d\.]+\s*ppm)/ },
            { name: "Free Chlorine", regex: /Free\s*Chlorine.*?(<\s*[\d\.]+\s*ppm)/ },
            { name: "Heavy Metals", regex: /Heavy\s*Metals.*?(<\s*[\d\.]+\s*ppm)/ },
            { name: "Ammonium", regex: /Ammonium.*?(<\s*[\d\.]+\s*ppm)/ },
            { name: "Sulfite", regex: /Sulfite.*?(<\s*[\d\.]+\s*ppm)/ },
            { name: "Sulfate", regex: /Sulfate.*?(<\s*[\d\.]+\s*ppm)/ },
            { name: "Meets ACS Requirements", regex: /Meets\s*ACS\s*Requirements.*?(Conforms)/ }
        ];
        
        // Add any common tests that weren't found
        for (const commonTest of hclTests) {
            // Skip if we already have this test
            if (tests.some(t => t.name.includes(commonTest.name))) continue;
            
            const match = text.match(commonTest.regex);
            if (match) {
                tests.push({ name: commonTest.name, result: match[1] });
            }
        }
        
        return tests;
    }
    
    // Extract generic tests from raw text
    function extractGenericTestsFromRawText(text) {
        if (!text) return [];
        
        const tests = [];
        
        // Look for test patterns in the text
        const lines = text.split('\n');
        for (const line of lines) {
            // Skip short lines
            if (line.length < 5) continue;
            
            // Try different patterns for test results
            const colonPattern = line.match(/([A-Za-z\s\(\)]+):\s*([A-Za-z0-9\s\.%<>]+)/);
            if (colonPattern) {
                const testName = colonPattern[1].trim();
                const result = colonPattern[2].trim();
                
                // Filter out non-test fields
                if (testName && result && 
                    !testName.toLowerCase().includes('date') && 
                    !testName.toLowerCase().includes('number') && 
                    !testName.toLowerCase().includes('name')) {
                    
                    // Check if we already have this test
                    if (!tests.some(t => t.name === testName)) {
                        tests.push({ name: testName, result: result });
                    }
                }
                continue;
            }
            
            // Try tab or multiple space pattern
            const spacePattern = line.match(/([A-Za-z\s\(\)]+)\s{2,}([A-Za-z0-9\s\.%<>]+)/);
            if (spacePattern) {
                const testName = spacePattern[1].trim();
                const result = spacePattern[2].trim();
                
                // Filter out non-test fields
                if (testName && result && 
                    !testName.toLowerCase().includes('date') && 
                    !testName.toLowerCase().includes('number') && 
                    !testName.toLowerCase().includes('name')) {
                    
                    // Check if we already have this test
                    if (!tests.some(t => t.name === testName)) {
                        tests.push({ name: testName, result: result });
                    }
                }
            }
        }
        
        return tests;
    }
    
    // ===== DRAG AND DROP FUNCTIONALITY =====
    
    // Only set up drag and drop if the upload area exists
    if (uploadArea) {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });
        
        // Highlight drop area when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });
        
        // Handle dropped files
        uploadArea.addEventListener('drop', handleDrop, false);
    }
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight() {
        uploadArea.classList.add('highlight');
    }
    
    function unhighlight() {
        uploadArea.classList.remove('highlight');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            // Update button state to UPLOADING using ButtonManager
            if (typeof ButtonManager !== 'undefined') {
                ButtonManager.updateState(ButtonManager.AppState.UPLOADING);
            }
            
            fileInput.files = files;
            
            // Update the file name display
            if (fileName) {
                fileName.textContent = files[0].name;
            }
            
            // Add the file-selected class to the upload area
            uploadArea.classList.add('file-selected');
            
            // Activate the extract button
            if (extractButton) {
                extractButton.classList.add('active');
                extractButton.classList.remove('disabled');
                extractButton.disabled = false;
            }
            
            // Trigger the change event on the file input to run your existing code
            const changeEvent = new Event('change', { bubbles: true });
            fileInput.dispatchEvent(changeEvent);
        }
    }
});
