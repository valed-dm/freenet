import httpx
import random
from bs4 import BeautifulSoup

LOGIN_URL = "https://power.freenet.de/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

def get_random_proxy():
    with open("/Users/dmvaled/WD/fnet/data/proxy.txt") as f:
        proxy_line = random.choice([line.strip() for line in f if line.strip()])
        parts = proxy_line.split(":")
        if len(parts) == 4:
            ip, port, user, pwd = parts
            return f"http://{user}:{pwd}@{ip}:{port}"
        elif len(parts) == 2:
            ip, port = parts
            return f"http://{ip}:{port}"
        raise ValueError("Bad proxy format.")

def main():
    try:
        proxy = get_random_proxy()
        print(f"[+] Using proxy: {proxy}")

        transport = httpx.HTTPTransport(
            proxy=httpx.Proxy(proxy)
        )

        with httpx.Client(transport=transport, timeout=10) as client:
            resp = client.get(LOGIN_URL, headers=HEADERS)
            soup = BeautifulSoup(resp.text, "html.parser")

            with open("http_response.html", "w", encoding="utf-8") as f:
                f.write(soup.prettify())
            print("HTML saved to http_response.html")

            csrf = soup.find("input", {"name": "_csrf"})
            print(f"[+] CSRF: {csrf.get('value') if csrf else 'Not found'}")


    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    main()
