/**
 * COA Display Fixer
 * 
 * This script fixes the way COA (Certificate of Analysis) data is 
 * displayed in the UI. It ensures that test results and analytical data
 * are properly formatted and displayed in the data grid.
 * 
 * Include this script in your index.html after the main script.js file.
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("COA Display Fixer loaded");
    
    // Function to format test results for display
    function formatTestResults(testResults) {
        if (!testResults || typeof testResults !== 'object') {
            return "No test results available";
        }
        
        // Build HTML for displaying test results in a table
        let html = '<table class="table table-sm table-bordered mb-0">';
        html += '<thead><tr><th>Test</th><th>Specification</th><th>Result</th></tr></thead><tbody>';
        
        // Add rows for each test
        for (const [testName, testData] of Object.entries(testResults)) {
            const specification = testData.specification || '';
            const result = testData.result || '';
            
            html += `<tr>
                <td class="fw-medium">${testName}</td>
                <td>${specification}</td>
                <td>${result}</td>
            </tr>`;
        }
        
        html += '</tbody></table>';
        return html;
    }
    
    // Function to format analytical data for display
    function formatAnalyticalData(analyticalData) {
        if (!analyticalData || typeof analyticalData !== 'object') {
            return "No analytical data available";
        }
        
        // Build HTML for displaying analytical data in a table
        let html = '<table class="table table-sm table-bordered mb-0">';
        html += '<thead><tr><th>Parameter</th><th>Value</th></tr></thead><tbody>';
        
        // Add rows for each parameter
        for (const [parameter, value] of Object.entries(analyticalData)) {
            html += `<tr>
                <td class="fw-medium">${parameter}</td>
                <td>${value}</td>
            </tr>`;
        }
        
        html += '</tbody></table>';
        return html;
    }
    
    // Override the AG Grid update function to handle COA-specific data formatting
    const originalUpdateGridWithData = window.updateGridWithData;
    
    if (typeof originalUpdateGridWithData === 'function') {
        window.updateGridWithData = function(data) {
            // Process COA-specific data
            let processedData = {};
            
            // Copy all data
            Object.assign(processedData, data);
            
            // Special handling for COA document
            if (data.document_type === 'coa') {
                // Format test results if present
                if (data.test_results && typeof data.test_results === 'object') {
                    // Create a specially formatted HTML version
                    const formattedTestResults = formatTestResults(data.test_results);
                    
                    // Create a new field with the formatted HTML
                    processedData.formatted_test_results = formattedTestResults;
                    
                    // Remove the original test_results to avoid confusion
                    delete processedData.test_results;
                }
                
                // Format analytical data if present
                if (data.analytical_data && typeof data.analytical_data === 'object') {
                    // Create a specially formatted HTML version
                    const formattedAnalyticalData = formatAnalyticalData(data.analytical_data);
                    
                    // Create a new field with the formatted HTML
                    processedData.formatted_analytical_data = formattedAnalyticalData;
                    
                    // Remove the original analytical_data to avoid confusion
                    delete processedData.analytical_data;
                }
            }
            
            // Call the original function with the processed data
            return originalUpdateGridWithData(processedData);
        };
        
        console.log("COA Display Fixer: Successfully overrode updateGridWithData function");
    } else {
        console.error("COA Display Fixer: Could not find updateGridWithData function");
    }
    
    // Create a custom cell renderer for HTML content
    class HtmlCellRenderer {
        init(params) {
            this.eGui = document.createElement('div');
            if (params.value === null || params.value === undefined) {
                this.eGui.innerHTML = '';
                return;
            }
            
            // If the value starts with <table, it's HTML content
            if (typeof params.value === 'string' && params.value.trim().startsWith('<table')) {
                this.eGui.innerHTML = params.value;
            } else {
                this.eGui.textContent = params.value;
            }
        }
        
        getGui() {
            return this.eGui;
        }
    }
    
    // Register the custom cell renderer with AG Grid
    if (typeof agGrid !== 'undefined') {
        agGrid.Grid.prototype.componentProvider.setCellRendererInstance('htmlCellRenderer', HtmlCellRenderer);
        console.log("COA Display Fixer: Registered HTML cell renderer");
        
        // Override the grid initialization to use the HTML cell renderer
        const originalInitializeGrid = window.initializeGrid;
        
        if (typeof originalInitializeGrid === 'function') {
            window.initializeGrid = function() {
                const gridOptions = originalInitializeGrid();
                
                // Ensure the value column uses the HTML cell renderer
                if (gridOptions.columnDefs && gridOptions.columnDefs.length > 1) {
                    const valueColumn = gridOptions.columnDefs[1]; // Usually the second column is 'Value'
                    if (valueColumn) {
                        valueColumn.cellRenderer = 'htmlCellRenderer';
                    }
                }
                
                return gridOptions;
            };
            
            console.log("COA Display Fixer: Successfully overrode grid initialization");
        }
    } else {
        console.error("COA Display Fixer: AG Grid not available");
    }
    
    // If the grid is already initialized, attempt to fix it
    if (typeof extractedDataGrid !== 'undefined' && 
        extractedDataGrid.gridOptions && 
        extractedDataGrid.gridOptions.columnDefs) {
        
        // Apply the HTML cell renderer to the value column
        const valueColumn = extractedDataGrid.gridOptions.columnDefs[1];
        if (valueColumn) {
            valueColumn.cellRenderer = 'htmlCellRenderer';
            extractedDataGrid.gridOptions.api.refreshCells();
            console.log("COA Display Fixer: Applied fix to existing grid");
        }
    }
});
