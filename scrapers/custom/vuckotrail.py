"""Custom scraper for visitbjelasnica.com (Vučko Trail)."""

import hashlib
import re
from typing import Optional, List, Tuple
from datetime import datetime

from bs4 import BeautifulSoup
from common.fetch import get_safe
from common.model import Event, Race
from common.normalize import parse_date, parse_distance_km, parse_elev_m, clean_text
from . import register_scraper


SOURCE = "visitbjelasnica.com"


def _mk_id(source: str, name: str, date_str: str = "") -> str:
    """Generate unique ID from source, name, and date."""
    s = f"{source}|{name}|{date_str}"
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _extract_date(text: str) -> Optional[str]:
    if not text:
        return None

    # Full date like 15.06.2025
    match = re.search(r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})", text)
    if match:
        return match.group(1).replace(" ", "")

    # Date range like "13. – 15.06.2025"
    range_match = re.search(r"(\d{1,2})\.\s*[–-]\s*(\d{1,2}\.\s*\d{2}\.\s*\d{4})", text)
    if range_match:
        start_day = range_match.group(1)
        end_part = range_match.group(2).replace(" ", "")
        parts = end_part.split(".")
        if len(parts) >= 3:
            return f"{start_day}.{parts[1]}.{parts[2]}"

    return None


def _extract_line_value(text: str, label: str) -> Optional[str]:
    if not text:
        return None
    pattern = rf"{re.escape(label)}\s*:\s*([^\n]+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match:
        return clean_text(match.group(1))
    return None


def _extract_races(text: str) -> List[dict]:
    races = []
    if not text:
        return races

    pattern = r"([A-ZČĆŽŠĐ]+)\s*staza.{0,120}?(\d+(?:\.\d+)?)\s*km.{0,80}?\+\s*(\d+)\s*m"
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        color = clean_text(match.group(1))
        distance = parse_distance_km(match.group(2) + "km")
        elevation = parse_elev_m(match.group(3) + "m")
        if distance:
            races.append({
                "name": f"{color.capitalize()} staza",
                "distance_km": distance,
                "elevation_m": elevation,
            })

    # Fallback: find distances without elevation
    if not races:
        distances = []
        for match in re.findall(r"(\d+(?:\.\d+)?)\s*k(?:m)?", text.lower()):
            try:
                km = float(match)
                if 5 <= km <= 200:
                    distances.append(km)
            except ValueError:
                continue
        for km in sorted(set(distances), reverse=True):
            races.append({
                "name": f"{km}km",
                "distance_km": km,
                "elevation_m": None,
            })

    return races


def _extract_image_url(soup: BeautifulSoup) -> Optional[str]:
    """Extract image from page."""
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return clean_text(og_image.get("content"))
    
    main_img = soup.select_one('img.featured, .hero-image img, article img')
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


@register_scraper("visitbjelasnica.com")
@register_scraper("vuckotrail.ba")
def scrape_vuckotrail(url: str) -> Tuple[Optional[Event], List[Race]]:
    """
    Scrape event and races from visitbjelasnica.com (Vučko Trail page)

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

    # Event name
    event_name = None
    title_elem = soup.find("h1") or soup.find("title")
    if title_elem:
        event_name = clean_text(title_elem.get_text())

    if not event_name:
        event_name = "Vučko Trail"

    text_all = "\n".join(soup.stripped_strings)

    # Date and location
    date_str = _extract_date(text_all)
    location = _extract_line_value(text_all, "Lokacija")

    # Organizer and contact
    organizer = _extract_line_value(text_all, "Organizator")
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", text_all)
    contact_email = email_match.group(0) if email_match else None

    # Description
    description = None
    desc_meta = soup.find("meta", attrs={"name": "description"})
    if desc_meta and desc_meta.get("content"):
        description = clean_text(desc_meta.get("content"))
    
    # Extract image and registration URL
    image_url = _extract_image_url(soup)
    registration_url = _extract_registration_url(soup, url)

    event_id = _mk_id(SOURCE, event_name, date_str or "")
    event = Event(
        id=event_id,
        name=event_name,
        date=parse_date(date_str) if date_str else None,
        country="Bosnia and Herzegovina",
        region=None,
        location=location,
        latitude=None,
        longitude=None,
        organizer=organizer,
        contact_email=contact_email,
        website=url,
        image_url=image_url,
        source=SOURCE,
        event_url=url,
        description=description,
        registration_opens=None,
        registration_closes=None,
        more_details=None,
        fee_rsd=None,
        fee_eur=None,
        runners_stats=None,
        participants=None,
        scraped_at=datetime.now(),
        last_updated=datetime.now(),
        last_check=datetime.now()
    )

    races: List[Race] = []
    race_defs = _extract_races(" ".join(soup.stripped_strings))

    for race_def in race_defs:
        race_name = f"{event_name} {race_def['name']}" if race_def.get("name") else event_name
        race_id = _mk_id(SOURCE, race_name, date_str or "")
        race = Race(
            id=race_id,
            event_id=event_id,
            name=race_name,
            distance_km=race_def.get("distance_km"),
            elevation_m=race_def.get("elevation_m"),
            race_type="trail",
            terrain="trail",
            registration_url=registration_url,
            fee_eur=None,
            fee_rsd=None,
            cutoff=None,
            race_url=url,
            source=SOURCE,
            description=None,
            organizer=organizer,
            contact_email=contact_email,
            participants=None,
            scraped_at=datetime.now(),
            last_updated=datetime.now()
        )
        races.append(race)

    print(f"Extracted: 1 event, {len(races)} race(s)")
    return event, races
