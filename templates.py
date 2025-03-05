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
    """

def get_header_html(title, logo_path):
    """Return the HTML for the page header with logo"""
    return f"""
    <div class="header">
        <img src="{logo_path}" alt="{config.COMPANY_NAME} Logo" class="logo">
        <h1>{title}</h1>
    </div>
    """

def get_index_html(app_title, company_name, logo_path):
    """Return the HTML for the index/upload page"""
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
        
        <p>Upload an image file to extract text:</p>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept="image/*">
            <input type="submit" value="Extract Text" class="button">
        </form>
    </body>
    </html>
    """

def get_result_html(text, app_title, company_name, logo_path):
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
    </head>
    <body>
        {get_header_html(f"{app_title} Result", logo_path)}
        
        <h2>Extracted Text:</h2>
        <pre>{text}</pre>
        <a href="/" class="button">Back to Upload</a>
    </body>
    </html>
    """
