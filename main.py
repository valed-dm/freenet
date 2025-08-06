import random
import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Using curl_cffi to impersonate browser TLS fingerprints and handle its specific errors
from curl_cffi.requests import Session, errors
from loguru import logger

# --- Constants ---
# URLs for Freenet services
LOGIN_PAGE_URL = "https://power.freenet.de/"
OAUTH_HANDSHAKE_URL = "https://oauth.freenet.de/"
LOGIN_URL = "https://oauth.freenet.de/oauth/token"
MAIL_ACCOUNTS_URL = "https://api.mail.freenet.de/v2.0/mail/accounts"
SETTINGS_URL = "https://api.mail.freenet.de/v2.0/customer/settings"

# Credentials for the API client
CLIENT_ID = "customer_api"
CLIENT_SECRET = "rotOHeGC39FWOasymMLC4g=="

# --- Configuration ---
MAX_ALIASES_PER_ACCOUNT = 10
MAX_WORKERS = 5
BROWSER_PROFILES = ["chrome110", "chrome107", "chrome104", "chrome99"]

# --- File Paths ---
INPUT_FILE = Path("data/input.txt")
ALIASES_FILE = Path("data/aliases.txt")
REMAINING_ALIASES_FILE = Path("data/remaining_aliases.txt")  # New file for state management
PROXY_FILE = Path("data/proxy.txt")
OUTPUT_FILE = Path("output.txt")
LOG_FILE = Path("logs/output.log")
CRITICAL_ERRORS_FILE = Path("critical_errors.txt")

# --- Logger Setup ---
logger = logger.patch(lambda record: record.update(name="AliasWorker"))
logger.add(LOG_FILE, rotation="500 KB", backtrace=True, diagnose=True, level="DEBUG")


