import random
import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from curl_cffi.requests import Session
from loguru import logger

# Constants
LOGIN_PAGE_URL = "https://power.freenet.de/"
OAUTH_HANDSHAKE_URL = "https://oauth.freenet.de/"
LOGIN_URL = "https://oauth.freenet.de/oauth/token"
CUSTOMER_URL = "https://api.mail.freenet.de/v2.0/customer"
MAIL_ACCOUNTS_URL = "https://api.mail.freenet.de/v2.0/mail/accounts"
SETTINGS_URL = "https://api.mail.freenet.de/v2.0/customer/settings"
CLIENT_ID = "customer_api"
CLIENT_SECRET = "rotOHeGC39FWOasymMLC4g=="
MAX_ALIASES_PER_ACCOUNT = 10
MAX_WORKERS = 1
BROWSER_PROFILES = ["chrome110", "chrome107", "chrome104", "chrome99"]

logger = logger.patch(lambda record: record.update(name="AliasWorker"))
logger.add("logs/output.log", rotation="500 KB", backtrace=True, diagnose=True, level="DEBUG")

class FreenetAliasAdder:
    def __init__(self):
        self.available_aliases = queue.Queue()
        self.output_lock = threading.Lock()
        self.accounts = []
        self.proxy_config = {}

    def load_files(self):
        try:
            with open("data/input.txt", "r") as f:
                self.accounts = [line.strip().split(":", 1) for line in f if ":" in line]

            with open("data/aliases.txt", "r") as f:
                for alias in f:
                    self.available_aliases.put(alias.strip())

            with open("data/proxy.txt", "r") as f:
                parts = f.readline().strip().split(":")
                self.proxy_config = {
                    'http': f"socks5h://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}",
                    'https': f"socks5h://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                }

        except FileNotFoundError as e:
            logger.error(f"File loading error: {e}")

    def run(self):
        self.load_files()
        if not self.accounts or not self.proxy_config:
            logger.error("Required input files or proxy configuration missing.")
            return

        logger.info(f"Loaded {len(self.accounts)} accounts. Processing with {MAX_WORKERS} workers.")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(self.process_account, self.accounts)

        logger.info("All accounts processed.")

    def process_account(self, account):
        email, password = account
        session = Session(impersonate=random.choice(BROWSER_PROFILES))
        session.proxies = self.proxy_config

        try:
            logger.info(f"[{email}] Starting session warm-up.")
            session.get(LOGIN_PAGE_URL, headers={"Referer": "https://www.google.com/"})
            session.get(OAUTH_HANDSHAKE_URL, headers={
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://power.freenet.de",
                "Referer": "https://power.freenet.de/"
            })

            logger.success(f"[{email}] Session warmed up.")

            login_payload = {
                "grant_type": "password", "username": email, "password": password,
                "world": "2", "webLogin": "true", "domainLogin": "false"
            }

            resp = session.post(
                LOGIN_URL,
                data=login_payload,
                auth=(CLIENT_ID, CLIENT_SECRET),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "https://power.freenet.de",
                    "Referer": "https://power.freenet.de/"
                }
            )

            resp.raise_for_status()
            access_token = resp.json()["access_token"]
            logger.success(f"[{email}] Login successful.")

            delay = random.uniform(60, 90)
            logger.info(f"[{email}] Sleeping for {delay:.2f} seconds to simulate human behavior...")
            time.sleep(delay)

            headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Client': 'fn-cloud-web-web',
                'Origin': 'https://webmail.freenet.de',
                'Referer': 'https://webmail.freenet.de/'
            }

            accounts_data = session.get(MAIL_ACCOUNTS_URL, headers=headers).json()
            primary_account = accounts_data.get('data', [])[0]
            correct_account_id = primary_account.get('account_id')
            existing_aliases = {a['email'] for a in primary_account.get('aliases', [])}

            if not correct_account_id:
                raise ValueError("No account_id found.")

            logger.info(f"[{email}] Account ID: {correct_account_id}, Existing: {len(existing_aliases)}")

            to_add_count = MAX_ALIASES_PER_ACCOUNT - len(existing_aliases)
            added = []

            while len(added) < to_add_count:
                if self.available_aliases.empty():
                    logger.warning("Alias queue is empty.")
                    break

                new_alias = self.available_aliases.get()
                full_email = f"{new_alias}@freenet.de"

                if full_email in existing_aliases:
                    logger.info(f"[{email}] Alias {full_email} already exists.")
                    continue

                payload = {
                    "account_id": correct_account_id,
                    "email": full_email,
                    "setting": "mail.accounts.internal.alias"
                }

                logger.debug(f"[{email}] Adding alias: {full_email}")

                try:
                    response = session.post(SETTINGS_URL, headers=headers, json=payload, timeout=30)
                except Exception as ex:
                    logger.error(f"[{email}] Timeout adding {full_email}: {ex}")
                    time.sleep(15)
                    continue

                if response.status_code == 200:
                    logger.success(f"[{email}] Added alias: {new_alias}")
                    added.append(new_alias)
                    time.sleep(random.uniform(3, 6))
                    continue

                try:
                    err = response.json()
                    msg = err.get("message", "")
                    code = err.get("code")

                    if "Ratelimit" in msg:
                        logger.warning(f"[{email}] Rate limited. Waiting.")
                        time.sleep(random.uniform(10, 15))
                    elif code == 4101:
                        logger.warning(f"[{email}] Alias limit reached.")
                        break
                    else:
                        logger.warning(f"[{email}] Minor error: {msg}")
                        time.sleep(random.uniform(2, 4))
                except Exception:
                    logger.error(f"[{email}] Non-JSON error: {response.text}")
                    time.sleep(random.uniform(5, 8))

            # Final result output
            result = f"{email}:{password} [Add: {len(added)}; {', '.join(added)}]"
            with self.output_lock:
                Path("output.txt").open("a").write(result + "\n")

        except Exception as e:
            error_text = getattr(e, 'response', {}).text if hasattr(e, 'response') else ""
            logger.critical(f"[{email}] CRITICAL ERROR: {e} | Response: {error_text}")
            with self.output_lock:
                Path("output.txt").open("a").write(f"{email}:{password} [Error: {e} | Response: {error_text}]\n")
        finally:
            session.close()


if __name__ == "__main__":
    FreenetAliasAdder().run()
