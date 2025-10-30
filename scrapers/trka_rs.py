"""Scraper for trka.rs (Serbian trail running calendar)."""

import hashlib
import json
import re
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup

from common.fetch import get_safe
from common.model import Race
from common.normalize import parse_date, parse_distance_km, parse_elev_m, clean_text


SOURCE = "trka.rs"
BASE_URL = "https://www.trka.rs"
LIST_URLS = [
    f"{BASE_URL}/events",        # Current/upcoming races
    f"{BASE_URL}/events/past",   # Past races
]

# Limit for testing (set to None to scrape all events)
# While developing/testing, keep this low to avoid overloading the server
MAX_EVENTS_PER_URL = 3  # TODO: Set to None for production scraping


def _mk_id(source: str, name: str, date_str: str) -> str:
    """
    Generate unique race ID from source, name, and date.

    Uses SHA1 hash of concatenated fields (first 16 hex chars).

    Args:
        source: Source domain (e.g., "trka.rs")
        name: Race name
        date_str: Date string representation

    Returns:
        Unique ID string (16 hex chars)
    """
    composite = f"{source}|{name}|{date_str}".lower()
    return hashlib.sha1(composite.encode("utf-8")).hexdigest()[:16]


def _extract_gps_coords(soup: BeautifulSoup) -> tuple[Optional[float], Optional[float]]:
    """
    Extract GPS coordinates from Leaflet map initialization data.

    Args:
        soup: BeautifulSoup object of event page

    Returns:
        Tuple of (latitude, longitude) or (None, None) if not found
    """
    # Look for script containing "initial-map-data"
    script_tag = soup.find('script', id='initial-map-data')
    if script_tag and script_tag.string:
        try:
            map_data = json.loads(script_tag.string)
            lat = map_data.get('latitude')
            lon = map_data.get('longitude')
            if lat is not None and lon is not None:
                return float(lat), float(lon)
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
    return None, None


def _normalize_race_type(race_type_sr: Optional[str]) -> Optional[str]:
    """
    Normalize Serbian race type to English standardized values.

    Args:
        race_type_sr: Serbian race type (e.g., "Трејл", "Полумаратон")

    Returns:
        Normalized English race type or original if not recognized
    """
    if not race_type_sr:
        return None

    # Mapping of Serbian to English race types
    type_mapping = {
        'трејл': 'Trail',
        'полумаратон': 'Half Marathon',
        'маратон': 'Marathon',
        'ултра': 'Ultra',
        'планинска трка': 'Mountain Race',
        'брдска трка': 'Hill Race',
        'крос': 'Cross Country',
        'улична трка': 'Road Race',
    }

    normalized = race_type_sr.lower().strip()
    return type_mapping.get(normalized, race_type_sr)


def _determine_terrain(race_type: Optional[str]) -> Optional[str]:
    """
    Determine terrain based on race type.

    Args:
        race_type: Normalized race type

    Returns:
        Terrain classification
    """
    if not race_type:
        return None

    race_type_lower = race_type.lower()

    if 'trail' in race_type_lower or 'mountain' in race_type_lower or 'hill' in race_type_lower:
        return 'Trail'
    elif 'road' in race_type_lower or 'marathon' in race_type_lower:
        return 'Road'
    elif 'cross country' in race_type_lower:
        return 'Mixed'

    return None


