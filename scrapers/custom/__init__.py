"""Custom site-specific scrapers for individual event websites."""

from typing import Dict, Callable, List, Tuple, Optional
from common.model import Event, Race

# Registry of domain-specific scrapers
# Maps domain patterns to scraper functions
SCRAPER_REGISTRY: Dict[str, Callable[[str], Tuple[Optional[Event], List[Race]]]] = {}


def register_scraper(domain_pattern: str):
    """Decorator to register a custom scraper for a specific domain."""
    def decorator(func):
        SCRAPER_REGISTRY[domain_pattern] = func
        return func
    return decorator


def get_scraper_for_url(url: str) -> Optional[Callable]:
    """Find appropriate scraper for given URL based on domain."""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.lower()
    
    # Check exact domain matches first
    for pattern, scraper in SCRAPER_REGISTRY.items():
        if pattern in domain:
            return scraper
    
    return None
