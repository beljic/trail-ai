"""
Scraper for https://www.racesmanager.com/Home/Results
Similar structure to trka_rs.py, but adapted for racesmanager.com
"""
import re
from bs4 import BeautifulSoup
from common.fetch import get_safe
from common.normalize import clean_text, parse_distance_km
from common.geocode import geocode_location
from common.model import Event, Race
from common.normalize import parse_date
from datetime import datetime
from typing import List, Tuple, Optional, Set

SOURCE = "racesmanager.com"
BASE_URL = "https://www.racesmanager.com"
RESULTS_URL = f"{BASE_URL}/Home/Results"

# Module-level cache for already scraped URLs
_CACHED_URLS: Set[str] = set()

def set_cached_urls(urls: Set[str]):
    """Set the URLs that have already been scraped (for caching)."""
    global _CACHED_URLS
    _CACHED_URLS = urls

def _mk_id(source: str, name: str, date_str: str) -> str:
    import hashlib
    s = f"{source}|{name}|{date_str}"
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def scrape() -> Tuple[List[Event], List[Race]]:
    events = []
    races = []
    print(f"Scraping {SOURCE}...")
    response = get_safe(RESULTS_URL)
    if not response:
        print(f"Failed to fetch {RESULTS_URL}")
        return events, races
    soup = BeautifulSoup(response.content, "lxml")
    # Find all event blocks
    for event_block in soup.find_all("a", href=re.compile(r"/Events/Details/")):
        event_name = clean_text(event_block.get_text(separator=" ", strip=True))
        event_url = BASE_URL + event_block["href"]
        # Try to find date and organizer in the text
        parent = event_block.parent
        date_str = None
        organizer = None
        race_links = []
        
        if parent:
            text = parent.get_text(separator=" ", strip=True)
            # Try to extract date (format: MM/DD/YYYY or DD/MM/YYYY)
            date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)
            if date_match:
                date_str = date_match.group(1)
            # Try to extract organizer
            org_match = re.search(r"Organizacija: ([^\d]+)", text)
            if org_match:
                organizer = clean_text(org_match.group(1))
            
            # Find all race result links under this event
            for sib in parent.find_all("a", href=re.compile(r"/Races/Results/")):
                race_name = clean_text(sib.get_text())
                race_url = BASE_URL + sib["href"]
                race_links.append((race_name, race_url))
        
        event_id = _mk_id(SOURCE, event_name, date_str or "")
        
        # Check if URL already scraped (caching)
        if event_url in _CACHED_URLS:
            continue
        
        # Geocode location if available
        latitude, longitude = None, None
        # Extract location from parent text if not already extracted
        if not location and parent:
            # Try to find location in text (usually between date and organizer)
            text = parent.get_text(separator=" ", strip=True)
            # Simple extraction - might need refinement based on actual HTML
            parts = text.split()
            for i, part in enumerate(parts):
                if part in ['Zagreb', 'Split', 'Rijeka', 'Osijek', 'Zadar', 'Pula', 'Dubrovnik']:
                    location = part
                    break
        
        if location:
            try:
                latitude, longitude = geocode_location(location, "Croatia")
            except:
                pass
        
        event_obj = Event(
            id=event_id,
            name=event_name,
            date=parse_date(date_str) if date_str else None,
            country="Croatia",
            region=None,
            location=location,
            latitude=latitude,
            longitude=longitude,
            organizer=organizer,
            contact_email=None,
            website=event_url,
            image_url=None,
            source=SOURCE,
            event_url=event_url,
            registration_opens=None,
            registration_closes=None,
            more_details=None,
            fee_rsd=None,
            fee_eur=None,
            description=None,
            runners_stats=None,
            participants=None
        )
        events.append(event_obj)
        for race_name, race_url in race_links:
            race_id = _mk_id(SOURCE, race_name, date_str or "")
            race = Race(
                id=race_id,
                event_id=event_id,
                name=race_name,
                distance_km=None,
                elevation_m=None,
                race_type=None,
                terrain=None,
                fee_eur=None,
                fee_rsd=None,
                cutoff=None,
                race_url=race_url,
                source=SOURCE,
                description=None,
                organizer=organizer,
                contact_email=None,
                participants=None
            )
            races.append(race)
    print(f"Scraped {len(events)} events and {len(races)} races from {SOURCE}")
    return events, races
