"""Scraper for runtrace.net (European trail running calendar)."""

import hashlib
import re
from typing import List, Tuple, Set
from datetime import datetime

# Module-level cache for already scraped URLs
_CACHED_URLS: Set[str] = set()

def set_cached_urls(urls: Set[str]):
    """Set the URLs that have already been scraped (for caching)."""
    global _CACHED_URLS
    _CACHED_URLS = urls

from bs4 import BeautifulSoup

from common.fetch import get_selenium_safe, get_safe
from common.model import Event, Race
from common.normalize import parse_date, parse_distance_km, parse_elev_m, clean_text
from common.geocode import geocode_location

SOURCE = "runtrace.net"
BASE_URL = "https://runtrace.net"
LIST_URL = BASE_URL  # Events are on the homepage


def _mk_id(source: str, name: str, date_str: str) -> str:
    """
    Generate unique race ID from source, name, and date.

    Uses SHA1 hash of concatenated fields (first 16 hex chars).

    Args:
        source: Source domain (e.g., "runtrace.net")
        name: Race name
        date_str: Date string representation

    Returns:
        Unique ID string (16 hex chars)
    """
    composite = f"{source}|{name}|{date_str}".lower()
    return hashlib.sha1(composite.encode("utf-8")).hexdigest()[:16]


def _extract_image_url(soup):
    """Extract event image URL from runtrace page."""
    # Try og:image meta tag
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        return og_image.get('content')
    
    # Try main event image
    main_img = soup.select_one('.event-image img, .event-header img, img.race-cover')
    if main_img and main_img.get('src'):
        src = main_img.get('src')
        if not src.startswith('http'):
            src = BASE_URL + src
        return src
    
    return None


def _extract_registration_url(soup, event_url):
    """Extract registration URL from runtrace page."""
    # Look for registration button
    reg_link = soup.find('a', href=re.compile(r'/reg(?:ister|istration)?'))
    if reg_link and reg_link.get('href'):
        href = reg_link.get('href')
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            return BASE_URL + href
    
    # Common pattern: event_url + /reg
    if event_url:
        reg_url = event_url.rstrip('/') + '/reg'
        return reg_url
    
    return None


def scrape() -> Tuple[List[Event], List[Race]]:
    """
    Scrape races from runtrace.net.

    Returns:
        Tuple of (events_list, races_list)

    Note:
        This is a STUB implementation with placeholder selectors.
        Adjust selectors based on actual HTML structure of runtrace.net.
    """
    events = []
    races = []

    try:
        print(f"Scraping {SOURCE}...")

        # Fetch main race list page using Selenium (bypasses bot detection)
        html = get_selenium_safe(LIST_URL, timeout=30)
        if not html:
            print(f"Failed to fetch {LIST_URL}")
            return events, races

        soup = BeautifulSoup(html, "lxml")

        # Find race cards - they have class grid__race__info
        race_elements = soup.select(".grid__race__info")

        if not race_elements:
            print(f"No race elements found. Check selector: '.grid__race__info'")
            return events, races

        print(f"Found {len(race_elements)} race elements")

        for elem in race_elements:
            try:
                # Extract race info from card
                # Name: a.race-title or first link
                name_elem = elem.select_one(".race-title") or elem.find('a', href='#')
                # Date: .race-date or second text element
                date_elem = elem.select_one(".race-date")
                # Location: .race-location or third text element
                location_elem = elem.select_one(".race-location")
                
                # Participants link: a[href*="/"] (not "#")
                detail_link = None
                for link in elem.find_all('a', href=True):
                    href = link['href']
                    if href != '#' and not href.endswith('/reg'):
                        detail_link = href
                        break

                name = clean_text(name_elem.get_text() if name_elem else None)
                date_str = clean_text(date_elem.get_text() if date_elem else None)
                location = clean_text(location_elem.get_text() if location_elem else None)
                
                # Fallback: parse from entire card text if selectors fail
                if not name or not date_str:
                    text_parts = [t.strip() for t in elem.stripped_strings]
                    if len(text_parts) >= 2:
                        name = name or text_parts[0]
                        date_str = date_str or text_parts[1]
                        if len(text_parts) >= 3:
                            location = location or text_parts[2]

                if not name:
                    continue  # Skip if no name

                # Parse date
                race_date = parse_date(date_str)
                
                # Geocode location
                latitude, longitude = None, None
                if location:
                    try:
                        latitude, longitude = geocode_location(location, "Serbia")
                    except Exception as e:
                        pass  # Silent fail on geocoding

                # Generate IDs
                event_id = _mk_id(SOURCE, name, date_str or "")
                race_id = _mk_id(SOURCE, name + " - Race", date_str or "")

                # Build detail URL
                event_url = None
                if detail_link:
                    if detail_link.startswith('http'):
                        event_url = detail_link
                    elif detail_link.startswith('/'):
                        event_url = BASE_URL + detail_link
                    else:
                        event_url = BASE_URL + '/' + detail_link
                
                # Check if URL already scraped (caching)
                if event_url and event_url in _CACHED_URLS:
                    continue

                # Fetch detail page for more data and get list of all races
                detail_races = _scrape_detail(event_url) if event_url else [{}]
                
                # Extract organizer, description, image, and registration URL from first race
                organizer = None
                description = None
                image_url = None
                registration_url = None
                
                if event_url:
                    # Get image and registration URL from detail page
                    html_detail = get_selenium_safe(event_url, timeout=20) if event_url else None
                    if html_detail:
                        soup_detail = BeautifulSoup(html_detail, "lxml")
                        image_url = _extract_image_url(soup_detail)
                        registration_url = _extract_registration_url(soup_detail, event_url)
                
                if detail_races and len(detail_races) > 0:
                    organizer = detail_races[0].get('organizer')
                    description = detail_races[0].get('description')
                
                # Create Event object
                event = Event(
                    id=event_id,
                    name=name,
                    date=race_date,
                    country="Serbia",  # Default for runtrace.net
                    region=None,
                    location=location,
                    latitude=latitude,
                    longitude=longitude,
                    organizer=organizer,  # Use organizer from detail page
                    contact_email=None,
                    website=event_url,
                    image_url=image_url,
                    source=SOURCE,
                    event_url=event_url,
                    registration_opens=None,
                    registration_closes=None,
                    more_details=None,
                    fee_rsd=None,
                    fee_eur=None,
                    description=description,  # Use description from detail page
                    runners_stats=None,
                    participants=None,
                    scraped_at=datetime.now(),
                    last_updated=datetime.now(),
                    last_check=datetime.now()
                )
                
                # Create a Race object for each race variant
                for idx, race_detail in enumerate(detail_races):
                    # Generate unique race_id for each distance variant
                    race_suffix = race_detail.get('name', f'Race {idx+1}')
                    race = Race(
                        name=race_name,
                        distance_km=race_detail.get('distance_km'),
                        elevation_m=race_detail.get('elevation_m'),
                        race_type=race_detail.get('race_type'),
                        terrain=race_detail.get('terrain'),
                        registration_url=registration_url,
                        fee_eur=race_detail.get('fee_eur'),
                        fee_rsd=race_detail.get('fee_rsd'),
                        cutoff=race_detail.get('cutoff'),
                        race_url=event_url,
                        source=SOURCE,
                        description=race_detail.get('description'),
                        organizer=race_detail.get('organizer'),
                        contact_email=race_detail.get('contact_email'),
                        participants=race_detail.get('participants'),
                        scraped_at=datetime.now(),
                        last_updated=datetime.now()
                    )
                    
                    races.append(race)
                
                events.append(event)

            except Exception as e:
                # Defensive: skip malformed entries
                print(f"Error parsing race element: {e}")
                continue

        print(f"Successfully scraped {len(events)} events with {len(races)} races from {SOURCE}")

    except Exception as e:
        print(f"Error scraping {SOURCE}: {e}")

    return events, races


