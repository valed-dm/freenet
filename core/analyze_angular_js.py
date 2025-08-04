import re
import csv

def analyze_angular_js_file(filepath):
    """
    Parses a minified AngularJS file to extract the API endpoint map
    from a service definition. This script is tailored to find key-value
    pairs inside a specific kind of JavaScript object structure.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return

    # This more specific regex is designed to find the API endpoint map.
    # It looks for patterns like: someName:"/api/ps/auth/login"
    # It captures the 'name' (e.g., "login") and the 'URL'
    api_map_pattern = r'([a-zA-Z0-9]+):"((?:/|http)[^"]+)"'

    matches = re.findall(api_map_pattern, content)

    # The original patterns might still be useful if the file contains
    # other formats, so we can run them as well.
    legacy_patterns = {
        'hostnames': r'host\s*:\s*[\'"](https?://[\w\.:-]+)[\'"]',
        'usernames': r'clientUsername\s*:\s*[\'"]([\w_]+)[\'"]',
        'passwords': r'clientPassword\s*:\s*[\'"](.+?)[\'"]'
    }

    extracted_data = {}
    for key, pattern in legacy_patterns.items():
        extracted_data[key] = re.findall(pattern, content)

    # Prepare data for CSV output
    if matches:
        print(f"Found {len(matches)} API endpoints in the UrlService map.")
        output_data = []
        for match in matches:
            # Create a dictionary for each key-value pair found
            row = {
                'endpoint_name': match[0],
                'url_pattern': match[1]
            }
            output_data.append(row)

        # Write the main API map to its own CSV file
        with open('extracted_api_map.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['endpoint_name', 'url_pattern'])
            writer.writeheader()
            writer.writerows(output_data)
        print("Successfully extracted API map to 'extracted_api_map.csv'")
    else:
        print("No API endpoints were found using the new pattern.")

    # You can still process and save any data found by the old patterns if needed
    if any(extracted_data.values()):
        print("Found additional data with legacy patterns.")
        # (Add CSV writing logic for legacy data if necessary)

if __name__ == "__main__":
    # Make sure to place the md.min.js file in the same directory
    # or provide the correct path.
    analyze_angular_js_file("md.min.js")
