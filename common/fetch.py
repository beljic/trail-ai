"""HTTP fetching utilities with retry, user-agent rotation, and rate limiting."""

import os
import random
import time
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]


def get_random_ua() -> str:
    """Get a random user agent string."""
    return random.choice(USER_AGENTS)


def get_sleep_duration() -> float:
    """
    Get sleep duration for politeness delay.

    Uses SCRAPER_SLEEP_BASE_MS env var if set, otherwise defaults to 800-1400ms range.

    Returns:
        Sleep duration in seconds
    """
    base_ms = int(os.getenv("SCRAPER_SLEEP_BASE_MS", "800"))
    # Add some randomness (±25%)
    variation = int(base_ms * 0.25)
    sleep_ms = random.randint(base_ms - variation, base_ms + variation)
    return sleep_ms / 1000.0


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def get(url: str, timeout: int = 30) -> Optional[requests.Response]:
    """
    Fetch URL with retry logic, random user agent, and politeness delay.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Response object if successful, None if all retries failed

    Raises:
        requests.RequestException: If all retry attempts fail
    """
    headers = {
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,sr;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    # Politeness delay before request
    sleep_duration = get_sleep_duration()
    time.sleep(sleep_duration)

    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()

    return response


def get_safe(url: str, timeout: int = 30) -> Optional[requests.Response]:
    """
    Safe version of get() that catches exceptions and returns None on failure.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Response object if successful, None if failed
    """
    try:
        return get(url, timeout=timeout)
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None


def download_image(url: str, save_path: str, timeout: int = 30) -> bool:
    """
    Download an image from URL and save it locally.

    Args:
        url: Image URL to download
        save_path: Local path where to save the image
        timeout: Request timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    import os
    from pathlib import Path

    try:
        # Create directory if it doesn't exist
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # Check if file already exists
        if os.path.exists(save_path):
            return True

        headers = {
            "User-Agent": get_random_ua(),
            "Accept": "image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Connection": "keep-alive",
        }

        # Politeness delay
        sleep_duration = get_sleep_duration()
        time.sleep(sleep_duration)

        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()

        # Write image to file
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True

    except Exception as e:
        print(f"Failed to download image {url}: {e}")
        return False


def download_image_safe(url: str, save_dir: str, race_id: str) -> Optional[str]:
    """
    Download an image and save it with race ID as filename.

    Args:
        url: Image URL to download
        save_dir: Directory where to save images
        race_id: Race ID to use as filename base

    Returns:
        Local path to saved image if successful, None otherwise
    """
    from pathlib import Path
    import mimetypes

    if not url:
        return None

    try:
        # Guess extension from URL
        ext = Path(url).suffix.lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            ext = '.jpg'  # Default to jpg

        save_path = f"{save_dir}/{race_id}{ext}"

        if download_image(url, save_path):
            return save_path
        return None

    except Exception as e:
        print(f"Error saving image for race {race_id}: {e}")
        return None


def get_cloudflare_safe(url: str, timeout: int = 30) -> Optional[requests.Response]:
    """
    Fetch URL using cloudscraper to bypass Cloudflare protection.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Response object if successful, None if failed
    """
    if not CLOUDSCRAPER_AVAILABLE:
        print(f"cloudscraper not available, falling back to regular request")
        return get_safe(url, timeout)

    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

        # Politeness delay
        sleep_duration = get_sleep_duration()
        time.sleep(sleep_duration)

        response = scraper.get(url, timeout=timeout)
        response.raise_for_status()
        return response

    except Exception as e:
        print(f"Failed to fetch {url} with cloudscraper: {e}")
        return None


def get_selenium_safe(url: str, timeout: int = 30, wait_for: str = None) -> Optional[str]:
    """
    Fetch URL using Selenium headless browser (bypasses most bot detection).

    Args:
        url: URL to fetch
        timeout: Page load timeout in seconds
        wait_for: Optional CSS selector to wait for before returning HTML

    Returns:
        HTML content as string if successful, None if failed
    """
    if not SELENIUM_AVAILABLE:
        print(f"Selenium not available, falling back to regular request")
        resp = get_safe(url, timeout)
        return resp.text if resp else None

    driver = None
    try:
        # Configure Chrome options for headless mode
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(f'user-agent={get_random_ua()}')

        # Politeness delay
        sleep_duration = get_sleep_duration()
        time.sleep(sleep_duration)

        # Initialize driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(timeout)

        # Fetch page
        driver.get(url)

        # Wait for specific element if requested
        if wait_for:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
            )
        else:
            # Default: wait for body tag
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )

        # Get page source
        html = driver.page_source
        return html

    except Exception as e:
        print(f"Failed to fetch {url} with Selenium: {e}")
        return None

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
