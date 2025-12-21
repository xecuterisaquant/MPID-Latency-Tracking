#!/usr/bin/env python3
"""Convert markdown report to HTML with academic styling."""

import markdown

# Read the markdown file
with open('report.md', 'r', encoding='utf-8') as f:
    md_content = f.read()

# Convert to HTML with extensions
html_content = markdown.markdown(
    md_content,
    extensions=['extra', 'codehilite', 'toc', 'tables', 'fenced_code']
)

# Add CSS styling for professional academic look
html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MPID Latency Analysis Report</title>
    <style>
        body {{
            font-family: 'Times New Roman', Times, serif;
            line-height: 1.6;
            max-width: 8.5in;
            margin: 0 auto;
            padding: 1in;
            background: white;
            color: #333;
        }}
        h1 {{
            font-size: 20pt;
            text-align: center;
            margin-bottom: 0.5em;
            border-bottom: 2px solid #333;
            padding-bottom: 0.5em;
        }}
        h2 {{
            font-size: 16pt;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            color: #000;
        }}
        h3 {{
            font-size: 14pt;
            margin-top: 1em;
            margin-bottom: 0.3em;
        }}
        h4 {{
            font-size: 12pt;
            margin-top: 0.8em;
            margin-bottom: 0.3em;
            font-style: italic;
        }}
        p {{
            text-align: justify;
            margin-bottom: 0.8em;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        pre {{
            background: #f4f4f4;
            padding: 1em;
            border-left: 4px solid #ccc;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
        }}
        pre code {{
            background: none;
            padding: 0;
        }}
        blockquote {{
            border-left: 4px solid #ddd;
            padding-left: 1em;
            margin-left: 0;
            color: #666;
            font-style: italic;
        }}
        .author-info {{
            text-align: center;
            font-size: 11pt;
            margin-bottom: 2em;
        }}
        strong {{
            font-weight: bold;
        }}
        em {{
            font-style: italic;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ccc;
            margin: 2em 0;
        }}
        img {{
            max-width: 100%;
            display: block;
            margin: 1em auto;
        }}
        @media print {{
            body {{
                padding: 0;
            }}
            h1, h2, h3 {{
                page-break-after: avoid;
            }}
            table, figure {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
{content}
</body>
</html>
"""

# Write the HTML file
output_html = html_template.format(content=html_content)
with open('report.html', 'w', encoding='utf-8') as f:
    f.write(output_html)

print("✓ Successfully converted report.md to report.html")
print("✓ Open report.html in your browser to view")
print("✓ You can print to PDF from your browser (Ctrl+P → Save as PDF)")
