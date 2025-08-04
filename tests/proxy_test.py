import requests

proxy = "eu.lunaproxy.com:12233:user-taranata_O4qcP-region-ch:Karabata1"
parts = proxy.split(':')

proxies = {
    'http': f"socks5://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}",
    'https': f"socks5://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
}

try:
    r = requests.get("https://api.ipify.org?format=json",
                    proxies=proxies,
                    timeout=10)
    print(f"✅ Proxy Working | IP: {r.json()['ip']}")
except Exception as e:
    print(f"❌ Proxy Failed | Error: {str(e)}")
