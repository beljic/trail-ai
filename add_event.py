#!/usr/bin/env python3
"""
CLI tool to scrape individual event URLs and add them to races.jsonl.

Usage:
    python add_event.py <event_url>
    python add_event.py https://ivanjicatrail.rs/en/#
    python add_event.py https://example.com/event --dry-run
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from common.model import Event, Race

# Import custom scrapers
from scrapers.custom import get_scraper_for_url
import scrapers.custom.ivanjicatrail  # noqa - registers scraper
import scrapers.custom.bjelasicatrail  # noqa - registers scraper
import scrapers.custom.vuckotrail  # noqa - registers scraper


OUTPUT_FILE = Path("data/clean/races.jsonl")


def load_existing_urls() -> set:
    """Load existing event URLs from races.jsonl to avoid duplicates."""
    existing_urls = set()
    
    if not OUTPUT_FILE.exists():
        return existing_urls
    
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event_data = json.loads(line)
                    if event_data.get('event_url'):
                        existing_urls.add(event_data['event_url'])
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Warning: Could not read existing file: {e}")
    
    return existing_urls


def append_to_jsonl(event: Event, races: list[Race]):
    """Append event and races to races.jsonl file."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Build event dict with races
    event_dict = event.model_dump(mode="json") if hasattr(event, 'model_dump') else dict(event)
    event_dict["races"] = [
        r.model_dump(mode="json") if hasattr(r, 'model_dump') else dict(r)
        for r in races
    ]
    
    # Append to file
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        json_line = json.dumps(event_dict, ensure_ascii=False)
        f.write(json_line + "\n")
    
    print(f"✓ Added to {OUTPUT_FILE}")


def scrape_event(url: str, dry_run: bool = False) -> bool:
    """
    Scrape event from URL and add to races.jsonl.
    
    Args:
        url: Event page URL
        dry_run: If True, don't save to file
        
    Returns:
        True if successful, False otherwise
    """
    # Normalize URL
    url = url.strip()
    if not url.startswith('http'):
        url = 'https://' + url
    
    # Check if already scraped
    existing_urls = load_existing_urls()
    if url in existing_urls:
        print(f"⚠ Event URL already exists in {OUTPUT_FILE}")
        print(f"  URL: {url}")
        return False
    
    # Find appropriate scraper
    scraper = get_scraper_for_url(url)
    if not scraper:
        domain = urlparse(url).netloc
        print(f"✗ No scraper found for domain: {domain}")
        print(f"\nTo add support for this site, create a new scraper in:")
        print(f"  scrapers/custom/{domain.replace('.', '_')}.py")
        print(f"\nSee scrapers/custom/ivanjicatrail.py for an example.")
        return False
    
    # Run scraper
    try:
        event, races = scraper(url)
        
        if not event or not races:
            print(f"✗ No event or races extracted from {url}")
            return False
        
        # Display extracted data
        print(f"\n{'='*60}")
        print(f"Event: {event.name}")
        print(f"Date: {event.date}")
        print(f"Location: {event.location}")
        print(f"Races: {len(races)}")
        for i, race in enumerate(races, 1):
            dist = f"{race.distance_km}km" if race.distance_km else "N/A"
            print(f"  {i}. {race.name} ({dist})")
        print(f"{'='*60}\n")
        
        if dry_run:
            print("✓ Dry run - not saving to file")
            return True
        
        # Save to file
        append_to_jsonl(event, races)
        return True
        
    except Exception as e:
        print(f"✗ Error scraping {url}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Scrape individual event URL and add to races.jsonl",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python add_event.py https://ivanjicatrail.rs/en/#
  python add_event.py https://example.com/event --dry-run
  
To add support for new sites, create a scraper in:
  scrapers/custom/<domain>.py
        """
    )
    parser.add_argument("url", help="Event page URL to scrape")
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Extract data but don't save to file"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("Add Event - Individual Event Scraper")
    print("="*60)
    print()
    
    success = scrape_event(args.url, dry_run=args.dry_run)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
