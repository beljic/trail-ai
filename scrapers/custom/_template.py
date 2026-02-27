"""
Template for creating custom site-specific scrapers.

Copy this file to scrapers/custom/<domain>.py and customize the selectors
and extraction logic for your target site.

Example:
    cp scrapers/custom/_template.py scrapers/custom/mysite_com.py
    # Edit mysite_com.py and update:
    # - SOURCE
    # - register_scraper domain
    # - scrape_* function logic
"""

import hashlib
from typing import Optional, List, Tuple
from bs4 import BeautifulSoup
from common.fetch import get_safe, get_selenium_safe
from common.model import Event, Race
from common.normalize import parse_date, parse_distance_km, parse_elev_m, clean_text
from . import register_scraper


# CHANGE THIS: Set your source domain
SOURCE = "example.com"


def _mk_id(source: str, name: str, date_str: str = "") -> str:
    """Generate unique ID from source, name, and date."""
    s = f"{source}|{name}|{date_str}"
    return hashlib.md5(s.encode("utf-8")).hexdigest()


# CHANGE THIS: Update domain pattern to match your site
@register_scraper("example.com")
def scrape_example(url: str) -> Tuple[Optional[Event], List[Race]]:
    """
    Scrape event and races from example.com
    
    Args:
        url: Event page URL
        
    Returns:
        Tuple of (Event object, List of Race objects)
    """
    print(f"Scraping {url}...")
    
    # Use get_safe for regular pages, get_selenium_safe for JS-rendered pages
    response = get_safe(url)
    # html = get_selenium_safe(url)  # Use this for JS-heavy sites
    
    if not response:
        print(f"Failed to fetch {url}")
        return None, []
    
    soup = BeautifulSoup(response.content, "lxml")
    
    # ========================================
    # CUSTOMIZE: Extract event information
    # ========================================
    
    # Event name - adjust selector
    event_name = None
    title_elem = soup.select_one("h1.event-title")  # CHANGE THIS
    if title_elem:
        event_name = clean_text(title_elem.get_text())
    
    if not event_name:
        event_name = "Event Name"  # Fallback
    
    # Event date - adjust selector
    date_str = None
    date_elem = soup.select_one(".event-date")  # CHANGE THIS
    if date_elem:
        date_str = clean_text(date_elem.get_text())
    
    # Location - adjust selector
    location = None
    location_elem = soup.select_one(".event-location")  # CHANGE THIS
    if location_elem:
        location = clean_text(location_elem.get_text())
    
    # Organizer - adjust selector
    organizer = None
    organizer_elem = soup.select_one(".organizer-name")  # CHANGE THIS
    if organizer_elem:
        organizer = clean_text(organizer_elem.get_text())
    
    # Description - adjust selector
    description = None
    desc_elem = soup.select_one(".event-description")  # CHANGE THIS
    if desc_elem:
        description = clean_text(desc_elem.get_text())
    
    # Image URL - adjust selector
    image_url = None
    img_elem = soup.select_one("img.event-image")  # CHANGE THIS
    if img_elem and img_elem.get('src'):
        image_url = img_elem['src']
        if not image_url.startswith('http'):
            from urllib.parse import urljoin
            image_url = urljoin(url, image_url)
    
    # ========================================
    # CUSTOMIZE: Extract race information
    # ========================================
    
    races = []
    
    # Option 1: Find race cards/blocks
    race_elements = soup.select(".race-card")  # CHANGE THIS
    for elem in race_elements:
        race_name_elem = elem.select_one(".race-name")  # CHANGE THIS
        distance_elem = elem.select_one(".race-distance")  # CHANGE THIS
        
        if not race_name_elem:
            continue
        
        race_name = clean_text(race_name_elem.get_text())
        distance_str = clean_text(distance_elem.get_text()) if distance_elem else None
        distance_km = parse_distance_km(distance_str) if distance_str else None
        
        race_id = _mk_id(SOURCE, race_name, date_str or "")
        race = Race(
            id=race_id,
            event_id=_mk_id(SOURCE, event_name, date_str or ""),
            name=race_name,
            distance_km=distance_km,
            elevation_m=None,
            race_type="trail",  # Adjust as needed
            terrain="trail",  # Adjust as needed
            fee_eur=None,
            fee_rsd=None,
            cutoff=None,
            race_url=url,
            source=SOURCE,
            description=None,
            organizer=organizer,
            contact_email=None,
            participants=None
        )
        races.append(race)
    
    # Option 2: Auto-detect distances from text (fallback)
    if not races:
        import re
        distances = []
        for text in soup.stripped_strings:
            dist_matches = re.findall(r'(\d+)\s*k?m', text.lower())
            for match in dist_matches:
                try:
                    km = int(match)
                    if 5 <= km <= 200:
                        distances.append(km)
                except:
                    pass
        
        distances = sorted(set(distances), reverse=True)
        
        for dist in distances:
            race_name = f"{event_name} {dist}km"
            race_id = _mk_id(SOURCE, race_name, date_str or "")
            race = Race(
                id=race_id,
                event_id=_mk_id(SOURCE, event_name, date_str or ""),
                name=race_name,
                distance_km=float(dist),
                elevation_m=None,
                race_type="trail",
                terrain="trail",
                fee_eur=None,
                fee_rsd=None,
                cutoff=None,
                race_url=url,
                source=SOURCE,
                description=None,
                organizer=organizer,
                contact_email=None,
                participants=None
            )
            races.append(race)
    
    # ========================================
    # Create Event object
    # ========================================
    
    event_id = _mk_id(SOURCE, event_name, date_str or "")
    event = Event(
        id=event_id,
        name=event_name,
        date=parse_date(date_str) if date_str else None,
        country="Serbia",  # CHANGE THIS
        region=None,
        location=location,
        latitude=None,
        longitude=None,
        organizer=organizer,
        contact_email=None,
        website=url,
        image_url=image_url,
        source=SOURCE,
        event_url=url,
        registration_opens=None,
        registration_closes=None,
        more_details=None,
        fee_rsd=None,
        fee_eur=None,
        description=description,
        runners_stats=None,
        participants=None
    )
    
    print(f"Extracted: 1 event, {len(races)} race(s)")
    return event, races
