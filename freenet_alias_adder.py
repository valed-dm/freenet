import threading
from queue import Queue, Empty
import os
import time
import random
import sys
import zipfile
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# FIX for [SSL: CERTIFICATE_VERIFY_FAILED]
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import undetected_chromedriver as uc

# --- Configuration ---
MAX_THREADS = 1
HEADLESS_MODE = False
MAX_ALIASES_PER_ACCOUNT = 10
DEBUG = True

# --- Freenet URLs ---
LOGIN_PAGE_URL = "https://power.freenet.de/"
SETTINGS_URL = "https://email.freenet.de/settings/aliases"
ADD_ALIAS_URL = "https://email.freenet.de/settings/aliases/add"


def print_debug(message):
    if DEBUG: print(f"[DEBUG] {message}")

class FreenetManagerSelenium:
    def __init__(self, email, password, proxy_config):
        self.email = email
        self.password = password
        self.driver = None
        self.proxy_config = proxy_config
        self.proxy_extension_path = f'proxy_auth_extension_{threading.get_ident()}.zip'

    def _create_proxy_extension(self, proxy_host, proxy_port, proxy_user, proxy_pass):
        manifest_json = """
        {
            "version": "1.0.0", "manifest_version": 2, "name": "Freenet Proxy Auth",
            "permissions": ["proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>", "webRequest", "webRequestBlocking"],
            "background": { "scripts": ["background.js"] }
        }
        """
        background_js = f"""
        var config = {{
            mode: "fixed_servers",
            rules: {{ singleProxy: {{ scheme: "http", host: "{proxy_host}", port: parseInt({proxy_port}) }}, bypassList: ["localhost"] }}
        }};
        chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});
        function callbackFn(details) {{ return {{ authCredentials: {{ username: "{proxy_user}", password: "{proxy_pass}" }} }}; }}
        chrome.webRequest.onAuthRequired.addListener(callbackFn, {{urls: ["<all_urls>"]}}, ['blocking']);
        """
        with zipfile.ZipFile(self.proxy_extension_path, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)

    def _setup_driver(self):
        options = uc.ChromeOptions()
        if self.proxy_config:
            try:
                parts = self.proxy_config.strip().split(':')
                if len(parts) == 2:
                    host, port = parts
                    options.add_argument(f"--proxy-server=http://{host}:{port}")
                    print_debug(f"[{self.email}] Using unauthenticated proxy {host}:{port}")
                elif len(parts) == 4:
                    host, port, user, pw = parts
                    self._create_proxy_extension(host, port, user, pw)
                    options.add_extension(self.proxy_extension_path)
                    print_debug(f"[{self.email}] Using authenticated proxy {host}:{port}")
                else:
                    raise ValueError("Invalid proxy format")
            except Exception as e:
                print(f"[ERROR] [{self.email}] Could not set proxy: {e}")
                return False

        if HEADLESS_MODE:
            options.add_argument("--headless")

        try:
            self.driver = uc.Chrome(options=options, use_subprocess=True)
            self.driver.set_page_load_timeout(30)
            print_debug(f"[{self.email}] Undetected WebDriver initialized.")
            return True
        except Exception as e:
            print(f"[ERROR] [{self.email}] Failed to initialize Undetected WebDriver: {e}")
            return False


    def login(self):
        print_debug(f"[{self.email}] Attempting to login via browser...")
        if not self._setup_driver():
            return False
        try:
            self.driver.get(LOGIN_PAGE_URL)

            # --- SNIPPET TO SAVE THE HTML ---
            debug_filename = f"login_page_{self.email.replace('@','_')}.html"
            with open(f"debug/{debug_filename}", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print_debug(f"[{self.email}] Page HTML saved to {debug_filename}")
            # --- END SNIPPET ---

            wait = WebDriverWait(self.driver, 20)

            # --- CORRECTED LOCATOR for Username ---
            user_field = wait.until(EC.presence_of_element_located(
                (By.XPATH, '//input[@placeholder="E-Mail-Adresse"]')
            ))
            print_debug(f"[{self.email}] Login form has rendered, found username field.")
            user_field.send_keys(self.email)

            # --- CORRECTED LOCATOR for Password ---
            self.driver.find_element(By.XPATH, '//input[@placeholder="Passwort"]').send_keys(self.password)

            # --- CORRECTED LOCATOR for Login Button ---
            self.driver.find_element(By.CSS_SELECTOR, 'a.frn_button.login').click()

            wait.until(EC.url_contains("email.freenet.de"))
            print_debug(f"[{self.email}] Login successful.")
            return True
        except Exception as e:
            print(f"[{self.email}] Login failed. Reason: {e}")
            try:
                self.driver.save_screenshot(f"debug/error_{self.email.replace('@','_')}.png")
            except: pass
            return False


    def get_current_alias_count(self):
        try:
            self.driver.get(SETTINGS_URL)
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'E-Mail-Aliasse')]")))
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            count = len(soup.select('div.alias-address'))
            print_debug(f"[{self.email}] Found {count} existing aliases.")
            return count
        except Exception as e:
            print(f"[{self.email}] Could not get current alias count: {e}")
            return 0

    def add_alias(self, alias_to_add):
        try:
            print_debug(f"[{self.email}] Attempting to add alias: {alias_to_add}")
            self.driver.get(ADD_ALIAS_URL)
            wait = WebDriverWait(self.driver, 10)
            alias_input = wait.until(EC.presence_of_element_located((By.NAME, "alias")))
            add_button = self.driver.find_element(By.XPATH, '//button[contains(text(), "E-Mail-Alias anlegen")]')
            alias_input.send_keys(alias_to_add)
            add_button.click()
            wait.until(EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), 'wurde erfolgreich eingerichtet')]")))
            print_debug(f"[{self.email}] Successfully added alias: {alias_to_add}")
            return True
        except Exception as e:
            print(f"[{self.email}] Failed to add alias '{alias_to_add}'. It might be taken.")
            return False

    def close(self):
        if self.driver:
            self.driver.quit()
        if os.path.exists(self.proxy_extension_path):
            try:
                os.remove(self.proxy_extension_path)
            except OSError as e:
                print(f"Error removing file {self.proxy_extension_path}: {e}")

