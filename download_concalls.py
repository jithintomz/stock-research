from playwright.sync_api import sync_playwright
import os
import logging

# Configure logging
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler('download_log.txt')
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)


def download_company_concalls(company_url: str, download_root_dir: str) -> bool:
    playwright_instance = None
    browser = None
    page = None
    downloaded_something = False

    try:
        logger.info(f"[{company_url}] Starting Playwright setup...")
        playwright_instance = sync_playwright().start()
        browser = playwright_instance.chromium.launch()
        page = browser.new_page()
        logger.info(f"[{company_url}] Playwright setup successful.")
    except Exception as e:
        logger.critical(f"[{company_url}] Failed to initialize Playwright or launch browser: {e}")
        if browser:
            browser.close()
        if playwright_instance:
            playwright_instance.stop()
        return False

    try:
        logger.info(f"[{company_url}] Navigating to Screener URL: {company_url}")
        page.goto(company_url, timeout=60000)
        logger.info(f"[{company_url}] Successfully navigated to Screener URL.")
    except Exception as e:
        logger.error(f"[{company_url}] Failed to navigate to {company_url}: {e}")
        if browser:
            browser.close()
        if playwright_instance:
            playwright_instance.stop()
        return False

    transcript_urls = []
    try:
        logger.info(f"[{company_url}] Attempting to find 'Concalls' section and extract links...")
        concalls_section_heading = page.query_selector('//h3[text()="Concalls"]')

        if not concalls_section_heading:
            logger.warning(f"[{company_url}] 'Concalls' section heading not found.")
            if browser:
                browser.close()
            if playwright_instance:
                playwright_instance.stop()
            return False

        logger.info(f"[{company_url}] Found 'Concalls' section heading.")
        card_element = concalls_section_heading.query_selector('xpath=ancestor::div[contains(@class, "documents") and contains(@class, "concalls") and contains(@class, "flex-column")]')

        if not card_element:
            logger.warning(f"[{company_url}] Could not find the parent element for 'Concalls' section.")
            if browser:
                browser.close()
            if playwright_instance:
                playwright_instance.stop()
            return False
            
        logger.info(f"[{company_url}] Found parent element for 'Concalls'.")
        links = card_element.query_selector_all('a.concall-link')
        for link_element in links:
            href = link_element.get_attribute('href')
            if href and href.lower().endswith('.pdf'):
                transcript_urls.append(href)

        if not transcript_urls:
            logger.info(f"[{company_url}] No PDF transcript URLs found in 'Concalls' section.")
            if browser:
                browser.close()
            if playwright_instance:
                playwright_instance.stop()
            return False
        logger.info(f"[{company_url}] Successfully extracted {len(transcript_urls)} PDF transcript URLs.")

    except Exception as e:
        logger.error(f"[{company_url}] Error during 'Concalls' section processing or link extraction: {e}")
        if browser:
            browser.close()
        if playwright_instance:
            playwright_instance.stop()
        return False

    # Determine company name and create download directory
    try:
        # Extract company name from URL (e.g., INFY from https://www.screener.in/company/INFY/)
        company_name = company_url.strip('/').split('/')[-1]
        if not company_name:
            raise ValueError("Could not extract company name from URL")

        company_download_dir = os.path.join(download_root_dir, company_name)
        # Directory creation is deferred until a successful download
    except ValueError as e:
        logger.error(f"[{company_url}] Error determining company name or download path: {e}")
        if browser:
            browser.close()
        if playwright_instance:
            playwright_instance.stop()
        return False

    logger.info(f"[{company_url}] Starting transcript downloads to {company_download_dir} (if any PDFs are downloaded)...")
    for href in transcript_urls:
        download_page = None # Ensure download_page is defined in this scope
        try:
            download_page = browser.new_page() # Create a new page for each download attempt
            logger.info(f"[{company_url}] Attempting to download: {href}")

            # Go to the Screener page where the link is present
            download_page.goto(company_url, timeout=60000)

            # Wait for the Concalls section to be visible
            download_page.wait_for_selector('h3:text("Concalls")', timeout=10000)

            # Wait for the specific link to be present
            selector = f'a.concall-link[href="{href}"]'
            download_page.wait_for_selector(selector, timeout=10000)

            with download_page.expect_download(timeout=120000) as download_info:
                download_page.click(selector)

            download = download_info.value
            logger.debug(f"[{company_url}] Download event triggered for {href}, suggested filename: {download.suggested_filename}")

            temp_download_path = download.path()
            if not temp_download_path:
                raise Exception("Playwright download path was not available.")
            logger.debug(f"[{company_url}] Temporary download path: {temp_download_path}")

            suggested_filename = download.suggested_filename
            if not suggested_filename:
                logger.warning(f"[{company_url}] No suggested filename for {href}. Deriving from URL.")
                suggested_filename = href.split("/")[-1]
                if "?" in suggested_filename:
                    suggested_filename = suggested_filename.split("?")[0]
                if not suggested_filename.lower().endswith(".pdf"): # ensure .pdf check is case-insensitive
                    suggested_filename += ".pdf"

            # Create company-specific download directory if it doesn't exist and this is the first successful download
            if not downloaded_something and not os.path.exists(company_download_dir):
                try:
                    os.makedirs(company_download_dir, exist_ok=True)
                    logger.info(f"[{company_url}] Created download directory: {company_download_dir}")
                except Exception as e_dir:
                    logger.error(f"[{company_url}] Could not create download directory {company_download_dir}: {e_dir}")
                    # Continue to try other downloads, but this company's downloads might fail to save
                    # Or decide to return False here if directory creation is critical for any download
                    raise # Re-raise to stop this download attempt if dir creation fails

            save_path = os.path.join(company_download_dir, suggested_filename)
            download.save_as(save_path)
            logger.info(f"[{company_url}] Successfully downloaded and saved: {save_path}")
            downloaded_something = True # Mark that at least one PDF was downloaded

        except Exception as e:
            logger.error(f"[{company_url}] Failed to download {href}. Error: {e}")
        finally:
            if download_page and not download_page.is_closed():
                try:
                    download_page.close()
                    logger.debug(f"[{company_url}] Closed download page for {href}")
                except Exception as e_close:
                    logger.warning(f"[{company_url}] Could not close download page for {href}. Error: {e_close}")
    
    if downloaded_something:
        logger.info(f"[{company_url}] Finished transcript downloads for {company_url}. {len(transcript_urls)} links processed.")
    else:
        logger.info(f"[{company_url}] No PDFs were downloaded for {company_url}.")

    if browser:
        browser.close()
    if playwright_instance:
        playwright_instance.stop()
    logger.info(f"[{company_url}] Playwright closed. Script finished for this company.")
    return downloaded_something

