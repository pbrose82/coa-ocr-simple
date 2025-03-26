/**
 * Document AI Trainer
 * This script handles the training interface for teaching the AI to recognize new document types
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const documentTypeSelect = document.getElementById('documentType');
    const customTypeInput = document.getElementById('customTypeInput');
    const customTypeName = document.getElementById('customTypeName');
    const trainingFileInput = document.getElementById('trainingFileInput');
    const processBtn = document.getElementById('processBtn');
    const trainingInterface = document.getElementById('trainingInterface');
    const documentContent = document.getElementById('documentContent');
    const selectedText = document.getElementById('selectedText');
    const fieldName = document.getElementById('fieldName');
    const fieldType = document.getElementById('fieldType');
    const addFieldBtn = document.getElementById('addFieldBtn');
    const mappedFields = document.getElementById('mappedFields');
    const saveTrainingBtn = document.getElementById('saveTrainingBtn');
    const cancelTrainingBtn = document.getElementById('cancelTrainingBtn');
    const processingStatus = document.getElementById('processingStatus');
    
    // Mapped fields data
    let mappedFieldsData = [];
    
    // Handle document type selection
    if (documentTypeSelect) {
        documentTypeSelect.addEventListener('change', function() {
            if (this.value === 'custom') {
                customTypeInput.style.display = 'block';
            } else {
                customTypeInput.style.display = 'none';
            }
        });
    }
    
    // Process button click handler
    if (processBtn) {
        processBtn.addEventListener('click', function() {
            const file = trainingFileInput.files[0];
            
            if (!file) {
                alert('Please select a file to process');
                return;
            }
            
            // Show processing status
            processingStatus.style.display = 'flex';
            
            // In a real implementation, we would upload the file and get back
            // the OCR'd text. For this demo, we'll simulate the process.
            
            // Simulate file processing delay
            setTimeout(() => {
                // Hide processing status
                processingStatus.style.display = 'none';
                
                // Show the training interface
                trainingInterface.style.display = 'block';
                
                // Add sample text based on document type
                const docType = documentTypeSelect.value;
                
                // Set sample text based on document type
                if (docType === 'sds') {
                    documentContent.textContent = getSampleSDS();
                } else if (docType === 'tds') {
                    documentContent.textContent = getSampleTDS();
                } else {
                    documentContent.textContent = getSampleGeneric();
                }
                
                // Set up text selection in document content
                setupTextSelection();
                
                // Scroll to the training interface
                trainingInterface.scrollIntoView({ behavior: 'smooth' });
            }, 1500);
        });
    }
    
    // Text selection handler
    function setupTextSelection() {
        documentContent.addEventListener('mouseup', function() {
            const selection = window.getSelection();
            const selectedTextContent = selection.toString().trim();
            
            if (selectedTextContent) {
                selectedText.textContent = selectedTextContent;
                addFieldBtn.disabled = false;
            } else {
                selectedText.textContent = 'No text selected';
                addFieldBtn.disabled = true;
            }
        });
    }
    
    // Add field button handler
    if (addFieldBtn) {
        addFieldBtn.addEventListener('click', function() {
            const fieldNameValue = fieldName.value.trim();
            const fieldTypeValue = fieldType.value;
            const selectedTextValue = selectedText.textContent;
            
            if (!fieldNameValue) {
                alert('Please enter a field name');
                return;
            }
            
            if (selectedTextValue === 'No text selected') {
                alert('Please select text from the document');
                return;
            }
            
            // Add to mapped fields data
            const newField = {
                name: fieldNameValue,
                type: fieldTypeValue,
                value: selectedTextValue
            };
            
            mappedFieldsData.push(newField);
            
            // Update UI
            updateMappedFieldsUI();
            
            // Clear inputs
            fieldName.value = '';
            selectedText.textContent = 'No text selected';
            addFieldBtn.disabled = true;
            
            // Enable save button if we have at least one field
            saveTrainingBtn.disabled = false;
        });
    }
    
    // Update the mapped fields UI
    function updateMappedFieldsUI() {
        if (mappedFieldsData.length === 0) {
            mappedFields.innerHTML = '<div class="text-muted p-3 text-center">No fields mapped yet</div>';
            return;
        }
        
        mappedFields.innerHTML = '';
        
        mappedFieldsData.forEach((field, index) => {
            const fieldElement = document.createElement('div');
            fieldElement.className = 'field-item';
            fieldElement.innerHTML = `
                <div>
                    <strong>${field.name}</strong> (${field.type})
                    <div class="text-muted text-truncate" style="max-width: 300px;" title="${field.value}">${field.value}</div>
                </div>
                <button class="btn btn-sm btn-outline-danger remove-field" data-index="${index}">Remove</button>
            `;
            mappedFields.appendChild(fieldElement);
        });
        
        // Add remove field handlers
        document.querySelectorAll('.remove-field').forEach(button => {
            button.addEventListener('click', function() {
                const index = parseInt(this.getAttribute('data-index'));
                mappedFieldsData.splice(index, 1);
                updateMappedFieldsUI();
                
                // Disable save button if no fields
                if (mappedFieldsData.length === 0) {
                    saveTrainingBtn.disabled = true;
                }
            });
        });
    }
    
    // Save training button handler
    if (saveTrainingBtn) {
        saveTrainingBtn.addEventListener('click', function() {
            if (mappedFieldsData.length === 0) {
                alert('Please map at least one field before saving');
                return;
            }
            
            // Show processing status
            processingStatus.style.display = 'flex';
            document.getElementById('statusText').textContent = 'Saving training data...';
            
            // Prepare annotations data
            const annotations = {
                field_mappings: {}
            };
            
            // Format the annotations
            mappedFieldsData.forEach(field => {
                annotations.field_mappings[field.name] = field.value;
            });
            
            // Get the selected document type
            let docType = documentTypeSelect.value;
            if (docType === 'custom' && customTypeName.value.trim()) {
                docType = customTypeName.value.trim();
            }
            
            // In a real implementation, we would send this data to the server
            // For this demo, we'll simulate the process
            
            // Simulate API call delay
            setTimeout(() => {
                // Hide processing status
                processingStatus.style.display = 'none';
                
                // Show success message
                alert('Training data saved successfully! The system will now use these patterns for future extractions.');
                
                // Reset the interface
                resetTrainingInterface();
                
            }, 1500);
        });
    }
    
    // Cancel button handler
    if (cancelTrainingBtn) {
        cancelTrainingBtn.addEventListener('click', function() {
            if (mappedFieldsData.length > 0) {
                if (!confirm('Are you sure you want to cancel? All mapping progress will be lost.')) {
                    return;
                }
            }
            
            resetTrainingInterface();
        });
    }
    
    // Reset the training interface
    function resetTrainingInterface() {
        trainingInterface.style.display = 'none';
        documentContent.textContent = '';
        selectedText.textContent = 'No text selected';
        fieldName.value = '';
        mappedFieldsData = [];
        updateMappedFieldsUI();
        saveTrainingBtn.disabled = true;
        trainingFileInput.value = '';
    }
    
    // Sample SDS text
    function getSampleSDS() {
        return `SAFETY DATA SHEET
SECTION 1: Identification
Product Name: Sample Chemical Solution
CAS Number: 123-45-6789
Manufacturer: Example Chemicals Inc.
Emergency Phone: 1-800-123-4567

SECTION 2: Hazard(s) Identification
GHS Classification: Flammable Liquid Category 2
Signal Word: Danger
Hazard Statements: H225 - Highly flammable liquid and vapor
                   H319 - Causes serious eye irritation
                   H336 - May cause drowsiness or dizziness

SECTION 3: Composition/Information on Ingredients
Chemical Name: Example Chemical
CAS Number: 123-45-6789
Concentration: 99.5%
                    
SECTION 4: First-Aid Measures
Eye Contact: Rinse cautiously with water for several minutes. Remove contact lenses, if present and easy to do.
Skin Contact: Wash with plenty of soap and water.
Inhalation: Remove person to fresh air and keep comfortable for breathing.

SECTION 5: Fire-Fighting Measures
Suitable Extinguishing Media: Water spray, alcohol-resistant foam, dry chemical, carbon dioxide.
Special Protective Equipment: Self-contained breathing apparatus and full protective clothing must be worn.`;
    }
    
    // Sample TDS text
    function getSampleTDS() {
        return `TECHNICAL DATA SHEET
        
Product Name: TechBond Adhesive X-500
Product Code: TB-X500
Manufacturer: TechBond Solutions Ltd.

PRODUCT DESCRIPTION
TechBond X-500 is a high-performance, two-component epoxy adhesive designed for bonding metals, ceramics, and most plastics. It provides excellent resistance to chemicals, heat, and impact.

TECHNICAL PROPERTIES
Base: Epoxy Resin
Color: Clear Amber
Mix Ratio: 1:1 by volume
Working Time: 20 minutes at 25°C
Fixture Time: 2 hours
Full Cure: 24 hours at 25°C
Viscosity: 12,000 cP
Hardness (Shore D): 80
Temperature Resistance: -40°C to 120°C
Tensile Strength: 35 MPa
Lap Shear Strength (ASTM D1002): 25 MPa (on steel)

APPLICATIONS
• Bonding metals including steel, aluminum, and brass
• Fixing ceramic components
• Electronic component assembly
• Automotive repair
• General industrial bonding applications

STORAGE
Store in a cool, dry place between 5°C and 25°C. Keep containers tightly closed when not in use. Shelf life is 12 months from date of manufacture when stored properly.`;
    }
    
    // Sample generic text
    function getSampleGeneric() {
        return `CERTIFICATE OF ANALYSIS

Product Name: Analytical Standard Solution
Catalog Number: AS-1234
Lot Number: L5678901
CAS Number: 78-93-3
Expiration Date: 2024-12-31

TEST RESULTS
Appearance          Clear, colorless liquid      PASS
Purity (GC)         99.8%                        PASS
Density at 20°C     0.805 g/mL                   PASS
Refractive Index    1.3785                       PASS
Water Content       0.02%                        PASS

This lot meets or exceeds all quality specifications. This product is suitable for analytical use.

Analysis Date: 2023-06-15
Analyst: J. Smith
Quality Control Approval: M. Johnson

For laboratory use only. Store at 2-8°C.`;
    }
});
