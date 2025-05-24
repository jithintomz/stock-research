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

def main():
    playwright_instance = None
    browser = None
    page = None
    
    try:
        logger.info("Starting Playwright setup...")
        playwright_instance = sync_playwright().start()
        browser = playwright_instance.chromium.launch()
        page = browser.new_page()
        logger.info("Playwright setup successful.")
    except Exception as e:
        logger.critical(f"Failed to initialize Playwright or launch browser: {e}")
        if browser:
            browser.close()
        if playwright_instance:
            playwright_instance.stop()
        return

    try:
        screener_url = "https://www.screener.in/company/SUYOG/"
        logger.info(f"Navigating to Screener URL: {screener_url}")
        page.goto(screener_url, timeout=60000) # Added timeout
        logger.info("Successfully navigated to Screener URL.")
    except Exception as e:
        logger.error(f"Failed to navigate to {screener_url}: {e}")
        if browser:
            browser.close()
        if playwright_instance:
            playwright_instance.stop()
        return

    transcript_urls = []
    try:
        logger.info("Attempting to find 'Concalls' section and extract links...")
        concalls_section_heading = page.query_selector('//h2[text()="Concalls"]')

        if not concalls_section_heading:
            logger.error("'Concalls' section heading not found. Exiting.")
            if browser:
                browser.close()
            if playwright_instance:
                playwright_instance.stop()
            return

        logger.info("Found 'Concalls' section heading.")
        card_element = concalls_section_heading.query_selector('xpath=ancestor::div[contains(@class, "card")]')

        if not card_element:
            logger.error("Could not find the parent card element for 'Concalls' section. Exiting.")
            if browser:
                browser.close()
            if playwright_instance:
                playwright_instance.stop()
            return
            
        logger.info("Found parent card element for 'Concalls'.")
        links = card_element.query_selector_all('//a[contains(text(), "Transcript") and contains(@href, ".pdf")]')
        
        if not links:
            logger.error("No links with 'Transcript' and '.pdf' found in the 'Concalls' card content. Exiting.")
            if browser:
                browser.close()
            if playwright_instance:
                playwright_instance.stop()
            return

        logger.info(f"Found {len(links)} potential transcript links.")
        for link_element in links:
            href = link_element.get_attribute('href')
            if href and "bseindia.com" in href:
                transcript_urls.append(href)
        
        if not transcript_urls:
            logger.error("No transcript URLs from bseindia.com were extracted. Exiting.")
            if browser:
                browser.close()
            if playwright_instance:
                playwright_instance.stop()
            return
        logger.info(f"Successfully extracted {len(transcript_urls)} transcript URLs from bseindia.com.")

    except Exception as e:
        logger.error(f"Error during 'Concalls' section processing or link extraction: {e}")
        if browser:
            browser.close()
        if playwright_instance:
            playwright_instance.stop()
        return

    # Create download directory
    download_dir = "concall_transcripts"
    try:
        os.makedirs(download_dir, exist_ok=True)
        logger.info(f"Ensured download directory exists: {download_dir}")
    except Exception as e:
        logger.error(f"Could not create download directory {download_dir}: {e}")
        if browser:
            browser.close()
        if playwright_instance:
            playwright_instance.stop()
        return

    logger.info("Starting transcript downloads...")
    for url in transcript_urls:
        download_page = None # Define here for broader scope in finally
        try:
            logger.info(f"Attempting to download: {url}")
            
            # Start waiting for the download before triggering it
            with page.expect_download(timeout=60000) as download_info: # Added timeout
                # Using a new page for each download
                download_page = browser.new_page()
                logger.debug(f"Navigating new page to PDF URL: {url}")
                download_page.goto(url, timeout=120000) # Increased timeout for potentially large PDFs
            
            download = download_info.value
            logger.debug(f"Download event triggered for {url}, suggested filename: {download.suggested_filename}")
            
            temp_download_path = download.path() 
            if not temp_download_path:
                raise Exception("Playwright download path was not available.")
            logger.debug(f"Temporary download path: {temp_download_path}")

            suggested_filename = download.suggested_filename
            if not suggested_filename:
                logger.warning(f"No suggested filename for {url}. Deriving from URL.")
                suggested_filename = url.split("/")[-1]
                if "?" in suggested_filename:
                    suggested_filename = suggested_filename.split("?")[0]
                if not suggested_filename.endswith(".pdf"):
                     suggested_filename += ".pdf"
            
            save_path = os.path.join(download_dir, suggested_filename)
            
            download.save_as(save_path)
            logger.info(f"Successfully downloaded and saved: {save_path}")

        except Exception as e:
            logger.error(f"Failed to download {url}. Error: {e}")
            # Continue to the next download
        finally:
            if download_page and not download_page.is_closed():
                try:
                    download_page.close()
                    logger.debug(f"Closed download page for {url}")
                except Exception as e:
                    logger.warning(f"Could not close download page for {url}. Error: {e}")
    
    logger.info("All transcript download attempts finished.")
    if browser:
        browser.close()
    if playwright_instance:
        playwright_instance.stop()
    logger.info("Playwright closed and script finished.")

if __name__ == "__main__":
    main()
