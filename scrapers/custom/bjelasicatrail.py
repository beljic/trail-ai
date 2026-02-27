"""Custom scraper for bjelasicatrail.me"""

import hashlib
import re
from typing import Optional, List, Tuple
from urllib.parse import urljoin
from datetime import datetime

from bs4 import BeautifulSoup
from common.fetch import get_safe
from common.model import Event, Race
from common.normalize import parse_date, parse_distance_km, parse_elev_m, clean_text
from . import register_scraper


SOURCE = "bjelasicatrail.me"


def _mk_id(source: str, name: str, date_str: str = "") -> str:
    """Generate unique ID from source, name, and date."""
    s = f"{source}|{name}|{date_str}"
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _extract_date(text: str) -> Optional[str]:
    if not text:
        return None

    # Prefer full dates if present (e.g., 15.06.2026)
    match = re.search(r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})", text)
    if match:
        return match.group(1).replace(" ", "")

    return None


def _extract_image_url(soup: BeautifulSoup) -> Optional[str]:
    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        return clean_text(og_image.get("content"))

    tw_image = soup.find("meta", attrs={"name": "twitter:image"})
    if tw_image and tw_image.get("content"):
        return clean_text(tw_image.get("content"))
    
    # Try main content image
    main_img = soup.select_one('img.hero-image, .main-image img, article img')
    if main_img and main_img.get('src'):
        return main_img.get('src')

    return None


def _extract_registration_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    # Look for registration links
    reg_link = soup.find('a', string=re.compile(r'prijavi|register|registruj se', re.I))
    if reg_link and reg_link.get('href'):
        href = reg_link.get('href')
        if href.startswith('http'):
            return href
        return urljoin(base_url, href)
    return None


def _extract_elevation_from_text(text: str) -> Optional[int]:
    if not text:
        return None
    patterns = [
        r'D\+\s*(\d+)',
        r'(\d+)\s*m?\s*D\+',
        r'elevation[:\s]+(\d+)',
        r'uspon[:\s]+(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


@register_scraper("bjelasicatrail.me")
def scrape_bjelasicatrail(url: str) -> Tuple[Optional[Event], List[Race]]:
    """
    Scrape event and races from bjelasicatrail.me

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
        event_name = "Bjelasica Trail"

    # Date (if any)
    text_all = " ".join(soup.stripped_strings)
    date_str = _extract_date(text_all)

    # Location defaults
    location = "Kolašin"

    # Contact email
    contact_email = None
    mailto = soup.select_one("a[href^='mailto:']")
    if mailto and mailto.get("href"):
        contact_email = clean_text(mailto.get("href").replace("mailto:", ""))

    # Description
    description = None
    desc_meta = soup.find("meta", attrs={"name": "description"})
    if desc_meta and desc_meta.get("content"):
        description = clean_text(desc_meta.get("content"))

    image_url = _extract_image_url(soup)
    registration_url = _extract_registration_url(soup, url)

    event_id = _mk_id(SOURCE, event_name, date_str or "")
    event = Event(
        id=event_id,
        name=event_name,
        date=parse_date(date_str) if date_str else None,
        country="Montenegro",
        region=None,
        location=location,
        latitude=None,
        longitude=None,
        organizer=None,
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

    # Find race links like "/62k-red-trail/"
    race_links = []
    for link in soup.select("a[href]"):
        href = link.get("href")
        text = clean_text(link.get_text())
        if not href or not text:
            continue
        if re.search(r"/\d+\s*k", href) or re.search(r"\d+\s*k", text.lower()):
            race_links.append((text, urljoin(url, href)))

    # Build races from links
    seen_distances = set()
    for race_text, race_url in race_links:
        distance = parse_distance_km(race_text)
        if distance:
            if distance in seen_distances:
                continue
            seen_distances.add(distance)
        race_name = race_text or (f"{event_name} {distance}km" if distance else event_name)
        # Try to extract elevation from race text
        elevation = _extract_elevation_from_text(race_text) if race_text else None
        race_id = _mk_id(SOURCE, race_name, date_str or "")
        race = Race(
            id=race_id,
            event_id=event_id,
            name=race_name,
            distance_km=distance,
            elevation_m=elevation,
            race_type="trail",
            terrain="trail",
            registration_url=registration_url,
            fee_eur=None,
            fee_rsd=None,
            cutoff=None,
            race_url=race_url,
            source=SOURCE,
            description=None,
            organizer=None,
            contact_email=contact_email,
            participants=None,
            scraped_at=datetime.now(),
            last_updated=datetime.now()
        )
        races.append(race)

    # Fallback: parse distances from page text
    if not races:
        distances = []
        for match in re.findall(r"(\d+(?:\.\d+)?)\s*k(?:m)?", text_all.lower()):
            try:
                km = float(match)
                if 5 <= km <= 200:
                    distances.append(km)
            except ValueError:
                continue
        for km in sorted(set(distances), reverse=True):
            race_name = f"{event_name} {km}km"
            race_id = _mk_id(SOURCE, race_name, date_str or "")
            race = Race(
                id=race_id,
                event_id=event_id,
                name=race_name,
                distance_km=km,
                elevation_m=_extract_elevation_from_text(text_all),
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
                contact_email=contact_email,
                participants=None,
                scraped_at=datetime.now(),
                last_updated=datetime.now()
            )
            races.append(race)

    print(f"Extracted: 1 event, {len(races)} race(s)")
    return event, races