# def main():
#     playwright_instance = None
#     browser = None
#     page = None

#     try:
#         logger.info("Starting Playwright setup...")
#         playwright_instance = sync_playwright().start()
#         browser = playwright_instance.chromium.launch()
#         page = browser.new_page()
#         logger.info("Playwright setup successful.")
#     except Exception as e:
#         logger.critical(f"Failed to initialize Playwright or launch browser: {e}")
#         if browser:
#             browser.close()
#         if playwright_instance:
#             playwright_instance.stop()
#         return

#     try:
#         screener_url = "https://www.screener.in/company/SUYOG/"
#         logger.info(f"Navigating to Screener URL: {screener_url}")
#         page.goto(screener_url, timeout=60000) # Added timeout
#         logger.info("Successfully navigated to Screener URL.")
#     except Exception as e:
#         logger.error(f"Failed to navigate to {screener_url}: {e}")
#         if browser:
#             browser.close()
#         if playwright_instance:
#             playwright_instance.stop()
#         return

#     transcript_urls = []
#     try:
#         logger.info("Attempting to find 'Concalls' section and extract links...")
#         concalls_section_heading = page.query_selector('//h3[text()="Concalls"]')

#         if not concalls_section_heading:
#             logger.error("'Concalls' section heading not found. Exiting.")
#             if browser:
#                 browser.close()
#             if playwright_instance:
#                 playwright_instance.stop()
#             return