def _scrape_detail(url: str) -> list:
    """
    Scrape detail page for additional race information.
    Extracts multiple races from selector and their distance/elevation data.

    Args:
        url: Detail page URL

    Returns:
        List of race data dictionaries with distance, elevation, etc.
    """
    import re
    
    races_data = []
    
    try:
        # Use Selenium to load the page fully (modal data should be in the HTML)
        html = get_selenium_safe(url, timeout=20)
        if not html:
            return races_data
        
        soup = BeautifulSoup(html, "lxml")
        
        # Extract event description and organizer from event description
        organizer = None
        description = None
        event_description = soup.select_one(".event-description")
        if event_description:
            # Get full description text
            desc_text = event_description.get_text(separator="\n", strip=True)
            description = clean_text(desc_text)
            
            # Look for "Organizator:" in the description
            org_match = re.search(r'Organizator:\s*([^\n<]+)', desc_text)
            if org_match:
                organizer = clean_text(org_match.group(1))
        
        # First, look for race selector dropdown to extract multiple races
        race_selector = soup.select_one(".js_result_change_race") or soup.select_one(".cs-select-race")
        
        race_options = []
        if race_selector:
            # Extract race options from the selector
            options = race_selector.find_all("option")
            
            for option in options:
                race_name = clean_text(option.get_text())
                race_value = option.get("value", "")
                
                if race_name:
                    race_options.append({
                        'name': race_name,
                        'value': race_value
                    })
        
        # If no races found in selector, create a single default entry
        if not race_options:
            race_options = [{'name': '', 'value': ''}]
        
        # Extract modal data that should be visible in the loaded HTML
        # Look for distance and elevation in the race info sidebar
        distance_elem = soup.select_one(".distance-in")
        elevation_elem = soup.select_one(".elevation-in")
        
        common_distance = None
        common_elevation = None
        
        if distance_elem:
            distance_text = clean_text(distance_elem.get_text())
            dist_match = re.search(r'(\d+(?:\.\d+)?)', distance_text)
            if dist_match:
                try:
                    common_distance = float(dist_match.group(1))
                except:
                    pass
        
        if elevation_elem:
            elevation_text = clean_text(elevation_elem.get_text())
            elev_match = re.search(r'(\d+)', elevation_text)
            if elev_match:
                try:
                    common_elevation = int(elev_match.group(1))
                except:
                    pass
        
        # Process each race option
        for race_opt in race_options:
            race_data = {}
            race_data['name'] = race_opt.get('name', '')
            race_data['value'] = race_opt.get('value', '')
            race_data['race_type'] = 'trail'
            race_data['terrain'] = 'trail'
            race_data['organizer'] = organizer  # Add organizer info
            race_data['description'] = description  # Add full event description
            
            # Extract distance from race name if available (e.g., "6K" -> 6)
            dist_match = re.search(r'(\d+(?:\.\d+)?)\s*k', race_data['name'].lower())
            if dist_match:
                try:
                    race_data['distance_km'] = float(dist_match.group(1))
                except:
                    pass
            
            # If no distance from name, use common distance from modal
            if 'distance_km' not in race_data and common_distance:
                race_data['distance_km'] = common_distance
            
            # Add elevation if available
            if common_elevation:
                race_data['elevation_m'] = common_elevation
            
            races_data.append(race_data)
        
        # If no races data extracted, create default
        if not races_data:
            races_data = [{'race_type': 'trail', 'terrain': 'trail'}]
        
    except Exception as e:
        print(f"Error scraping detail page {url}: {e}")
        races_data = [{'race_type': 'trail', 'terrain': 'trail'}]
    
    return races_data

