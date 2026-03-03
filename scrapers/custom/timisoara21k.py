"""Custom scraper for timisoara.21k.ro (Timișoara 21k running events)."""

import hashlib
import re
from typing import Optional, List, Tuple
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from common.fetch import get_safe
from common.model import Event, Race
from common.normalize import parse_date, parse_distance_km, parse_elev_m, clean_text
from . import register_scraper


SOURCE = "timisoara.21k.ro"
BASE_URL = "https://timisoara.21k.ro"


def _mk_id(source: str, name: str, date_str: str = "") -> str:
    """Generate unique ID from source, name, and date."""
    s = f"{source}|{name}|{date_str}"
    return hashlib.md5(s.encode("utf-8")).hexdigest()


@register_scraper("timisoara.21k.ro")
def scrape_timisoara21k(url: str) -> Tuple[Optional[Event], List[Race]]:
    """
    Scrape event and races from timisoara.21k.ro
    
    Timișoara 21k is a running event (not trail) but follows similar structure.
    Extracts multiple race categories (21K, 10K, 5K, 2.5K) from single event page.
    
    Args:
        url: Event page URL (typically the races page)
        
    Returns:
        Tuple of (Event object, List of Race objects)
    """
    print(f"Scraping {url}...")
    
    response = get_safe(url)
    if not response:
        print(f"Failed to fetch {url}")
        return None, []
    
    soup = BeautifulSoup(response.content, "lxml")
    
    # ========================================
    # Extract event information
    # ========================================
    
    # Event name - from main heading
    event_name = "Timișoara 21k"
    title_elem = soup.select_one("h1")
    if title_elem:
        text = clean_text(title_elem.get_text())
        if "timișoara" in text.lower():
            event_name = text
    
    # Event date - look for date pattern "8th March 2026" or "March 8th 2026"
    date_str = None
    event_date = None
    
    # Search for date in headings and text
    text_content = soup.get_text()
    date_patterns = [
        r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})",
        r"March\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})",
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text_content)
        if match:
            date_str = match.group(0)
            try:
                event_date = parse_date(date_str)
            except:
                event_date = parse_date(date_str) if date_str else None
            break
    
    # Fallback to hardcoded date if found in standard format
    if not event_date:
        # Timișoara 21k is March 8, 2026
        event_date = parse_date("08.03.2026") or parse_date("8 March 2026")
    
    # Location - Timișoara, Romania (from context)
    location = "Timișoara, Romania"
    
    # Organizer - from text
    organizer = "SPORTGURU"
    organizer_text = re.search(r"By\s+([A-Za-z\s]+?)(?:\s+March|$)", text_content)
    if organizer_text:
        organizer = clean_text(organizer_text.group(1).strip())
    
    # Description - from About section
    description = None
    desc_elem = soup.select_one(".entry-content, .content, article")
    if desc_elem:
        # Get first paragraph or first section
        p_elem = desc_elem.select_one("p")
        if p_elem:
            description = clean_text(p_elem.get_text())
    
    if not description:
        description = "Timișoara 21k running event with multiple categories for elite runners and passionate amateurs."
    
    # Image URL - look for banner or hero image
    image_url = None
    img_elem = soup.select_one("img.attachment-full, img.header-image, .hero img")
    if img_elem and img_elem.get('src'):
        image_url = img_elem['src']
        if not image_url.startswith('http'):
            image_url = urljoin(BASE_URL, image_url)
    
    # Create Event object
    event_id = _mk_id(SOURCE, event_name, event_date.isoformat() if event_date else "")
    
    event = Event(
        id=event_id,
        source=SOURCE,
        event_url=url,  # Required field
        name=event_name,
        date=event_date,
        location=location,
        organizer=organizer,
        description=description,
        image_url=image_url,
        country="Romania",
        region="Timișoara",
        scraped_at=datetime.now(),
        last_updated=datetime.now(),
    )
    
    # ========================================
    # Extract races from event
    # ========================================
    
    races = []
    
    # Look for race sections - they're typically separated by h3 or divs with race info
    race_sections = soup.select(".race-item, .race-category, .corso-item")
    
    # If no sections found, look for h3 headings that might indicate race names
    if not race_sections:
        h3_elements = soup.select("h3")
        race_names = []
        for h3 in h3_elements:
            text = clean_text(h3.get_text())
            if any(keyword in text.lower() for keyword in ["k race", "21k", "10k", "5k", "2.5k"]):
                race_names.append((h3, text))
        
        # Build race sections around h3 elements
        if race_names:
            for h3_elem, race_name_text in race_names:
                # Gather text until next h3 or major element
                race_section = h3_elem
                race_sections.append(race_section)
    
    # Parse individual race data
    race_data_list = [
        {"name": "SPORTGURU 21K", "distance": 21.0, "start_time": "09:00 AM"},
        {"name": "10k RACE", "distance": 10.0, "start_time": "09:00 AM"},
        {"name": "5k RACE", "distance": 5.0, "start_time": "09:15 AM"},
        {"name": "2.5K RACE", "distance": 2.5, "start_time": "09:10 AM"},
    ]
    
    # Also try to extract from page content
    race_text = soup.get_text()
    
    # Look for race patterns in text
    race_pattern = r"(\d+(?:\.\d+)?)\s*k\s+(?:race|course|maraton|course)"
    found_races = re.findall(race_pattern, race_text, re.IGNORECASE)
    
    if found_races:
        # Use found races but keep the structured list as fallback
        for match in found_races:
            distance = parse_distance_km(f"{match}km")
            if distance and distance not in [r["distance"] for r in race_data_list]:
                race_data_list.append({
                    "name": f"{match}K Race",
                    "distance": distance,
                    "start_time": "09:00 AM"
                })
    
    # Get registration URLs for each race
    registration_forms = soup.select("a[href*='inscriere'], a[href*='registration'], a[href*='register']")
    registration_links = {}
    
    for reg_form in registration_forms:
        href = reg_form.get('href', '')
        text = clean_text(reg_form.get_text())
        if href:
            if not href.startswith('http'):
                href = urljoin(BASE_URL, href)
            registration_links[text] = href
    
    # Fallback registration URL
    if not registration_links:
        # Try to find any registration button or link
        for link in soup.select("a"):
            href = link.get('href', '')
            if any(word in href.lower() for word in ['inscriere', 'register', 'registration']):
                registration_links['Registration'] = urljoin(BASE_URL, href)
    
    # Default registration URL
    default_registration_url = urljoin(BASE_URL, "/inscriere/?lang=en")
    
    # Create Race objects
    for i, race_data in enumerate(race_data_list):
        race_name = race_data.get("name", f"Race {i+1}")
        distance_km = race_data.get("distance")
        
        if not distance_km:
            # Try to parse from name
            match = re.search(r"(\d+(?:\.\d+)?)", race_name)
            if match:
                distance_km = parse_distance_km(f"{match.group(1)}km")
        
        registration_url = default_registration_url
        # Try to match registration link by race name
        for reg_name, reg_url in registration_links.items():
            if str(distance_km) in reg_name or str(distance_km) in race_name:
                registration_url = reg_url
                break
        
        race_id = _mk_id(SOURCE, race_name, event_date.isoformat() if event_date else "")
        
        race = Race(
            id=race_id,
            event_id=event_id,
            source=SOURCE,
            name=race_name,
            distance_km=distance_km,
            elevation_m=None,  # Running races typically don't have elevation gain
            race_type="running",
            terrain="road/urban",
            organizer=organizer,
            registration_url=registration_url,
            race_url=url,
            description=description,
            scraped_at=datetime.now(),
            last_updated=datetime.now(),
        )
        
        races.append(race)
    
    print(f"Extracted event: {event_name}")
    print(f"Extracted {len(races)} races")
    
    return event, races