def _parse_serbian_datetime(date_str: str) -> Optional[datetime]:
    """
    Parse Serbian datetime format (DD.MM.YYYY. HH:MM).

    Args:
        date_str: Date string like "26.08.2025. 11:16" or "12.10.2025. 17:00"

    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None

    try:
        # Clean the string
        date_str = clean_text(date_str)
        # Try format with time: "26.08.2025. 11:16"
        return datetime.strptime(date_str, "%d.%m.%Y. %H:%M")
    except ValueError:
        try:
            # Try format without time: "26.08.2025."
            return datetime.strptime(date_str, "%d.%m.%Y.")
        except ValueError:
            return None


def _extract_fees_and_race_type_from_race_page(race_url: str) -> tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Extract fee and race type information from individual race page.

    Parses the fee table and returns the first (earliest/cheapest) fee tier.
    Also extracts race type if present on the race page.

    Args:
        race_url: URL to individual race page

    Returns:
        Tuple of (fee_rsd, fee_eur, race_type)
    """
    if not race_url:
        return None, None, None

    try:
        response = get_safe(race_url)
        if not response:
            return None, None, None

        soup = BeautifulSoup(response.content, "lxml")

        # Extract fee information
        fee_rsd = None
        fee_eur = None

        # Look for "Стартнина:" section - find the label first
        fee_label = soup.find('label', class_='col-form-label', string=lambda t: t and 'Стартнина:' in t)

        if fee_label:
            # Find the parent row and then the table
            parent_row = fee_label.find_parent('div', class_='row')
            if parent_row:
                # Find table within the next div with table-responsive class
                table_div = parent_row.find_next('div', class_='table-responsive')
                if table_div:
                    fee_table = table_div.find('table')
                    if fee_table:
                        # Find first data row in tbody
                        first_row = fee_table.select_one('tbody tr')
                        if first_row:
                            # Extract price from second column (Цена)
                            price_cells = first_row.select('td')
                            if len(price_cells) > 1:
                                price_cell = price_cells[1]
                                price_text = price_cell.get_text()

                                # Extract RSD amount (e.g., "2800 RSD")
                                rsd_match = re.search(r'(\d+)\s*RSD', price_text)
                                if rsd_match:
                                    fee_rsd = float(rsd_match.group(1))

                                # Extract EUR amount (e.g., "28 €")
                                eur_match = re.search(r'(\d+)\s*€', price_text)
                                if eur_match:
                                    fee_eur = float(eur_match.group(1))

        # Extract race type from race page (if present)
        race_type = None
        race_type_label = soup.find('label', class_='col-form-label', string=lambda t: t and 'Врста:' in t)
        if race_type_label:
            race_type_elem = race_type_label.find_next('p', class_='form-control-plaintext')
            if race_type_elem:
                race_type = clean_text(race_type_elem.get_text())

        return fee_rsd, fee_eur, race_type

    except Exception as e:
        print(f"  Error extracting data from {race_url}: {e}")
        return None, None, None


def scrape() -> List[Race]:
    """
    Scrape races from trka.rs (both current and past events).

    Returns:
        List of Race objects

    Note:
        This is a STUB implementation with placeholder selectors.
        Adjust selectors based on actual HTML structure of trka.rs.
    """
    races = []

    try:
        print(f"Scraping {SOURCE}...")

        # Scrape all configured URLs
        for url in LIST_URLS:
            print(f"  Fetching {url}...")
            response = get_safe(url)
            if not response:
                print(f"  Failed to fetch {url}")
                continue

            soup = BeautifulSoup(response.content, "lxml")

            # Real selectors based on actual HTML structure
            # Each event is in: .event-list-item > .event-list-item-main > .card.event-tile
            race_elements = soup.select(".event-list-item")

            if not race_elements:
                print(f"  No race elements found on {url}. Check selector: '.event-list-item'")
                # Continue to next URL instead of returning
                continue

            print(f"  Found {len(race_elements)} race elements")

            # Apply limit if set (for testing)
            if MAX_EVENTS_PER_URL:
                race_elements = race_elements[:MAX_EVENTS_PER_URL]
                print(f"  Limiting to {len(race_elements)} events (MAX_EVENTS_PER_URL={MAX_EVENTS_PER_URL})")

            for elem in race_elements:
                try:
                    # Extract basic info from list page
                    # Name: in .card-body h5.card-title
                    name_elem = elem.select_one(".card-title")
                    # Date: in .card-body .card-text small
                    date_elem = elem.select_one(".card-text small")
                    # Link to details: a.stretched-link
                    link_elem = elem.select_one("a.stretched-link")

                    name = clean_text(name_elem.get_text() if name_elem else None)
                    date_str = clean_text(date_elem.get_text() if date_elem else None)

                    # Get detail page URL
                    detail_url = None
                    if link_elem and link_elem.get("href"):
                        detail_url = link_elem["href"]
                        # Make absolute URL if relative
                        if detail_url and not detail_url.startswith("http"):
                            detail_url = BASE_URL + detail_url

                    # Location and distance not available on list page
                    location = None
                    distance_str = None

                    if not name:
                        continue  # Skip if no name

                    # Fetch detail page for complete race information
                    if detail_url:
                        print(f"    Fetching detail page: {detail_url}")
                        detail_races = _scrape_detail(detail_url, name, date_str or "")
                        if detail_races:
                            races.extend(detail_races)
                            print(f"    Found {len(detail_races)} race(s) in event '{name}'")
                        else:
                            print(f"    No races found in detail page for '{name}'")
                    else:
                        # No detail URL, create basic race entry
                        race_id = _mk_id(SOURCE, name, date_str or "")
                        race = Race(
                            id=race_id,
                            name=name,
                            date=parse_date(date_str),
                            country="Serbia",
                            region=None,
                            location=None,
                            latitude=None,
                            longitude=None,
                            distance_km=None,
                            elevation_m=None,
                            race_type=None,
                            terrain=None,
                            website=None,
                            registration_url=None,
                            contact_email=None,
                            registration_opens=None,
                            registration_closes=None,
                            fee_eur=None,
                            fee_rsd=None,
                            cutoff=None,
                            organizer=None,
                            source=SOURCE,
                            event_url=None,
                            race_url=None,
                        )
                        races.append(race)

                except Exception as e:
                    # Defensive: skip malformed entries
                    print(f"  Error parsing race element: {e}")
                    continue

        print(f"Successfully scraped {len(races)} races from {SOURCE}")

    except Exception as e:
        print(f"Error scraping {SOURCE}: {e}")

    return races


