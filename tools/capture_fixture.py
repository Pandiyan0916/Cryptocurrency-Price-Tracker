"""
tools/capture_fixture.py
-------------------------
Captures a real static HTML fixture from live CoinMarketCap.
Saves the table HTML (with at least 12 valid <tr> rows) to tests/fixtures/sample_table.html.
Refuses to save if the page is a Chrome error page or contains < 12 rows.
"""

import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "sample_table.html"


def capture_fixture() -> None:
    print("Launching Chrome to capture live fixture...")
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.page_load_strategy = "none"

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)

    try:
        url = "https://coinmarketcap.com/"
        print(f"Navigating to {url}...")
        driver.get(url)

        # Wait for page ready
        time.sleep(5)

        page_src = driver.page_source or ""
        if "#main-frame-error" in page_src or "net::ERR_" in page_src or "error-code" in page_src:
            raise RuntimeError("ERROR: Chrome loaded an error page. Refusing to save fixture.")

        # Poll for table rows up to 30s
        found_rows = 0
        for i in range(15):
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            found_rows = len(rows)
            if found_rows >= 12:
                break
            print(f"Waiting for table rows... (found {found_rows}/12, attempt {i+1}/15)")
            time.sleep(2)

        if found_rows < 12:
            raise RuntimeError(f"ERROR: Found only {found_rows} rows (minimum 12 required). Refusing to save fixture.")

        table_el = driver.find_element(By.CSS_SELECTOR, "table")
        table_html = table_el.get_attribute("outerHTML")

        # Parse with BeautifulSoup to slice the first 12 rows cleanly
        soup = BeautifulSoup(table_html, "html.parser")
        tbody = soup.find("tbody")
        if tbody:
            trs = tbody.find_all("tr", recursive=False)
            if len(trs) > 12:
                # keep first 12 trs
                for tr in trs[12:]:
                    tr.decompose()

        cleaned_html = str(soup)

        FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_PATH.write_text(cleaned_html, encoding="utf-8")
        print(f"SUCCESS: Saved captured table HTML with {min(found_rows, 12)} rows to {FIXTURE_PATH}")

    finally:
        driver.quit()
        print("Browser closed.")


if __name__ == "__main__":
    capture_fixture()