# --- Global Queues and Main Logic ---
accounts_queue = Queue()
aliases_queue = Queue()
output_lock = threading.Lock()
aliases_lock = threading.Lock()

def worker(proxy_list):
    proxy = random.choice(proxy_list) if proxy_list else None
    while not accounts_queue.empty():
        try:
            account_details = accounts_queue.get_nowait()
        except Empty:
            break
        try:
            email, password = account_details.split(':', 1)
        except ValueError:
            print(f"[ERROR] Invalid format: {account_details}")
            accounts_queue.task_done()
            continue

        manager = FreenetManagerSelenium(email, password, proxy)
        if not manager.login():
            with output_lock:
                with open("output.txt", "a", encoding='utf-8') as f:
                    f.write(f"{email}:{password} [Error: Login Failed]\n")
            manager.close()
            accounts_queue.task_done()
            continue

        current_aliases = manager.get_current_alias_count()
        aliases_needed = MAX_ALIASES_PER_ACCOUNT - current_aliases
        added_aliases = []

        if aliases_needed > 0:
            for _ in range(aliases_needed):
                with aliases_lock:
                    if aliases_queue.empty():
                        print(f"[{email}] No more aliases available.")
                        break
                    new_alias = aliases_queue.get()

                if manager.add_alias(new_alias):
                    added_aliases.append(new_alias)
                    time.sleep(random.uniform(1, 2.5))

        with output_lock:
            with open("output.txt", "a", encoding='utf-8') as f:
                if added_aliases:
                    f.write(f"{email}:{password} [Add: {len(added_aliases)}; {', '.join(added_aliases)}]\n")
                elif aliases_needed <= 0:
                    f.write(f"{email}:{password} [Info: Alias limit reached ({current_aliases})]\n")
                else:
                    f.write(f"{email}:{password} [Info: No aliases were added]\n")

        manager.close()
        accounts_queue.task_done()

def setup_and_load_data(input_dir):
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
        sys.exit(f"Created directory '{input_dir}'. Please add input files and run again.")

    with open(os.path.join(input_dir, "input.txt"), 'r') as f:
        accounts = [line.strip() for line in f if line.strip()]
        for acc in accounts: accounts_queue.put(acc)
    print(f"Loaded {len(accounts)} accounts from data/input.txt.")

    with open(os.path.join(input_dir, "aliases.txt"), 'r') as f:
        aliases = [line.strip() for line in f if line.strip()]
        for alias in aliases: aliases_queue.put(alias)
    print(f"Loaded {len(aliases)} aliases from data/aliases.txt.")

    proxies = []
    try:
        with open(os.path.join(input_dir, "proxy.txt"), 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        if not proxies: print("[WARNING] proxy.txt is empty. Running without proxies.")
        else: print(f"Loaded {len(proxies)} proxies.")
    except FileNotFoundError:
        print("[WARNING] proxy.txt not found.")

    return proxies

def main():
    print("--- Freenet Alias Adder (Final Corrected Version) ---")

    if os.path.exists("output.txt"):
        os.remove("output.txt")

    proxies = setup_and_load_data("data")

    threads = []
    thread_count = min(MAX_THREADS, accounts_queue.qsize())
    print(f"Starting {thread_count} worker threads...")

    for _ in range(thread_count):
        thread = threading.Thread(target=worker, args=(proxies,))
        thread.daemon = True
        thread.start()
        threads.append(thread)

    accounts_queue.join()
    print("\n--- All tasks completed. Check output.txt for results. ---")

if __name__ == "__main__":
    main()