def _scrape_detail(url: str, event_name: str, event_date: str) -> List[Race]:
    """
    Scrape detail page for race information.

    One event can have multiple races (e.g., 27km, 18km, 10km variants).
    Returns one Race object per individual race.

    Args:
        url: Detail page URL
        event_name: Event name from list page
        event_date: Event date from list page

    Returns:
        List of Race objects (one per individual race in the event)
    """
    races = []

    try:
        response = get_safe(url)
        if not response:
            return races

        soup = BeautifulSoup(response.content, "lxml")

        # Extract common event details
        location = None
        organizer = None
        contact_email = None
        race_type = None
        registration_url = None
        latitude = None
        longitude = None
        registration_opens = None
        registration_closes = None

        # Find location: look for label "Локација:" and get next text
        location_row = soup.find('label', string=lambda t: t and 'Локација:' in t)
        if location_row:
            location_elem = location_row.find_next('p', class_='form-control-plaintext')
            if location_elem:
                location = clean_text(location_elem.get_text())

        # Find organizer: look for label "Организатор:" and preserve line breaks
        organizer_row = soup.find('label', string=lambda t: t and 'Организатор:' in t)
        if organizer_row:
            organizer_elem = organizer_row.find_next('p', class_='form-control-plaintext')
            if organizer_elem:
                # Get text with line breaks preserved
                organizer_parts = []
                for line in organizer_elem.stripped_strings:
                    organizer_parts.append(line)
                organizer = '\n'.join(organizer_parts) if organizer_parts else None

        # Find contact: look for label "Контакт:" and extract email
        contact_row = soup.find('label', string=lambda t: t and 'Контакт:' in t)
        if contact_row:
            contact_link = contact_row.find_next('a', href=lambda h: h and h.startswith('mailto:'))
            if contact_link:
                contact_email = contact_link.get_text().strip()

        # Find race type from event page: look for label "Врста:" and get text
        race_type_event = None
        race_type_row = soup.find('label', string=lambda t: t and 'Врста:' in t)
        if race_type_row:
            race_type_elem = race_type_row.find_next('p', class_='form-control-plaintext')
            if race_type_elem:
                race_type_event = clean_text(race_type_elem.get_text())

        # Find registration/more info URL: look for "Више детаља:" link
        details_row = soup.find('label', string=lambda t: t and 'Више детаља:' in t)
        if details_row:
            details_link = details_row.find_next('a')
            if details_link and details_link.get('href'):
                registration_url = details_link['href']

        # Extract GPS coordinates from map
        latitude, longitude = _extract_gps_coords(soup)

        # Extract registration dates: look for "Пријаве се отварају:" and "Крајњи рок за пријаву:"
        reg_opens_row = soup.find('label', string=lambda t: t and 'Пријаве се отварају:' in t)
        if reg_opens_row:
            reg_opens_elem = reg_opens_row.find_next('p', class_='form-control-plaintext')
            if reg_opens_elem:
                registration_opens = _parse_serbian_datetime(reg_opens_elem.get_text())

        reg_closes_row = soup.find('label', string=lambda t: t and 'Крајњи рок за пријаву:' in t)
        if reg_closes_row:
            reg_closes_elem = reg_closes_row.find_next('p', class_='form-control-plaintext')
            if reg_closes_elem:
                registration_closes = _parse_serbian_datetime(reg_closes_elem.get_text())

        # Extract individual races from the event
        race_list = soup.select('ul.list-group li.list-group-item a')

        if not race_list:
            # No individual races found, create single race with event data
            # Normalize race type and determine terrain
            normalized_race_type = _normalize_race_type(race_type_event)
            terrain = _determine_terrain(normalized_race_type)

            race_id = _mk_id(SOURCE, event_name, event_date)
            race = Race(
                id=race_id,
                name=event_name,
                date=parse_date(event_date),
                country="Serbia",
                region=None,
                location=location,
                latitude=latitude,
                longitude=longitude,
                distance_km=None,
                elevation_m=None,
                race_type=normalized_race_type,
                terrain=terrain,
                website=url,
                registration_url=registration_url,
                contact_email=contact_email,
                registration_opens=registration_opens,
                registration_closes=registration_closes,
                fee_eur=None,
                fee_rsd=None,
                cutoff=None,
                organizer=organizer,
                source=SOURCE,
                event_url=url,  # Parent event URL (same as main URL when no individual races)
                race_url=None,  # No individual race URL
            )
            races.append(race)
        else:
            # Create one Race object per individual race
            for race_link in race_list:
                race_text = clean_text(race_link.get_text())
                if not race_text:
                    continue

                # Parse distance from text like "[27.0 km] Red Race 27km"
                distance_km = None
                race_name = race_text

                # Extract distance from brackets
                distance_match = re.match(r'\[(\d+(?:\.\d+)?)\s*km\]\s*(.*)', race_text)
                if distance_match:
                    distance_km = float(distance_match.group(1))
                    race_name = distance_match.group(2).strip()

                # Extract individual race URL
                race_url = None
                if race_link.get('href'):
                    race_url = race_link['href']
                    if race_url and not race_url.startswith('http'):
                        race_url = BASE_URL + race_url

                # Extract fee and race type from individual race page
                fee_rsd = None
                fee_eur = None
                race_type_from_race_page = None
                if race_url:
                    print(f"      Extracting data from {race_url}")
                    fee_rsd, fee_eur, race_type_from_race_page = _extract_fees_and_race_type_from_race_page(race_url)

                # Determine final race type: race page overrides event page
                final_race_type = race_type_from_race_page if race_type_from_race_page else race_type_event

                # Normalize race type and determine terrain
                normalized_race_type = _normalize_race_type(final_race_type)
                terrain = _determine_terrain(normalized_race_type)

                # Generate unique ID for this specific race
                race_id = _mk_id(SOURCE, f"{event_name} - {race_name}", event_date)

                race = Race(
                    id=race_id,
                    name=f"{event_name} - {race_name}",
                    date=parse_date(event_date),
                    country="Serbia",
                    region=None,
                    location=location,
                    latitude=latitude,
                    longitude=longitude,
                    distance_km=distance_km,
                    elevation_m=None,
                    race_type=normalized_race_type,
                    terrain=terrain,
                    website=url,  # Keep website as event URL for now
                    registration_url=registration_url,
                    contact_email=contact_email,
                    registration_opens=registration_opens,
                    registration_closes=registration_closes,
                    fee_eur=fee_eur,
                    fee_rsd=fee_rsd,
                    cutoff=None,
                    organizer=organizer,
                    source=SOURCE,
                    event_url=url,  # Parent event URL
                    race_url=race_url,  # Individual race URL
                )
                races.append(race)

    except Exception as e:
        print(f"  Error scraping detail page {url}: {e}")

    return races
