import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

# Configuration
BASE_URL = "https://www.freenet-mobilfunk.de"
API_ENDPOINT = "/partials/add-contract-data.html"
OUTPUT_DIR = "responses"
BEARER_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik9iRFAyVmJ3WUJZRzFEZ04tLTBSdCJ9.eyJodHRwczovL2ZyZWVuZXQtZ3JvdXAuZGUvYWNyIjoiMSIsInVzZXJfdHlwZSI6Im1kVXNlciIsInVzZXJuYW1lIjoiZG12YWxlZEBnbWFpbC5jb20iLCJvcmdJZCI6IjU5Y2Q2ODFhLWJiYTMtNDZmNS1iNjFhLTg2ZjQyNDBmNjI0ZiIsImlzcyI6Imh0dHBzOi8vaWQuZnJlZW5ldC1tb2JpbGZ1bmsuZGUvIiwic3ViIjoiYXV0aDB8dXNlcnw5NjYzODk2Ni0yMDE1LTQ0YmUtYmIzOS1iZjE5NmZhMGZiOTgiLCJhdWQiOlsiaHR0cHM6Ly9hcGkubWQuZGUiLCJodHRwczovL21vYmlsY29tLWRlYml0ZWwtcHJvZC5ldS5hdXRoMC5jb20vdXNlcmluZm8iXSwiaWF0IjoxNzU0MjAxNTczLCJleHAiOjE3NTQyMDMzNzMsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwiLCJhenAiOiJjS05OejdPd1E5V0dmV1VWN2oyWWhJeFpEd0NrN09WUSJ9.U--HIv_btpbgvixiCEM6bOlPFMD6s_-HJORJ-XuRzV3WWFzIIGOrQsgEVYwGwYz8wNkeuAzSO_yUjSs_9pvMTNgqeBIobXLq5_LXTDTVQOGAmXgS5lWI1sQZjsVPcQwezw1aZiGoH2i1K6JPWOts-fcKUqKkW8n-gLbvgnQ2ag-mIRmbzofVxqq7s7HYZE45XgBY8rSnyVrMXgdSgXqxQbc7ffxxHya07M5rDUZrfoSZpTNroJdrPJVeRChJqcmapsDYyvdyv9z6ZqQWh5OhIQIbi1YnPuvKTEGYXrw2tK6AbaEe6ggazm2cVGeQEEMHxfwhrxAaUDw1WN0rDBPd8g"

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.freenet-mobilfunk.de/online-service/",
    "Origin": "https://www.freenet-mobilfunk.de",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
}

cookies = {
    "MDSESSID": "ik5huril47iikfk5thg3ts9dse",
    "vid": "6e7a060174a27635346635dec2c76c0cee291642c45874d31a19ef8110757900",
    "__cf_bm": "1CMcMdBgQRYlgZ9NYll34rQfdF7reeedJKb2AxaNUUo-1754201571-1.0.1.1-HxvmuXthMcEMKb16UEtmN.8wLCuvkUgyaRGUQpINDiZMk5fM4QqgdNNvIXPC8d_waQ62tun.UTIQxmDD7AYwFeqhYioU6.6Iyci1vPgBSM8",
    "_cfuvid": "w5usFG1zOtpT6fKJLjQl9Q.6Mhplp8b0hkbdc84zdJ8-1754200025207-0.0.1.1-604800000",
    "cf_clearance": "sC7BBz9UDmqXaK3GCoS7obDC51JG08OgjSvHUcEa1UY-1754201573-1.2.1.1-1XsuETdXDr4gHhn19JVZC31tQBIv8jAR3fEZQTFJX55tVfSrMe80qUH2mc0rqM0l"
}

def prettify_html(html_content):
    """Format HTML content using BeautifulSoup"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.prettify()
    except Exception as e:
        print(f"Error prettifying HTML: {str(e)}")
        return html_content  # Return original if prettify fails

def save_response_to_file(content, filename):
    """Save prettified response content to file"""
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    except Exception as e:
        print(f"File save error: {str(e)}")
        return None

def make_authenticated_request():
    """Make request and save prettified response"""
    try:
        response = requests.get(
            f"{BASE_URL}{API_ENDPOINT}",
            headers=headers,
            cookies=cookies,
            timeout=15
        )
        response.raise_for_status()

        print("\n=== Request Successful ===")
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")

        # Prettify the HTML
        pretty_html = prettify_html(response.text)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prettified_response_{timestamp}.html"

        # Save prettified content
        saved_path = save_response_to_file(pretty_html, filename)

        if saved_path:
            print(f"\nSaved prettified HTML to:\n{saved_path}")
            print(f"\nOriginal size: {len(response.text)} chars")
            print(f"Prettified size: {len(pretty_html)} chars")

            # Verify prettification worked
            line_count = pretty_html.count('\n')
            print(f"Formatted into {line_count} lines")

            # Show sample of prettified content
            print("\n=== Sample of Prettified Content ===")
            print(pretty_html[:500] + "\n...")  # First 500 chars

        return response

    except requests.exceptions.RequestException as e:
        print(f"\n!!! Request Failed !!!")
        print(f"Error: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Status: {e.response.status_code}")
            error_content = e.response.text
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_response_to_file(error_content, f"error_{timestamp}.html")
        return None

if __name__ == "__main__":
    make_authenticated_request()

