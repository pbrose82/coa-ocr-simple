/**
 * Enhanced COA Test Results Display Fix
 * 
 * This script provides a complete solution for displaying Certificate of Analysis (COA)
 * test results correctly in the data grid, making full use of available screen space.
 */

// Replace the entire formatTestResults function in coa_display_fixer.js with this implementation
function formatTestResults(testResults) {
    // Check if it's a string (JSON) and try to parse it
    if (typeof testResults === 'string') {
        try {
            testResults = JSON.parse(testResults);
        } catch (e) {
            console.error('Failed to parse test results:', e);
            return testResults || "No test results available";
        }
    }

    if (!testResults || typeof testResults !== 'object') {
        return "No test results available";
    }

    // Build HTML table with better styling for full-width display
    let html = `
    <div style="width:100%; overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; margin:0; border:1px solid #dee2e6;">
            <thead>
                <tr style="background-color:#f8f9fa;">
                    <th style="width:33%; padding:8px; text-align:left; border:1px solid #dee2e6; font-weight:600;">Test</th>
                    <th style="width:33%; padding:8px; text-align:left; border:1px solid #dee2e6; font-weight:600;">Specification</th>
                    <th style="width:33%; padding:8px; text-align:left; border:1px solid #dee2e6; font-weight:600;">Result</th>
                </tr>
            </thead>
            <tbody>
    `;

    // Add each test result as a row
    for (const [testName, testData] of Object.entries(testResults)) {
        let specification = '';
        let result = '';

        // Handle different possible formats
        if (typeof testData === 'object') {
            specification = testData.specification || testData.specificaton || '';  
            result = testData.result || '';
        } else {
            result = testData;
        }

        html += `
            <tr>
                <td style="padding:8px; text-align:left; border:1px solid #dee2e6; font-weight:500;">${testName}</td>
                <td style="padding:8px; text-align:left; border:1px solid #dee2e6;">${specification}</td>
                <td style="padding:8px; text-align:left; border:1px solid #dee2e6;">${result}</td>
            </tr>
        `;
    }

    html += `
            </tbody>
        </table>
    </div>
    `;
    return html;
}

// This is a complete replacement for the HtmlCellRenderer class in index.html
class HtmlCellRenderer {
    init(params) {
        this.eGui = document.createElement('div');
        this.eGui.style.width = '100%';
        this.eGui.style.height = '100%';
        this.eGui.style.overflow = 'auto';
        this.eGui.style.padding = '2px';
        
        if (params.value === null || params.value === undefined) {
            this.eGui.innerHTML = '';
            return;
        }

        if (typeof params.value === 'string' && params.value.trim().startsWith('<')) {
            // This is HTML content (like test results)
            this.eGui.innerHTML = params.value;
            
            // Apply styles to tables to ensure they use full width
            const tables = this.eGui.querySelectorAll('table');
            tables.forEach(table => {
                table.style.width = '100%';
                table.style.tableLayout = 'fixed';
            });
        } else {
            // Plain text content
            this.eGui.textContent = params.value;
        }
    }

    getGui() {
        return this.eGui;
    }
}

// Function to modify the grid options after initialization
function enhanceGridForCOA(gridOptions) {
    if (!gridOptions) return;

    // Adjust column definitions
    if (gridOptions.columnDefs && gridOptions.columnDefs.length >= 2) {
        // Field column (narrower)
        gridOptions.columnDefs[0].minWidth = 150;
        gridOptions.columnDefs[0].maxWidth = 220;
        
        // Value column (wider to accommodate test results)
        gridOptions.columnDefs[1].flex = 3;
        gridOptions.columnDefs[1].minWidth = 500;
        gridOptions.columnDefs[1].cellRenderer = 'htmlCellRenderer';
        gridOptions.columnDefs[1].autoHeight = true;
    }

    // Enhanced row height calculation
    gridOptions.getRowHeight = function(params) {
        if (params.data && params.data.field && 
            (params.data.field === 'Formatted Test Results' || 
             params.data.field.includes('Test Results'))) {
            return 300; // Taller rows for test results
        }
        return 48; // Default row height
    };

    // Register the HTML cell renderer
    gridOptions.components = {
        ...gridOptions.components,
        htmlCellRenderer: HtmlCellRenderer
    };

    return gridOptions;
}

// Apply enhancements after grid is initialized
document.addEventListener('DOMContentLoaded', function() {
    // Wait a short time to ensure the grid is fully initialized
    setTimeout(function() {
        if (typeof extractedDataGrid !== 'undefined' && 
            extractedDataGrid.gridOptions) {
            enhanceGridForCOA(extractedDataGrid.gridOptions);
            
            // Force the grid to redraw if it contains data
            if (extractedDataGrid.gridOptions.api) {
                extractedDataGrid.gridOptions.api.refreshCells({force: true});
                extractedDataGrid.gridOptions.api.sizeColumnsToFit();
                console.log('Enhanced grid options for COA display');
            }
        }
    }, 500);
});

// Modify updateGridWithData to handle COA data specifically
const originalUpdateGridWithData = window.updateGridWithData;
if (typeof originalUpdateGridWithData === 'function') {
    window.updateGridWithData = function(data) {
        let processedData = {...data};

        if (data.document_type === 'coa') {
            // Format test results correctly
            if (data.test_results) {
                const formattedTestResults = formatTestResults(data.test_results);
                processedData.formatted_test_results = formattedTestResults;
                delete processedData.test_results;
            }

            // Make sure the grid is properly configured for COA display
            setTimeout(function() {
                if (extractedDataGrid && extractedDataGrid.gridOptions && extractedDataGrid.gridOptions.api) {
                    extractedDataGrid.gridOptions.api.sizeColumnsToFit();
                    
                    // Adjust row heights for formatted test results
                    const rowNodes = [];
                    extractedDataGrid.gridOptions.api.forEachNode(node => rowNodes.push(node));
                    
                    rowNodes.forEach(node => {
                        if (node.data && node.data.field && 
                            (node.data.field === 'Formatted Test Results' || 
                             node.data.field.includes('Test Results'))) {
                            extractedDataGrid.gridOptions.api.refreshCells({
                                force: true,
                                rowNodes: [node],
                                columns: ['value']
                            });
                        }
                    });
                }
            }, 100);
        }

        return originalUpdateGridWithData(processedData);
    };
}