#         logger.info("Found 'Concalls' section heading.")
#         # Find the parent element with classes 'documents concalls flex-column'
#         card_element = concalls_section_heading.query_selector('xpath=ancestor::div[contains(@class, "documents") and contains(@class, "concalls") and contains(@class, "flex-column")]')

#         if not card_element:
#             logger.error("Could not find the parent element with classes 'documents concalls flex-column' for 'Concalls' section. Exiting.")
#             if browser:
#                 browser.close()
#             if playwright_instance:
#                 playwright_instance.stop()
#             return

#         logger.info("Found parent element with classes 'documents concalls flex-column' for 'Concalls'.")
#         # Find all links with class 'concall-link' and href ending with .pdf
#         links = card_element.query_selector_all('a.concall-link')
#         transcript_urls = []
#         for link_element in links:
#             href = link_element.get_attribute('href')
#             if href and href.lower().endswith('.pdf'):
#                 transcript_urls.append(href)

#         if not transcript_urls:
#             logger.error("No transcript URLs with class 'concall-link' and ending with .pdf were found. Exiting.")
#             if browser:
#                 browser.close()
#             if playwright_instance:
#                 playwright_instance.stop()
#             return
#         logger.info(f"Successfully extracted {len(transcript_urls)} transcript URLs with class 'concall-link' and ending with .pdf.")

#     except Exception as e:
#         logger.error(f"Error during 'Concalls' section processing or link extraction: {e}")
#         if browser:
#             browser.close()
#         if playwright_instance:
#             playwright_instance.stop()
#         return

#     # Create download directory
#     download_dir = "concall_transcripts"
#     try:
#         os.makedirs(download_dir, exist_ok=True)
#         logger.info(f"Ensured download directory exists: {download_dir}")
#     except Exception as e:
#         logger.error(f"Could not create download directory {download_dir}: {e}")
#         if browser:
#             browser.close()
#         if playwright_instance:
#             playwright_instance.stop()
#         return

#     logger.info("Starting transcript downloads...")
#     for href in transcript_urls:
#         download_page = browser.new_page()
#         try:
#             logger.info(f"Attempting to download by clicking link: {href}")

#             # Go to the Screener page where the link is present
#             download_page.goto(screener_url, timeout=60000)

#             # Wait for the Concalls section to be visible
#             download_page.wait_for_selector('h3:text("Concalls")', timeout=10000)

#             # Wait for the specific link to be present
#             selector = f'a.concall-link[href="{href}"]'
#             download_page.wait_for_selector(selector, timeout=10000)

#             with download_page.expect_download(timeout=120000) as download_info:
#                 download_page.click(selector)

#             download = download_info.value
#             logger.debug(f"Download event triggered for {href}, suggested filename: {download.suggested_filename}")

#             temp_download_path = download.path()
#             if not temp_download_path:
#                 raise Exception("Playwright download path was not available.")
#             logger.debug(f"Temporary download path: {temp_download_path}")

#             suggested_filename = download.suggested_filename
#             if not suggested_filename:
#                 logger.warning(f"No suggested filename for {href}. Deriving from URL.")
#                 suggested_filename = href.split("/")[-1]
#                 if "?" in suggested_filename:
#                     suggested_filename = suggested_filename.split("?")[0]
#                 if not suggested_filename.endswith(".pdf"):
#                     suggested_filename += ".pdf"

#             save_path = os.path.join(download_dir, suggested_filename)
#             download.save_as(save_path)
#             logger.info(f"Successfully downloaded and saved: {save_path}")

#         except Exception as e:
#             logger.error(f"Failed to download {href}. Error: {e}")
#         finally:
#             if download_page and not download_page.is_closed():
#                 try:
#                     download_page.close()
#                     logger.debug(f"Closed download page for {href}")
#                 except Exception as e:
#                     logger.warning(f"Could not close download page for {href}. Error: {e}")

#     logger.info("All transcript download attempts finished.")
#     if browser:
#         browser.close()
#     if playwright_instance:
#         playwright_instance.stop()
#     logger.info("Playwright closed and script finished.")

# if __name__ == "__main__":
#    main()
