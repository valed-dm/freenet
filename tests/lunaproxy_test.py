import requests

proxy_host = "eu.lunaproxy.com"
proxy_port = "12233"
proxy_user = "user-taranata_O4qcP-region-ch"
proxy_pass = "Karabata1"

proxies = {
    "http": f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}",
    "https": f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}",
}

try:
    response = requests.get("https://power.freenet.de", proxies=proxies, timeout=10, verify=False)
    with open("luna_response.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("HTML saved to luna_response.html")
    print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Proxy failed: {e}")
