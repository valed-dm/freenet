from concurrent.futures import ThreadPoolExecutor
import os
import random
from urllib.parse import urlparse

import requests
from requests.exceptions import ProxyError
from requests.exceptions import RequestException
from requests.exceptions import SSLError
from requests.exceptions import Timeout


def fetch_proxy_list(limit: int = 20) -> list[str]:
    """Fetch random HTTP proxies from ProxyScrape API.

    Args:
        limit: Maximum proxies to return

    Returns:
        List of proxy URLs (e.g., ["http://1.2.3.4:80", ...])
    """
    resp = requests.get(
        "https://api.proxyscrape.com/?request=getproxies&proxytype=http&country=all&timeout=5000"
    )
    proxies = [f"http://{p}" for p in resp.text.splitlines() if p.strip()]
    return random.sample(proxies, k=min(limit, len(proxies)))


def check_proxy(proxy: str) -> bool:
    """Validate if proxy is functional by testing against httpbin.

    Args:
        proxy: Proxy URL to test

    Returns:
        True if proxy is responsive, False otherwise

    Raises:
        ValueError: If proxy URL is malformed
    """
    try:
        r = requests.get(
            "https://httpbin.org/ip",
            proxies={"http": proxy, "https": proxy},
            timeout=3,
        )
        return r.status_code == 200
    except (Timeout, ProxyError, SSLError, ConnectionError):
        return False
    except RequestException:
        return False
    except ValueError as e:
        raise ValueError(f"Invalid proxy URL {proxy}") from e


def build_valid_proxy_pool() -> list[str]:
    """Build validated proxy pool using parallel checking.

    Returns:
        List of working proxy URLs
    """
    max_workers = min(10, os.cpu_count() - 1 or 1)
    raw = fetch_proxy_list()
    valid = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for proxy, ok in zip(raw, executor.map(check_proxy, raw)):
            if ok:
                valid.append(proxy)
    return valid


def save_proxies_to_file(proxies: list[str], filename: str = "data/proxy.txt"):
    """Save proxies to file in host:port:username:password format.

    Args:
        proxies: List of proxy URLs
        filename: Output file path
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'w') as f:
        for proxy in proxies:
            parsed = urlparse(proxy)
            host = parsed.hostname
            port = parsed.port
            if host and port:
                # Format: host:port:username:password (empty credentials in this case)
                f.write(f"{host}:{port}\n")


if __name__ == "__main__":
    valid_proxies = build_valid_proxy_pool()
    print(f"Found {len(valid_proxies)} valid proxies")
    save_proxies_to_file(valid_proxies)
    print("Proxies saved to data/proxy.txt")
