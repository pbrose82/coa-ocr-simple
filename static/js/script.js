body { 
    padding: 0;
    margin: 0;
    font-family: Arial, sans-serif;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
}

.header {
    padding: 20px;
    text-align: center;
    border-bottom: 1px solid #e0e0e0;
}

.header h1 {
    color: #333;
    font-size: 2rem;
    margin: 0;
}

.tips-section {
    background-color: #ddf1ff;
    padding: 20px;
    display: flex;
    align-items: center;
}

.tips-icon {
    color: #8bc4ea;
    font-size: 2.5rem;
    margin-right: 20px;
}

.tips-content strong {
    color: #333;
    display: block;
    margin-bottom: 10px;
}

.tips-content ul {
    margin: 0;
    padding-left: 20px;
}

.tips-content li {
    margin-bottom: 5px;
    color: #555;
}

.main-content {
    padding: 30px;
    flex: 1;
}

.upload-section {
    margin-bottom: 30px;
}

.upload-section h2 {
    color: #555;
    font-size: 1.5rem;
    margin-bottom: 20px;
}

.form-group {
    margin-bottom: 15px;
}

.form-label {
    display: block;
    margin-bottom: 5px;
    color: #555;
}

.form-select {
    width: 100%;
    max-width: 300px;
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
}

.file-upload {
    border: 2px dashed #ddd;
    border-radius: 5px;
    padding: 30px;
    text-align: center;
    background-color: #f9f9f9;
    margin-bottom: 20px;
    position: relative;
}

.file-upload-icon {
    font-size: 3rem;
    color: #ddd;
    margin-bottom: 10px;
}

.file-info {
    display: flex;
    align-items: center;
    color: #777;
    margin: 15px 0;
}

.file-info svg {
    margin-right: 10px;
    color: #8bc4ea;
}

.btn-extract {
    background-color: #e9ecef;
    color: #555;
    border: none;
    padding: 8px 20px;
    border-radius: 4px;
    cursor: pointer;
}

.footer {
    margin-top: auto;
    padding: 30px 0;
    text-align: center;
    border-top: 1px solid #e0e0e0;
}

.footer-logo {
    max-width: 150px;
    margin-bottom: 10px;
    opacity: 0.3;
}

.copyright {
    color: #aaa;
    font-size: 12px;
}

/* For custom file input */
.custom-file-upload {
    border: 1px solid #ccc;
    display: inline-block;
    padding: 6px 12px;
    cursor: pointer;
    background-color: #f8f8f8;
    color: #2196F3;
    border-radius: 4px;
}

input[type="file"] {
    display: none;
}

.result-box {
    background-color: #f8f9fa;
    padding: 20px;
    border-radius: 5px;
    margin-top: 20px;
}

.alert-info {
    background-color: #ddf1ff;
    border-color: #b8e0ff;
    color: #0c5460;
}

.progress-bar {
    background-color: #8bc4ea;
}
