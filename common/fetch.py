"""HTTP fetching utilities with retry, user-agent rotation, and rate limiting."""

import os
import random
import time
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential


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
