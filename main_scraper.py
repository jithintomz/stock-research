import logging
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Assuming download_concalls.py is in the same directory or accessible in PYTHONPATH
from download_concalls import download_company_concalls

# Configure basic logging
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# File handler for main_scraper logs
main_scraper_file_handler = logging.FileHandler('main_scraper_log.txt')
main_scraper_file_handler.setFormatter(log_formatter)
logger.addHandler(main_scraper_file_handler)


SCREENER_PAGE_URL = "https://www.screener.in/screens/2804103/quality-prmoter-holding-increase/"
DOWNLOAD_CONCALLS_DIR = "downloaded_concalls"
BASE_SCREENER_URL = "https://www.screener.in"

def scrape_screener_data():
    logger.info("Starting main scraper script.")

    # Ensure download directory exists
    try:
        os.makedirs(DOWNLOAD_CONCALLS_DIR, exist_ok=True)
        logger.info(f"Ensured download directory exists: {DOWNLOAD_CONCALLS_DIR}")
    except Exception as e:
        logger.error(f"Could not create download directory {DOWNLOAD_CONCALLS_DIR}: {e}")
        return

    playwright_instance = None
    browser = None

    try:
        logger.info("Initializing Playwright...")
        playwright_instance = sync_playwright().start()
        browser = playwright_instance.chromium.launch(headless=True) # Set headless=False for debugging UI
        page = browser.new_page()
        logger.info("Playwright initialized successfully.")

        logger.info(f"Navigating to Screener page: {SCREENER_PAGE_URL}")
        page.goto(SCREENER_PAGE_URL, timeout=90000) # Increased timeout
        logger.info("Successfully navigated to Screener page.")

        page_num = 1
        while True:
            logger.info(f"Processing page: {page_num}")

            # Wait for the table to load - adjust selector as needed
            try:
                page.wait_for_selector("//div[contains(@class, 'data-table')]/table/tbody/tr", timeout=30000)
                logger.info("Company table loaded.")
            except PlaywrightTimeoutError:
                logger.warning(f"Timeout waiting for company table on page {page_num}. Assuming no more data or page structure changed.")
                break

            # Extract company links from the current page
            # Selector targets <a> tags within the first <td> of each row in the main data table
            company_links_elements = page.query_selector_all("//div[contains(@class, 'data-table')]/table/tbody/tr/td[1]/a[starts-with(@href, '/company/')]")

            if not company_links_elements:
                logger.info(f"No company links found on page {page_num}. This might be the end or an issue.")
                # Check if it's because the table is empty or just no links matching
                rows = page.query_selector_all("//div[contains(@class, 'data-table')]/table/tbody/tr")
                if not rows:
                    logger.info(f"No table rows found on page {page_num}. Definitely the end of data.")
                break

            company_urls_on_page = []
            for link_el in company_links_elements:
                href = link_el.get_attribute('href')
                if href:
                    full_company_url = BASE_SCREENER_URL + href
                    company_urls_on_page.append(full_company_url)

            logger.info(f"Found {len(company_urls_on_page)} company links on page {page_num}.")

            for company_url in company_urls_on_page:
                logger.info(f"Processing company: {company_url}")
                try:
                    success = download_company_concalls(company_url, DOWNLOAD_CONCALLS_DIR)
                    if success:
                        logger.info(f"Successfully downloaded concalls for {company_url}")
                    else:
                        logger.info(f"No concalls downloaded for {company_url} (or none found).")
                except Exception as e_download: # Catch exceptions from the download function itself
                    logger.error(f"Error downloading concalls for {company_url}: {e_download}")

            # Pagination: Find and click "Next" button
            # Common selectors for "Next" button/link on Screener
            next_button_selectors = [
                "//a[@rel='next'][not(contains(@class, 'disabled'))]", # Typical pagination link
                "//button[contains(text(), 'Next')][not(@disabled)]",
                "//a[contains(text(), 'Next')][not(contains(@class, 'disabled'))]"
            ]

            next_button = None
            for selector in next_button_selectors:
                button = page.query_selector(selector)
                if button and button.is_visible() and button.is_enabled():
                    next_button = button
                    break

            if next_button:
                logger.info("Found 'Next' button. Navigating to next page...")
                try:
                    next_button.click()
                    # Add a wait for navigation or a specific element on the next page to ensure it loads
                    page.wait_for_load_state("domcontentloaded", timeout=30000)
                    # Alternatively, wait for the table of the next page
                    # page.wait_for_selector("//div[contains(@class, 'data-table')]/table/tbody/tr", timeout=30000)
                    page_num += 1
                except PlaywrightTimeoutError:
                    logger.warning("Timeout waiting for next page to load. Assuming end of pagination.")
                    break
                except Exception as e_click:
                    logger.error(f"Error clicking 'Next' button: {e_click}. Stopping pagination.")
                    break
            else:
                logger.info("No 'Next' button found or it's disabled. End of pages.")
                break

        logger.info("Finished processing all pages.")

    except PlaywrightTimeoutError as pte:
        logger.error(f"Playwright operation timed out: {pte}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in main scraper: {e}", exc_info=True)
    finally:
        logger.info("Cleaning up Playwright resources...")
        if browser:
            try:
                browser.close()
                logger.info("Browser closed.")
            except Exception as e_close_browser:
                logger.error(f"Error closing browser: {e_close_browser}")
        if playwright_instance:
            try:
                playwright_instance.stop()
                logger.info("Playwright instance stopped.")
            except Exception as e_stop_pw:
                logger.error(f"Error stopping Playwright instance: {e_stop_pw}")
        logger.info("Main scraper script finished.")

if __name__ == "__main__":
    scrape_screener_data()
