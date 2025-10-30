"""Scraper for runtrace.net (European trail running calendar)."""

import hashlib
from typing import List

from bs4 import BeautifulSoup

from common.fetch import get_safe
from common.model import Race
from common.normalize import parse_date, parse_distance_km, parse_elev_m, clean_text


SOURCE = "runtrace.net"
BASE_URL = "https://www.runtrace.net"  # TODO: verify actual URL
LIST_URL = f"{BASE_URL}/races"  # TODO: adjust to actual race list page


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


def scrape() -> List[Race]:
    """
    Scrape races from runtrace.net.

    Returns:
        List of Race objects

    Note:
        This is a STUB implementation with placeholder selectors.
        Adjust selectors based on actual HTML structure of runtrace.net.
    """
    races = []

    try:
        print(f"Scraping {SOURCE}...")

        # Fetch main race list page
        response = get_safe(LIST_URL)
        if not response:
            print(f"Failed to fetch {LIST_URL}")
            return races

        soup = BeautifulSoup(response.content, "lxml")

        # TODO: adjust selectors based on actual HTML structure
        # This is a PLACEHOLDER - real selectors must be determined by inspecting runtrace.net
        race_elements = soup.select(".race-card")  # TODO: adjust selector

        if not race_elements:
            print(f"No race elements found. Check selector: '.race-card'")
            # Returning empty list instead of raising exception (defensive)
            return races

        print(f"Found {len(race_elements)} race elements")

        for elem in race_elements:
            try:
                # TODO: adjust all selectors below based on actual HTML
                # Extract basic info from list page
                name_elem = elem.select_one(".race-title")  # TODO: adjust selector
                date_elem = elem.select_one(".race-date")  # TODO: adjust selector
                country_elem = elem.select_one(".race-country")  # TODO: adjust selector
                distance_elem = elem.select_one(".race-distance")  # TODO: adjust selector
                elevation_elem = elem.select_one(".race-elevation")  # TODO: adjust selector

                name = clean_text(name_elem.get_text() if name_elem else None)
                date_str = clean_text(date_elem.get_text() if date_elem else None)
                country = clean_text(country_elem.get_text() if country_elem else None)
                distance_str = clean_text(distance_elem.get_text() if distance_elem else None)
                elevation_str = clean_text(elevation_elem.get_text() if elevation_elem else None)

                if not name:
                    continue  # Skip if no name

                # Parse normalized fields
                race_date = parse_date(date_str)
                distance_km = parse_distance_km(distance_str)
                elevation_m = parse_elev_m(elevation_str)

                # Generate unique ID
                race_id = _mk_id(SOURCE, name, date_str or "")

                # Optional: fetch detail page for more info
                # detail_link = elem.select_one("a.race-link")  # TODO: adjust selector
                # if detail_link and detail_link.get("href"):
                #     detail_url = detail_link["href"]
                #     if not detail_url.startswith("http"):
                #         detail_url = BASE_URL + detail_url
                #     detail_data = _scrape_detail(detail_url)
                #     # merge detail_data into race object
                # For now, we skip detail page to avoid extra requests

                race = Race(
                    id=race_id,
                    name=name,
                    date=race_date,
                    country=country,
                    region=None,  # TODO: extract if available
                    location=None,  # TODO: extract if available
                    distance_km=distance_km,
                    elevation_m=elevation_m,
                    terrain=None,  # TODO: extract if available
                    website=None,  # TODO: extract if available
                    registration_url=None,  # TODO: extract if available
                    fee_eur=None,  # TODO: extract if available
                    cutoff=None,  # TODO: extract if available
                    organizer=None,  # TODO: extract if available
                    source=SOURCE,
                )

                races.append(race)

            except Exception as e:
                # Defensive: skip malformed entries
                print(f"Error parsing race element: {e}")
                continue

        print(f"Successfully scraped {len(races)} races from {SOURCE}")

    except Exception as e:
        print(f"Error scraping {SOURCE}: {e}")

    return races


def _scrape_detail(url: str) -> dict:
    """
    Scrape detail page for additional race information.

    Args:
        url: Detail page URL

    Returns:
        Dictionary with additional race data

    Note:
        This is a STUB for future expansion.
        Currently disabled by default to minimize requests.
    """
    # TODO: implement detail page scraping if needed
    # response = get_safe(url)
    # if not response:
    #     return {}
    # soup = BeautifulSoup(response.content, "lxml")
    # ... extract additional fields ...
    return {}
