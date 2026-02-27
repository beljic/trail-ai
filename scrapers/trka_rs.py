def _determine_terrain(race_type):
    """Detect terrain type from race_type string."""
    if not race_type:
        return None
    t = race_type.lower()
    if 'trail' in t or 'ultra' in t:
        return 'trail'
    if 'road' in t or 'ulica' in t:
        return 'road'
    if 'mountain' in t or 'planina' in t or 'skyrace' in t:
        return 'mountain'
    if 'cross' in t or 'kros' in t:
        return 'cross'
    if 'vertical' in t or 'vertikal' in t:
        return 'vertical'
    return None


def _extract_image_url(soup):
    """Extract event image URL from page (og:image or main image)."""
    # Try og:image meta tag first
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        return og_image.get('content')
    
    # Try twitter:image
    twitter_image = soup.find('meta', property='twitter:image')
    if twitter_image and twitter_image.get('content'):
        return twitter_image.get('content')
    
    # Try main content image
    content_img = soup.select_one('.content-panel img, .event-detail img, img.event-image')
    if content_img and content_img.get('src'):
        src = content_img.get('src')
        if not src.startswith('http'):
            src = BASE_URL + src
        return src
    
    return None


def _extract_registration_url(soup, event_url):
    """Extract registration URL from event page."""
    # Look for "Prijavi se" or "Register" button/link
    reg_link = soup.find('a', string=re.compile(r'Prijavi se|Register|Sign up', re.I))
    if reg_link and reg_link.get('href'):
        href = reg_link.get('href')
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            return BASE_URL + href
    
    # Try common registration URL patterns
    reg_patterns = ['/register', '/registration', '/prijava']
    for pattern in reg_patterns:
        if event_url:
            potential_url = event_url.rstrip('/') + pattern
            # We could check if it exists, but for now just construct it
            # Only return if we find the link on page
            pass
    
    # Look in actions panel
    actions = soup.select('.content-panel a, .actions a')
    for action in actions:
        href = action.get('href', '')
        text = action.get_text().lower()
        if 'register' in text or 'prijav' in text:
            if href.startswith('http'):
                return href
            elif href.startswith('/'):
                return BASE_URL + href
    
    return None


