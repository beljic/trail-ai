"""Custom scraper for ivanjicatrail.rs"""

import hashlib
import re
from typing import Optional, List, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from common.fetch import get_safe
from common.model import Event, Race
from common.normalize import parse_date, parse_distance_km, parse_elev_m, clean_text
from . import register_scraper


SOURCE = "ivanjicatrail.rs"


def _mk_id(source: str, name: str, date_str: str = "") -> str:
    """Generate unique ID from source, name, and date."""
    s = f"{source}|{name}|{date_str}"
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _extract_image_url(soup: BeautifulSoup) -> Optional[str]:
    """Extract image from page."""
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return clean_text(og_image.get("content"))
    
    main_img = soup.select_one('img.hero, .banner img, article img')
    if main_img and main_img.get('src'):
        return main_img.get('src')
    
    return None


def _extract_registration_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Extract registration URL."""
    reg_link = soup.find('a', string=re.compile(r'prijavi|register', re.I))
    if reg_link and reg_link.get('href'):
        href = reg_link.get('href')
        if href.startswith('http'):
            return href
        return base_url.rstrip('/') + '/' + href.lstrip('/')
    return None


def _extract_elevation_from_text(text: str) -> Optional[int]:
    """Extract elevation from text."""
    if not text:
        return None
    patterns = [r'D\+\s*(\d+)', r'(\d+)\s*m?\s*D\+', r'uspon[:\s]+(\d+)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


@register_scraper("ivanjicatrail.rs")
def scrape_ivanjicatrail(url: str) -> Tuple[Optional[Event], List[Race]]:
    """
    Scrape event and races from ivanjicatrail.rs
    
    Args:
        url: Event page URL
        
    Returns:
        Tuple of (Event object, List of Race objects)
    """
    print(f"Scraping {url}...")
    
    response = get_safe(url)
    if not response:
        print(f"Failed to fetch {url}")
        return None, []
    
    soup = BeautifulSoup(response.content, "lxml")
    
    # Extract event name from title or h1
    event_name = None
    title_elem = soup.find('h1') or soup.find('title')
    if title_elem:
        event_name = clean_text(title_elem.get_text())
    
    if not event_name:
        event_name = "Ivanjica Trail"  # Default fallback
    
    # Try to extract date
    date_str = None
    date_elem = soup.find(string=lambda t: t and any(month in str(t).lower() for month in ['januar', 'februar', 'mart', 'april', 'maj', 'jun', 'jul', 'avgust', 'septembar', 'oktobar', 'novembar', 'decembar']))
    if date_elem:
        date_str = clean_text(date_elem)
    
    # Extract location
    location = "Ivanjica"  # Default
    
    # Extract image and registration URL
    image_url = _extract_image_url(soup)
    registration_url = _extract_registration_url(soup, url)
    
    # Extract description
    description = None
    desc_meta = soup.find("meta", attrs={"name": "description"})
    if desc_meta and desc_meta.get("content"):
        description = clean_text(desc_meta.get("content"))
    
    # Try to find race distance information
    races = []
    
    # Look for distance indicators (e.g., "50km", "25km", "10km")
    distances = []
    all_text = " ".join(soup.stripped_strings)
    for text in soup.stripped_strings:
        # Look for patterns like "50 km", "50km", "25K"
        dist_matches = re.findall(r'(\d+)\s*k?m', text.lower())
        for match in dist_matches:
            try:
                km = int(match)
                if 5 <= km <= 200:  # Reasonable race distances
                    distances.append(km)
            except:
                pass
    
    # Deduplicate distances
    distances = sorted(set(distances), reverse=True)
    
    # Generate Event object
    event_id = _mk_id(SOURCE, event_name, date_str or "")
    event = Event(
        id=event_id,
        name=event_name,
        date=parse_date(date_str) if date_str else None,
        country="Serbia",
        region="Moravički okrug",
        location=location,
        latitude=None,
        longitude=None,
        organizer=None,
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
        participants=None,
        scraped_at=datetime.now(),
        last_updated=datetime.now(),
        last_check=datetime.now()
    )
    
    # Create Race objects for each distance found
    if distances:
        for dist in distances:
            race_name = f"{event_name} {dist}km"
            race_id = _mk_id(SOURCE, race_name, date_str or "")
            elevation = _extract_elevation_from_text(all_text)
            race = Race(
                id=race_id,
                event_id=event_id,
                name=race_name,
                distance_km=float(dist),
                elevation_m=elevation,
                race_type="trail",
                terrain="trail",
                registration_url=registration_url,
                fee_eur=None,
                fee_rsd=None,
                cutoff=None,
                race_url=url,
                source=SOURCE,
                description=None,
                organizer=None,
                contact_email=None,
                participants=None,
                scraped_at=datetime.now(),
                last_updated=datetime.now()
            )
            races.append(race)
    else:
        # Create a single generic race if no distances found
        race_id = _mk_id(SOURCE, event_name, date_str or "")
        race = Race(
            id=race_id,
            event_id=event_id,
            name=event_name,
            distance_km=None,
            elevation_m=_extract_elevation_from_text(all_text),
            race_type="trail",
            terrain="trail",
            registration_url=registration_url,
            fee_eur=None,
            fee_rsd=None,
            cutoff=None,
            race_url=url,
            source=SOURCE,
            description=None,
            organizer=None,
            contact_email=None,
            participants=None,
            scraped_at=datetime.now(),
            last_updated=datetime.now()
        )
        races.append(race)
    
    print(f"Extracted: 1 event, {len(races)} race(s)")
    return event, races
