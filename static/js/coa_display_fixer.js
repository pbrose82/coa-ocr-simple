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

    // Enhanced function to format test results for display
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

        // Build HTML table for display
        let html = '<table class="table table-sm table-bordered mb-0" style="width:100%; table-layout:auto;">';
        html += '<thead><tr><th>Test</th><th>Specification</th><th>Result</th></tr></thead><tbody>';

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

            html += `<tr>
                <td class="fw-medium" style="white-space: nowrap; max-width: 250px;">${testName}</td>
                <td style="white-space: nowrap; max-width: 250px;">${specification}</td>
                <td style="white-space: nowrap; max-width: 250px;">${result}</td>
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

        let html = '<table class="table table-sm table-bordered mb-0">';
        html += '<thead><tr><th>Parameter</th><th>Value</th></tr></thead><tbody>';

        for (const [parameter, value] of Object.entries(analyticalData)) {
            html += `<tr>
                <td class="fw-medium">${parameter}</td>
                <td>${value}</td>
            </tr>`;
        }

        html += '</tbody></table>';
        return html;
    }

    const originalUpdateGridWithData = window.updateGridWithData;

    if (typeof originalUpdateGridWithData === 'function') {
        window.updateGridWithData = function(data) {
            let processedData = {};
            Object.assign(processedData, data);

            if (data.document_type === 'coa') {
                if (data.test_results) {
                    const formattedTestResults = formatTestResults(data.test_results);
                    processedData.formatted_test_results = formattedTestResults;
                    delete processedData.test_results;
                }

                if (data.analytical_data) {
                    const formattedAnalyticalData = formatAnalyticalData(data.analytical_data);
                    processedData.formatted_analytical_data = formattedAnalyticalData;
                    delete processedData.analytical_data;
                }
            }

            return originalUpdateGridWithData(processedData);
        };

        console.log("COA Display Fixer: Successfully overrode updateGridWithData function");
    } else {
        console.error("COA Display Fixer: Could not find updateGridWithData function");
    }

    class HtmlCellRenderer {
        init(params) {
            this.eGui = document.createElement('div');
            if (params.value === null || params.value === undefined) {
                this.eGui.innerHTML = '';
                return;
            }

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

    if (typeof agGrid !== 'undefined') {
        agGrid.Grid.prototype.componentProvider.setCellRendererInstance('htmlCellRenderer', HtmlCellRenderer);
        console.log("COA Display Fixer: Registered HTML cell renderer");

        const originalInitializeGrid = window.initializeGrid;

        if (typeof originalInitializeGrid === 'function') {
            window.initializeGrid = function() {
                const gridOptions = originalInitializeGrid();

                if (gridOptions.columnDefs && gridOptions.columnDefs.length > 1) {
                    const valueColumn = gridOptions.columnDefs[1];
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

    if (typeof extractedDataGrid !== 'undefined' && 
        extractedDataGrid.gridOptions && 
        extractedDataGrid.gridOptions.columnDefs) {

        const valueColumn = extractedDataGrid.gridOptions.columnDefs[1];
        if (valueColumn) {
            valueColumn.cellRenderer = 'htmlCellRenderer';
            extractedDataGrid.gridOptions.api.refreshCells();
            console.log("COA Display Fixer: Applied fix to existing grid");
        }
    }
});
