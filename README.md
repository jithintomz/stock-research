# Conference Call Transcript Downloader

This script automates the download of conference call transcripts for a specific company (currently hardcoded for "SUYOG") from the Screener.in website. It extracts PDF links pointing to bseindia.com and saves them locally.

## Prerequisites

- Python 3.x
- Pip (Python package installer)

## Setup Instructions

1.  **Clone the repository (or download the script):**
    ```bash
    # If you have git installed
    git clone <repository_url>
    cd <repository_directory>
    # Otherwise, download download_concalls.py manually
    ```

2.  **Install Playwright:**
    Playwright is used for browser automation to fetch the page content.
    ```bash
    pip install playwright
    ```

3.  **Install browser drivers for Playwright:**
    This command downloads the necessary browser binaries (Chromium, Firefox, WebKit) for Playwright.
    ```bash
    playwright install
    ```
    -   **Note for Linux users:** If the above command reports missing dependencies, you might need to install them manually. The command `playwright install --with-deps` can help by attempting to install these system dependencies for you (may require `sudo`). Alternatively, you can list them with `python -m playwright print-deps` and install them with your package manager.
    -   **Note for system-wide installation:** On some systems, installing browser dependencies (especially if using `--with-deps` or installing manually) might require `sudo` (on Linux) or Administrator privileges (on Windows). It's often recommended to install Playwright and its drivers in a Python virtual environment to avoid permission issues and manage dependencies per project.

## How to Run

1.  **Navigate to the directory:**
    Open your terminal or command prompt and change to the directory where `download_concalls.py` is located.
    ```bash
    cd path/to/script_directory
    ```

2.  **Run the script:**
    Execute the script using Python.
    ```bash
    python download_concalls.py
    ```

## Output

-   **Transcripts:** Successfully downloaded PDF transcripts will be saved in a directory named `concall_transcripts`, which will be created in the same directory as the script.
-   **Logs:** A detailed log file named `download_log.txt` will be created (or appended to) in the script's directory. This file contains information about the script's execution, including successful downloads and any errors encountered.

## Troubleshooting

-   **Proxy Issues:** If you are behind a corporate proxy, Playwright might have trouble downloading browser drivers or accessing websites. You may need to configure `HTTP_PROXY` and `HTTPS_PROXY` environment variables.
-   **`playwright install` fails:**
    -   Ensure you have a stable internet connection.
    -   Check for error messages regarding missing system dependencies, especially on Linux (see setup step 3).
    -   Refer to the [official Playwright documentation](https://playwright.dev/python/docs/intro) for detailed installation and troubleshooting guides.
-   **Script Errors:** Check `download_log.txt` for specific error messages. The website structure of Screener.in or BSE India might change over time, which could break the script's selectors used to find information.

---
*This script is for educational purposes. Ensure you comply with the terms of service of the websites you are scraping.*
