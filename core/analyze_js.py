"""
# curl https://components.freenet.de/login/frnLogin.umd.min.js -o frnLogin.js

# --- How to use the script ---
# 1. Save the code above as a Python file (e.g., analyze_script.py).
# 2. Place the JavaScript file you want to analyze in the same directory.
# 3. Call the main function with the path to your JS file.

# Example usage:
# analyze_js_file('your_javascript_file.js')
"""

import re
import csv

def analyze_js_file(filepath):
    """
    Parses a JavaScript file to extract API endpoints, credentials, and other
    sensitive information.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return

    # Define regex patterns for different types of data
    patterns = {
        'api_endpoints': r'url\s*:\s*[\'"](/[\w/-]+)[\'"]',
        'hostnames': r'host\s*:\s*[\'"](https?://[\w\.:-]+)[\'"]',
        'usernames': r'clientUsername\s*:\s*[\'"]([\w_]+)[\'"]',
        'passwords': r'clientPassword\s*:\s*[\'"](.+?)[\'"]'
    }

    extracted_data = {}
    for key, pattern in patterns.items():
        extracted_data[key] = re.findall(pattern, content)

    # Prepare data for CSV output
    output_data = []
    max_len = max(len(v) for v in extracted_data.values()) if extracted_data else 0

    for i in range(max_len):
        row = {}
        for key, values in extracted_data.items():
            if i < len(values):
                row[key] = values[i]
            else:
                row[key] = ''
        output_data.append(row)

    # Write the extracted data to a CSV file
    if output_data:
        with open('extracted_data_md.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=patterns.keys())
            writer.writeheader()
            writer.writerows(output_data)
        print("Successfully extracted data to 'extracted_data.csv'")
    else:
        print("No data was extracted based on the defined patterns.")

if __name__ == "__main__":
    analyze_js_file("md.min.js")