class FreenetAliasAdder:
    def __init__(self):
        self.available_aliases = queue.Queue()
        self.output_lock = threading.Lock()
        self.accounts = []
        self.proxy_config = {}

    def load_files(self) -> bool:
        """Loads configuration from data files. Returns True on success."""
        try:
            INPUT_FILE.parent.mkdir(exist_ok=True)
            LOG_FILE.parent.mkdir(exist_ok=True)

            logger.info(f"Loading accounts from {INPUT_FILE}...")
            with INPUT_FILE.open("r", encoding='utf-8') as f:
                self.accounts = [line.strip().split(":", 1) for line in f if ":" in line]

            logger.info(f"Loading aliases from {ALIASES_FILE}...")
            with ALIASES_FILE.open("r", encoding='utf-8') as f:
                for alias in f:
                    self.available_aliases.put(alias.strip())

            with PROXY_FILE.open("r", encoding='utf-8') as f:
                line = f.readline().strip()
                if not line:
                    self.proxy_config = {}
                else:
                    parts = line.split(":")
                    self.proxy_config = {'http': f"socks5h://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}",
                                         'https': f"socks5h://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"}

            return True
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}. Please ensure data files exist.")
            return False
        except Exception as e:
            logger.critical(f"An unexpected error occurred during file loading: {e}")
            return False

    def _write_remaining_aliases(self):
        """Drains the queue of unused aliases and writes them to a file."""
        logger.info("Writing unused aliases to the remaining aliases file...")
        count = 0
        with REMAINING_ALIASES_FILE.open("w", encoding='utf-8') as f:
            while not self.available_aliases.empty():
                try:
                    alias = self.available_aliases.get_nowait()
                    f.write(alias + "\n")
                    count += 1
                except queue.Empty:
                    break  # Should not happen in this loop, but safe to have
        logger.success(f"Successfully wrote {count} remaining aliases to {REMAINING_ALIASES_FILE}")

    def run(self):
        """Initializes and runs the thread pool, then saves the remaining state."""
        if not self.load_files():
            logger.error("Could not load initial data. Shutting down.")
            return

        if not self.accounts:
            logger.error("No accounts found. Nothing to do.")
            return

        initial_alias_count = self.available_aliases.qsize()
        logger.info(f"Loaded {len(self.accounts)} accounts and {initial_alias_count} aliases.")
        logger.info(f"Starting processing with {MAX_WORKERS} concurrent worker(s).")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(self.process_account, self.accounts)

        logger.success("Processing complete for all accounts.")

        # **CRITICAL STEP**: After all threads are done, save the remaining aliases.
        self._write_remaining_aliases()

    def process_account(self, account: list):
        """
        Processes a single account: warms up, logs in, waits, checks, and adds new aliases.
        """
        email, password = account

        # Initialize session for this thread
        profile = random.choice(BROWSER_PROFILES)
        session = Session(impersonate=profile, proxies=self.proxy_config)
        logger.info(f"[{email}] Starting process with profile: {profile}")

        added_aliases = []

        try:
            # --- STEP 1: SESSION WARM-UP (The Missing Piece) ---
            logger.info(f"[{email}] Warming up session...")
            session.get(LOGIN_PAGE_URL, headers={"Referer": "https://www.google.com/"}, timeout=30)
            session.get(OAUTH_HANDSHAKE_URL, headers={"Origin": "https://power.freenet.de", "Referer": LOGIN_PAGE_URL},
                        timeout=30)
            logger.info(f"[{email}] Session warmed up.")

            # --- STEP 2: AUTHENTICATION ---
            login_payload = {"grant_type": "password", "username": email, "password": password, "world": "2",
                             "webLogin": "true"}
            resp = session.post(LOGIN_URL, data=login_payload, auth=(CLIENT_ID, CLIENT_SECRET), timeout=30)
            resp.raise_for_status()
            access_token = resp.json()["access_token"]
            logger.success(f"[{email}] Login successful.")

            # --- STEP 3: THE PATIENCE COOLDOWN (The Adjustment) ---
            # A longer, more human-like wait to defeat post-login rate limits.
            delay = random.uniform(60, 95)
            logger.info(f"[{email}] Waiting for {delay:.2f} seconds to simulate human behavior...")
            time.sleep(delay)

            # --- STEP 4: FETCH ACCOUNT DETAILS ---
            auth_headers = {'Authorization': f'Bearer {access_token}', 'X-Client': 'fn-cloud-web-web',
                            'Origin': 'https://webmail.freenet.de', 'Referer': 'https://webmail.freenet.de/'}
            accounts_data = session.get(MAIL_ACCOUNTS_URL, headers=auth_headers, timeout=30).json()
            primary_account = accounts_data.get('data', [{}])[0]
            account_id = primary_account.get('account_id')
            existing_aliases = {alias['email'] for alias in primary_account.get('aliases', [])}

            if not account_id: raise ValueError("Could not find correct account_id")
            logger.info(f"[{email}] AccountID: {account_id}. Found {len(existing_aliases)} existing aliases.")

            # --- STEP 5: LOOP TO ADD NEW ALIASES ---
            aliases_to_add_count = MAX_ALIASES_PER_ACCOUNT - len(existing_aliases)
            if aliases_to_add_count <= 0:
                logger.info(f"[{email}] Account already has max aliases. No action needed.")

            for _ in range(aliases_to_add_count):
                new_alias = None
                try:
                    new_alias = self.available_aliases.get_nowait()
                except queue.Empty:
                    logger.warning(f"[{email}] Alias queue is empty. Stopping alias addition for this account.")
                    break

                full_email = f"{new_alias}@freenet.de"
                if full_email in existing_aliases:
                    logger.info(f"[{email}] Alias {full_email} is already on the account, skipping.")
                    continue

                add_payload = {"account_id": account_id, "email": full_email, "setting": "mail.accounts.internal.alias"}

                try:
                    response = session.post(SETTINGS_URL, headers=auth_headers, json=add_payload, timeout=45)
                    if response.status_code == 200:
                        logger.success(f"[{email}] Successfully added alias: {new_alias}")
                        added_aliases.append(new_alias)
                        existing_aliases.add(full_email)
                        time.sleep(random.uniform(3, 6))  # Short delay after a success
                    else:
                        err_data = response.json()
                        err_msg = err_data.get("message", "No error message in response")
                        logger.warning(f"[{email}] API error adding '{new_alias}': {err_msg}")
                        # If rate limited or account limit hit, put alias back and stop for this user.
                        if "Ratelimit" in err_msg or err_data.get("code") == 4101:
                            logger.error(f"[{email}] Stopping alias addition due to limit. Re-queuing '{new_alias}'.")
                            self.available_aliases.put(new_alias)
                            break  # Stop trying for this user
                except (errors.RequestsError, errors.RequestsError) as e:
                    logger.error(
                        f"[{email}] A network error occurred while adding '{new_alias}': {e}. Re-queuing alias.")
                    if new_alias: self.available_aliases.put(new_alias)
                    logger.info(f"[{email}] Stopping work on this account due to persistent network issues.")
                    break

        except Exception as e:
            error_response_text = getattr(e, 'response', {}).text if hasattr(e, 'response') else ""
            logger.critical(f"[{email}] A critical error occurred in the main process: {e}")
            with self.output_lock:
                with CRITICAL_ERRORS_FILE.open("a", encoding='utf-8') as f:
                    f.write(f"{email}:{password} | Error: {e} | Response: {error_response_text}\n")

        finally:
            result_str = f"{email}:{password} [Added: {len(added_aliases)}; Aliases: {', '.join(added_aliases)}]" if added_aliases else f"{email}:{password} [Added: 0]"
            logger.info(f"[{email}] Finished. {result_str}")
            with self.output_lock:
                with OUTPUT_FILE.open("a", encoding='utf-8') as f:
                    f.write(result_str + "\n")
            session.close()


if __name__ == "__main__":
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    for f in [INPUT_FILE, ALIASES_FILE, PROXY_FILE]:
        if not f.exists(): f.touch()

    worker = FreenetAliasAdder()
    worker.run()