def _extract_elevation_from_text(text):
    """Extract elevation (D+) from text description."""
    if not text:
        return None
    
    # Common patterns: "D+ 1500", "1500m D+", "elevation: 1500m", etc.
    patterns = [
        r'D\+\s*(\d+)',
        r'(\d+)\s*m?\s*D\+',
        r'elevation[:\s]+(\d+)',
        r'elevacija[:\s]+(\d+)',
        r'uspon[:\s]+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None
from common.normalize import parse_distance_km, parse_elev_m
from common.normalize import clean_text
from common.geocode import geocode_location
from bs4 import BeautifulSoup
from common.fetch import get_safe
import re
SOURCE = "trka.rs"
BASE_URL = "https://trka.rs"
LIST_URLS = [f"{BASE_URL}/events"]
from typing import Optional
from common.model import Event, Race
from common.normalize import parse_date
from typing import List, Tuple, Set
from common.geocode import geocode_location

# Module-level cache for already scraped URLs
_CACHED_URLS: Set[str] = set()

def set_cached_urls(urls: Set[str]):
    """Set the URLs that have already been scraped (for caching)."""
    global _CACHED_URLS
    _CACHED_URLS = urls

def _extract_gps_coords(soup):
    return None, None
def _mk_id(source: str, name: str, date_str: str) -> str:
    import hashlib
    s = f"{source}|{name}|{date_str}"
    return hashlib.md5(s.encode("utf-8")).hexdigest()
MAX_EVENTS_PER_URL = None


from datetime import datetime

# Robust parser for event registration datetime fields
def parse_event_datetime(dt_str):
    if not dt_str:
        return None
    dt_str = dt_str.strip()
    # Try common formats
    fmts = [
        "%d/%m/%Y %I:%M %p",   # 01/02/2025 12:05 PM
        "%d/%m/%Y %I %p",      # 01/02/2025 5 PM
        "%d/%m/%Y %H:%M",     # 01/02/2025 17:05
        "%d/%m/%Y %H:%M %p",  # 01/02/2025 5:05 PM
        "%d/%m/%Y %H %p",     # 01/02/2025 5 PM
        "%d/%m/%Y %H:%M %p.", # 01/02/2025 5:05 p.m.
        "%d/%m/%Y %I:%M %p.", # 01/02/2025 12:05 p.m.
        "%d/%m/%Y %I %p.",    # 01/02/2025 5 p.m.
        "%d/%m/%Y %p",        # 01/02/2025 PM
        "%d/%m/%Y %H:%M",     # 01/02/2025 17:05
        "%d/%m/%Y",           # 01/02/2025
    ]
    # Normalize AM/PM
    dt_str = dt_str.replace('a.m.', 'AM').replace('p.m.', 'PM').replace('noon', '12:00 PM').replace('midnight', '12:00 AM')
    for fmt in fmts:
        try:
            return datetime.strptime(dt_str, fmt)
        except Exception:
            continue
    return None


def _extract_fee_and_type(race_url):
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


def scrape() -> Tuple[List[Event], List[Race]]:
    events = []
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
                        # Check if URL already scraped (caching)
                        if detail_url in _CACHED_URLS:
                            print(f"    Skipping already scraped: {detail_url}")
                            continue
                        
                        print(f"    Fetching detail page: {detail_url}")
                        event_obj, detail_races = _scrape_detail(detail_url, name, date_str or "")
                        if event_obj and detail_races:
                            events.append(event_obj)
                            races.extend(detail_races)
                            print(f"    Found {len(detail_races)} race(s) in event '{name}'")
                        else:
                            print(f"    No races found in detail page for '{name}'")

                except Exception as e:
                    # Defensive: skip malformed entries
                    print(f"  Error parsing race element: {e}")
                    continue

        print(f"Successfully scraped {len(events)} events with {len(races)} races from {SOURCE}")

    except Exception as e:
        print(f"Error scraping {SOURCE}: {e}")

    return events, races


def _scrape_detail(url: str, event_name: str, event_date: str) -> Tuple[Optional[Event], List[Race]]:
    from common.model import Event, Race
    event_id = _mk_id(SOURCE, event_name, event_date)
    response = get_safe(url)
    if not response:
        print(f"[trka_rs] No response for URL: {url}")
        return None, []
    soup = BeautifulSoup(response.content, "lxml")

    def get_event_field(label):
        # Find the row with the label
        for div in soup.select('div.row'):
            label_elem = div.find('label', class_='col-form-label')
            if label_elem and label in label_elem.get_text():
                val_elem = div.find('p', class_='form-control-plaintext')
                if val_elem:
                    return clean_text(val_elem.get_text(separator=' ', strip=True))
                val2_elem = div.find('div', class_='form-control-plaintext')
                if val2_elem:
                    return clean_text(val2_elem.get_text(separator=' ', strip=True))
        return None

    location = get_event_field('Location:') or get_event_field('Локација:')
    organizer = get_event_field('Organizer:')
    # Contact email
    contact_email = None
    for div in soup.select('div.row'):
        label_elem = div.find('label', class_='col-form-label')
        if label_elem and 'Contact:' in label_elem.get_text():
            mailto = div.find('a', href=lambda h: h and h.startswith('mailto:'))
            if mailto:
                contact_email = mailto.get('href').replace('mailto:', '').strip()
    registration_opens = get_event_field('Registrations open on:') or get_event_field('Почетак пријава:')
    registration_closes = get_event_field('Registrations deadline:') or get_event_field('Крај пријава:')
    registration_opens_dt = parse_event_datetime(registration_opens)
    registration_closes_dt = parse_event_datetime(registration_closes)
    # More details
    more_details = None
    for div in soup.select('div.row'):
        label_elem = div.find('label', class_='col-form-label')
        if label_elem and 'More details:' in label_elem.get_text():
            link = div.find('a')
            if link and link.get('href'):
                more_details = link.get('href')

    # Latitude/Longitude
    latitude, longitude = _extract_gps_coords(soup)
    
    # If GPS coords not found on page, try geocoding from location
    if not latitude and not longitude and location:
        try:
            latitude, longitude = geocode_location(location, "Serbia")
            if latitude and longitude:
                print(f"    Geocoded '{location}' -> ({latitude}, {longitude})")
        except Exception as e:
            print(f"    Geocoding failed for '{location}': {e}")
    
    # Extract image URL
    image_url = _extract_image_url(soup)
    if image_url:
        print(f"    Found image: {image_url}")
    
    # Extract registration URL
    registration_url = _extract_registration_url(soup, url)

    # Entry fee parsing
    fee_rsd = None
    fee_eur = None
    entry_fee_label = soup.find('label', string=lambda t: t and ('Entry fee:' in t or 'Стартнина:' in t))
    if entry_fee_label:
        parent_row = entry_fee_label.find_parent('div', class_='row')
        if parent_row:
            table_div = parent_row.find_next('div', class_='table-responsive')
            if table_div:
                fee_table = table_div.find('table')
                if fee_table:
                    first_row = fee_table.select_one('tbody tr')
                    if first_row:
                        price_cells = first_row.select('td')
                        if len(price_cells) > 1:
                            price_text = price_cells[1].get_text()
                            rsd_match = re.search(r'(\d+)\s*RSD', price_text)
                            if rsd_match:
                                fee_rsd = float(rsd_match.group(1))
                            eur_match = re.search(r'(\d+)\s*€', price_text)
                            if eur_match:
                                fee_eur = float(eur_match.group(1))

    # Event description
    event_description = None
    desc_row = soup.find('label', string=lambda t: t and ('Description:' in t or 'Опис:' in t))
    if desc_row:
        val = desc_row.find_next('p', class_='form-control-plaintext')
        if val:
            event_description = clean_text(val.get_text(separator=' ', strip=True))

    # Runners statistics parsing (per event and per race)
    runners_stats = None
    participants = {}
    runners_soup = None
    try:
        # Find the runners link in the Actions panel
        runners_url = None
        actions_panel = soup.find('div', class_='content-panel')
        if actions_panel:
            runners_link = actions_panel.find('a', href=re.compile(r'/events/\d+/runners/'))
            if runners_link:
                href = runners_link.get('href')
                if href.startswith('/'):
                    runners_url = BASE_URL + href
                else:
                    runners_url = href
        # --- Participants extraction: use only event-level runners page ---
        if runners_url:
            runners_resp = get_safe(runners_url)
            if runners_resp:
                runners_soup = BeautifulSoup(runners_resp.content, "lxml")
                filter_select = runners_soup.find('select', {'name': 'filter-by'})
                if filter_select:
                    # Per-race participants from filter select
                    for opt in filter_select.find_all('option'):
                        value = opt.get('value')
                        text = clean_text(opt.get_text())
                        if value and value.startswith('/races/'):
                            # Try to extract count for this race from the table below (after selecting option)
                            # But since we can't simulate the select, fallback to counting rows in the table as-is
                            table = runners_soup.find('table', class_='table')
                            reg_count = None
                            if table:
                                tbody = table.find('tbody')
                                if tbody:
                                    reg_count = len(tbody.find_all('tr'))
                            race_name = text
                            if race_name.lower().startswith('race - '):
                                race_name = race_name[7:].strip()
                            print(f"[trka_rs] Found participants (select): {race_name} -> {reg_count}")
                            if reg_count is not None:
                                participants[race_name] = reg_count
                else:
                    # No filter select: fallback to total count for all races
                    table = runners_soup.find('table', class_='table')
                    reg_count = None
                    if table:
                        tbody = table.find('tbody')
                        if tbody:
                            reg_count = len(tbody.find_all('tr'))
                    print(f"[trka_rs] Fallback: assign total participants {reg_count} to all races")
                    for a in soup.select('ul.list-group li.list-group-item a'):
                        race_name = clean_text(a.get_text())
                        if reg_count is not None:
                            participants[race_name] = reg_count
                print(f"[trka_rs] Final participants dict: {participants}")
        # If no runners_url or runners_resp, skip participants extraction for this event
        # --- Event-level stats (total, paid, unpaid, by_city, by_country) ---
        total = None
        paid = None
        unpaid = None
        by_city = {}
        by_country = {}
        if runners_soup:
            total_tag = runners_soup.find(string=re.compile(r"Total registered:|Укупно пријављених:"))
            if total_tag:
                total_match = re.search(r"(\d+)", total_tag)
                if total_match:
                    total = int(total_match.group(1))
            paid_tag = runners_soup.find(string=re.compile(r"Paid:|Плаћено:"))
            if paid_tag:
                paid_match = re.search(r"(\d+)", paid_tag)
                if paid_match:
                    paid = int(paid_match.group(1))
            unpaid_tag = runners_soup.find(string=re.compile(r"Unpaid:|Није плаћено:"))
            if unpaid_tag:
                unpaid_match = re.search(r"(\d+)", unpaid_tag)
                if unpaid_match:
                    unpaid = int(unpaid_match.group(1))
            city_table = runners_soup.find('table', id='by-city')
            if city_table:
                for row in city_table.select('tbody tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        city = clean_text(cells[0].get_text())
                        count = int(cells[1].get_text())
                        by_city[city] = count
            country_table = runners_soup.find('table', id='by-country')
            if country_table:
                for row in country_table.select('tbody tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        country = clean_text(cells[0].get_text())
                        count = int(cells[1].get_text())
                        by_country[country] = count
        runners_stats = {
            "total": total,
            "paid": paid,
            "unpaid": unpaid,
            "by_city": by_city,
            "by_country": by_country
        }
    except Exception as e:
        print(f"[trka_rs] ERROR fetching/parsing runners stats: {e}")

    event_obj = Event(
        id=event_id,
        name=event_name,
        date=parse_date(event_date),
        country="Serbia",
        region=None,
        location=location,
        latitude=latitude,
        longitude=longitude,
        organizer=organizer,
        contact_email=contact_email,
        website=url,
        image_url=image_url,
        source=SOURCE,
        event_url=url,
        registration_opens=registration_opens_dt,
        registration_closes=registration_closes_dt,
        more_details=more_details,
        fee_rsd=fee_rsd,
        fee_eur=fee_eur,
        description=event_description,
        runners_stats=runners_stats,
        participants=participants if participants else None,
        scraped_at=datetime.now(),
        last_updated=datetime.now(),
        last_check=datetime.now()
    )

    # --- RACE EXTRACTION ---
    races = []
    race_links = soup.select('ul.list-group li.list-group-item a')
    for a in race_links:
        race_name = clean_text(a.get_text())
        race_url = a.get('href')
        if race_url and not race_url.startswith('http'):
            race_url = BASE_URL + race_url
        race_distance = None
        race_elevation = None
        race_type = None
        race_description = None
        race_organizer = None
        race_contact = None
        race_registration_url = None
        fee_rsd = None
        fee_eur = None
        try:
            race_resp = get_safe(race_url) if race_url else None
            race_soup = BeautifulSoup(race_resp.content, "lxml") if race_resp else soup
            
            # Extract registration URL for this specific race
            race_registration_url = _extract_registration_url(race_soup, race_url) or registration_url
            
            # Use .row > label for fields
            for div in race_soup.select('div.row'):
                label_elem = div.find('label', class_='col-form-label')
                if not label_elem:
                    continue
                label_text = label_elem.get_text()
                val_elem = div.find('p', class_='form-control-plaintext')
                if 'Type:' in label_text or 'Врста:' in label_text:
                    if val_elem:
                        race_type = clean_text(val_elem.get_text())
                if 'Distance:' in label_text or 'Дужина:' in label_text:
                    if val_elem:
                        race_distance = parse_distance_km(val_elem.get_text())
                if 'Description:' in label_text or 'Опис:' in label_text:
                    if val_elem:
                        race_description = clean_text(val_elem.get_text(separator=' ', strip=True))
                        # Try to extract elevation from description
                        if race_description:
                            race_elevation = _extract_elevation_from_text(race_description)
                if 'Organizer:' in label_text:
                    if val_elem:
                        race_organizer = clean_text(val_elem.get_text(separator=' ', strip=True))
                if 'Contact:' in label_text:
                    mailto = div.find('a', href=lambda h: h and h.startswith('mailto:'))
                    if mailto:
                        race_contact = mailto.get('href').replace('mailto:', '').strip()
                # Look for elevation field explicitly
                if 'Elevation' in label_text or 'D+' in label_text or 'Uspon' in label_text or 'Позитивна' in label_text:
                    if val_elem:
                        elev_text = val_elem.get_text()
                        race_elevation = parse_elev_m(elev_text) or _extract_elevation_from_text(elev_text)
            # Entry fee table
            fee_table = race_soup.find('table', class_='table')
            if fee_table:
                for row in fee_table.select('tbody tr'):
                    price_cells = row.select('td')
                    if len(price_cells) > 1:
                        price_text = price_cells[1].get_text()
                        rsd_match = re.search(r'(\d+)\s*RSD', price_text)
                        if rsd_match:
                            fee_rsd = float(rsd_match.group(1))
                        eur_match = re.search(r'(\d+)\s*€', price_text)
                        if eur_match:
                            fee_eur = float(eur_match.group(1))
        except Exception as e:
            print(f"[trka_rs] ERROR fetching/parsing race detail {race_url}: {e}")
        # Try to match participants by race name (exact or partial)
        race_participants = None
        if participants:
            print(f"[trka_rs] Mapping participants for race: {race_name}")
            if race_name in participants:
                print(f"[trka_rs] Exact match: {race_name} -> {participants[race_name]}")
                race_participants = participants[race_name]
            else:
                for pname, pcount in participants.items():
                    if pname.lower() in race_name.lower() or race_name.lower() in pname.lower():
                        print(f"[trka_rs] Partial match: {race_name} ~ {pname} -> {pcount}")
                        race_participants = pcount
                        break
        race_id = _mk_id(SOURCE, race_name, event_date)
        race = Race(
            id=race_id,
            event_id=event_id,
            name=race_name,
            distance_km=race_distance,
            elevation_m=race_elevation,
            race_type=race_type,
            terrain=_determine_terrain(race_type),
            registration_url=race_registration_url,
            fee_eur=fee_eur,
            fee_rsd=fee_rsd,
            cutoff=None,
            race_url=race_url,
            source=SOURCE,
            description=race_description,
            organizer=race_organizer,
            contact_email=race_contact,
            participants=race_participants,
            scraped_at=datetime.now(),
            last_updated=datetime.now()
        )
        races.append(race)

    return event_obj, races
