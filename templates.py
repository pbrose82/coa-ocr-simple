"""
HTML templates for the OCR application.
These functions return HTML strings for the different pages.
"""
import config

def get_base_css():
    """Return the base CSS styling used across pages"""
    return f"""
        body {{
            font-family: {config.FONT_FAMILY};
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }}
        .logo {{
            height: 50px;
            margin-right: 15px;
        }}
        h1 {{
            margin: 0;
        }}
        pre {{
            background-color: {config.SECONDARY_COLOR};
            padding: 15px;
            border-radius: 5px;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 400px;
            overflow-y: auto;
        }}
        .button {{
            display: inline-block;
            margin-top: 20px;
            padding: 8px 16px;
            background-color: {config.PRIMARY_COLOR};
            color: white;
            text-decoration: none;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        form {{
            margin-top: 20px;
        }}
        input[type="file"] {{
            margin-bottom: 10px;
            display: block;
        }}
        .file-info {{
            margin-top: 10px;
            font-size: 0.9em;
            color: #666;
        }}
        .save-button {{
            margin-left: 10px;
            background-color: #2196F3;
        }}
    """

def get_header_html(title, logo_path):
    """Return the HTML for the page header with logo"""
    return f"""
    <div class="header">
        <img src="{logo_path}" alt="{config.COMPANY_NAME} Logo" class="logo">
        <h1>{title}</h1>
    </div>
    """

def get_index_html(app_title, company_name, logo_path, allowed_extensions):
    """Return the HTML for the index/upload page"""
    allowed_ext_str = ', '.join(allowed_extensions)
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{app_title} - {company_name}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            {get_base_css()}
        </style>
    </head>
    <body>
        {get_header_html(app_title, logo_path)}
        
        <p>Upload an image or PDF file to extract text:</p>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".png,.jpg,.jpeg,.gif,.tif,.tiff,.bmp,.pdf">
            <div class="file-info">Supported file types: {allowed_ext_str}</div>
            <input type="submit" value="Extract Text" class="button">
        </form>
    </body>
    </html>
    """

def get_result_html(text, app_title, company_name, logo_path, filename):
    """Return the HTML for the results page"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OCR Result - {company_name}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            {get_base_css()}
        </style>
        <script>
            function saveTextToFile() {{
                const text = document.getElementById('extracted-text').innerText;
                const blob = new Blob([text], {{ type: 'text/plain' }});
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = 'extracted_text.txt';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }}
        </script>
    </head>
    <body>
        {get_header_html(f"{app_title} Result", logo_path)}
        
        <h2>File Processed: {filename}</h2>
        <h3>Extracted Text:</h3>
        <pre id="extracted-text">{text}</pre>
        <div>
            <a href="/" class="button">Back to Upload</a>
            <button onclick="saveTextToFile()" class="button save-button">Save Text to File</button>
        </div>
    </body>
    </html>
    """
