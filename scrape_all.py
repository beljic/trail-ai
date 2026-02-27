#!/usr/bin/env python3
"""
Orchestrator script for scraping all race sources.

Runs all configured scrapers, deduplicates races by ID,
and writes normalized output to data/clean/races.jsonl.

Usage:
    python scrape_all.py          # Incremental mode (skip existing races)
    python scrape_all.py --all    # Full mode (scrape everything)
"""

import argparse
import json
import os
from pathlib import Path
from typing import List, Set, Tuple

from common.model import Event, Race

# Custom site scrapers (event URLs)
from scrapers.custom import get_scraper_for_url
import scrapers.custom.ivanjicatrail  # noqa - registers scraper
import scrapers.custom.bjelasicatrail  # noqa - registers scraper
import scrapers.custom.vuckotrail  # noqa - registers scraper

# Import all scrapers
from scrapers import trka_rs
from scrapers import runtrace
from scrapers import racesmanager


# Configure output path
OUTPUT_DIR = Path("data/clean")
OUTPUT_FILE = OUTPUT_DIR / "races.jsonl"
IMAGES_DIR = Path("data/images")

# Custom event URLs to scrape first (site-specific scrapers)
CUSTOM_EVENT_URLS = [
    "https://bjelasicatrail.me/",
    "https://visitbjelasnica.com/vucko-trail-2025/",
    "https://vuckotrail.ba/",
]


def scrape_custom_urls(
    urls: List[str],
    existing_ids: Set[str] | None = None,
    existing_urls: Set[str] | None = None,
) -> Tuple[List[Event], List[Race]]:
    """
    Scrape custom event URLs using site-specific scrapers.

    Args:
        urls: List of event URLs to scrape
        existing_ids: Set of race IDs to skip (incremental)
        existing_urls: Set of already scraped URLs (incremental)

    Returns:
        Tuple of (events_list, races_list)
    """
    events: List[Event] = []
    races: List[Race] = []
    skipped_count = 0

    for raw_url in urls:
        url = raw_url.strip()
        if not url:
            continue
        if not url.startswith("http"):
            url = "https://" + url

        if existing_urls and url in existing_urls:
            print(f"  Skipping already scraped URL: {url}")
            continue

        scraper = get_scraper_for_url(url)
        if not scraper:
            print(f"  No scraper registered for URL: {url}")
            continue

        try:
            event, event_races = scraper(url)
            if not event or not event_races:
                continue

            if existing_ids:
                new_races = []
                for race in event_races:
                    if race.id in existing_ids:
                        skipped_count += 1
                    else:
                        new_races.append(race)

                if new_races:
                    events.append(event)
                    races.extend(new_races)
            else:
                events.append(event)
                races.extend(event_races)
        except Exception as e:
            print(f"  Error scraping custom URL {url}: {e}")
            continue

    if skipped_count > 0:
        print(f"  Skipped {skipped_count} existing race(s) from custom URLs")

    return events, races


def load_existing_ids(jsonl_path: Path) -> Set[str]:
    """
    Load existing race IDs from JSONL file.

    Args:
        jsonl_path: Path to existing JSONL file

    Returns:
        Set of existing race IDs
    """
    existing_ids = set()

    if not jsonl_path.exists():
        return existing_ids

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    race = json.loads(line)
                    if race.get("id"):
                        existing_ids.add(race["id"])
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Warning: Could not read existing file {jsonl_path}: {e}")

    return existing_ids


def load_existing_races(jsonl_path: Path) -> List[dict]:
    """
    Load existing races from JSONL file.

    Args:
        jsonl_path: Path to existing JSONL file

    Returns:
        List of existing race dictionaries
    """
    existing_races = []

    if not jsonl_path.exists():
        return existing_races

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    race = json.loads(line)
                    existing_races.append(race)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Warning: Could not read existing file {jsonl_path}: {e}")

    return existing_races


def load_existing_urls(jsonl_path: Path) -> Set[str]:
    """
    Load existing event/race URLs from JSONL file for caching.

    Args:
        jsonl_path: Path to existing JSONL file

    Returns:
        Set of existing event_url and race_url values
    """
    existing_urls = set()

    if not jsonl_path.exists():
        return existing_urls

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    # Add event URL
                    if event.get('event_url'):
                        existing_urls.add(event['event_url'])
                    # Add race URLs
                    for race in event.get('races', []):
                        if race.get('race_url'):
                            existing_urls.add(race['race_url'])
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Warning: Could not read existing file {jsonl_path}: {e}")

    return existing_urls


def scrape_all_sources(existing_ids: Set[str] = None) -> Tuple[List[Event], List[Race]]:
    """
    Run all scrapers and collect events and races.

    Args:
        existing_ids: Set of IDs to skip (for incremental mode)

    Returns:
        Tuple of (events_list, races_list)
    """
    all_events = []
    all_races = []
    skipped_count = 0

    # List of scraper modules to run
    # Add new scrapers here as you create them
    scrapers = [
        trka_rs,
        runtrace,
        racesmanager,
        # Add more scrapers here
    ]

    for scraper_module in scrapers:
        try:
            events, races = scraper_module.scrape()
            
            # Filter out existing races in incremental mode
            if existing_ids:
                new_events = []
                new_races = []
                for race in races:
                    if race.id in existing_ids:
                        skipped_count += 1
                    else:
                        new_races.append(race)
                
                # Only add events if their races are new
                event_ids_to_add = set(r.event_id for r in new_races)
                for event in events:
                    if event.id in event_ids_to_add:
                        new_events.append(event)
                
                events = new_events
                races = new_races
            
            all_events.extend(events)
            all_races.extend(races)
        except Exception as e:
            print(f"Error running scraper {scraper_module.__name__}: {e}")
            continue

    if skipped_count > 0:
        print(f"Skipped {skipped_count} existing race(s) (incremental mode)")

    return all_events, all_races


def deduplicate_races(races: List[Race]) -> List[Race]:
    """
    Deduplicate races by ID, keeping first occurrence.

    Args:
        races: List of races (may contain duplicates)

    Returns:
        Deduplicated list of races
    """
    seen_ids = set()
    unique_races = []

    for race in races:
        if race.id not in seen_ids:
            seen_ids.add(race.id)
            unique_races.append(race)

    duplicates_removed = len(races) - len(unique_races)
    if duplicates_removed > 0:
        print(f"Removed {duplicates_removed} duplicate race(s)")

    return unique_races


def deduplicate_events(events: List[Event]) -> List[Event]:
    """
    Deduplicate events by ID, keeping first occurrence.

    Args:
        events: List of events (may contain duplicates)

    Returns:
        Deduplicated list of events
    """
    seen_ids = set()
    unique_events = []

    for event in events:
        if event.id not in seen_ids:
            seen_ids.add(event.id)
            unique_events.append(event)

    duplicates_removed = len(events) - len(unique_events)
    if duplicates_removed > 0:
        print(f"Removed {duplicates_removed} duplicate event(s)")

    return unique_events


def write_jsonl(events: List[Event], races: List[Race], output_dir: Path, append: bool = False) -> None:
    """
    Write events and races to JSONL files.

    Args:
        events: List of Event objects
        races: List of Race objects
        output_dir: Directory to save output files
        append: If True, append instead of overwriting
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    mode = "a" if append else "w"

    # Novi format: jedan event po liniji, sa poljem 'races' (lista dictova)
    races_file = output_dir / "races.jsonl"
    # Mapiraj event_id na sve pripadajuće trke
    races_by_event = {}
    for race in races:
        races_by_event.setdefault(race.event_id, []).append(race)

    with open(races_file, mode, encoding="utf-8") as f:
        for event in events:
            event_dict = event.model_dump(mode="json") if hasattr(event, 'model_dump') else dict(event)
            event_races = races_by_event.get(event.id, [])
            event_dict["races"] = [r.model_dump(mode="json") if hasattr(r, 'model_dump') else dict(r) for r in event_races]
            json_line = json.dumps(event_dict, ensure_ascii=False)
            f.write(json_line + "\n")
    action = "Appended" if append else "Wrote"
    print(f"{action} {len(events)} eventova u {races_file}")


def download_images(events: List[Event], images_dir: Path) -> dict:
    """
    Download images for events that have image_url.

    Args:
        events: List of Event objects
        images_dir: Directory to save images

    Returns:
        Dictionary with download statistics
    """
    from common.fetch import download_image_safe

    stats = {"downloaded": 0, "skipped": 0, "failed": 0}

    # Ensure images directory exists
    images_dir.mkdir(parents=True, exist_ok=True)

    # Images live on events (not races)
    for event in events:
        if not hasattr(event, 'image_url'):
            continue

        image_url = getattr(event, 'image_url', None)
        if not image_url:
            continue

        image_url = str(image_url)
        result = download_image_safe(image_url, str(images_dir), event.id)

        if result:
            stats["downloaded"] += 1
        else:
            stats["failed"] += 1

    return stats


def main():
    """Main orchestration function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Scrape trail race data from configured sources."
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Full scrape mode - scrape all races (default: incremental)"
    )
    parser.add_argument(
        "--images", "-i",
        action="store_true",
        help="Download images for scraped races"
    )
    args = parser.parse_args()

    incremental = not args.all
    mode_str = "INCREMENTAL" if incremental else "FULL"

    print("=" * 60)
    print(f"Trail Race Scraper - Starting ({mode_str} mode)")
    print("=" * 60)

    # Load existing data for incremental mode
    existing_ids = set()
    existing_urls = set()
    existing_count = 0
    if incremental:
        print(f"\nLoading existing races from {OUTPUT_FILE}...")
        existing_ids = load_existing_ids(OUTPUT_FILE)
        existing_urls = load_existing_urls(OUTPUT_FILE)
        existing_count = len(existing_ids)
        print(f"Found {existing_count} existing race(s)")
        print(f"Found {len(existing_urls)} unique URL(s) to skip")

    # Step 1: Scrape custom event URLs first
    print("\n[1/5] Scraping custom event URLs...")
    custom_events, custom_races = scrape_custom_urls(
        CUSTOM_EVENT_URLS,
        existing_ids if incremental else None,
        existing_urls if incremental else None,
    )
    print(f"Custom races scraped: {len(custom_races)}")

    # Step 2: Scrape all sources
    print("\n[2/5] Scraping all sources...")
    # Pass existing_urls to scrapers for URL-based caching
    import scrapers.trka_rs as trka_rs_module
    import scrapers.runtrace as runtrace_module
    import scrapers.racesmanager as racesmanager_module
    
    # Set cached URLs on scraper modules (they can check before fetching detail pages)
    if hasattr(trka_rs_module, 'set_cached_urls'):
        trka_rs_module.set_cached_urls(existing_urls)
    if hasattr(runtrace_module, 'set_cached_urls'):
        runtrace_module.set_cached_urls(existing_urls)
    if hasattr(racesmanager_module, 'set_cached_urls'):
        racesmanager_module.set_cached_urls(existing_urls)
    
    source_events, source_races = scrape_all_sources(existing_ids if incremental else None)
    print(f"New races scraped: {len(source_races)}")

    new_events = custom_events + source_events
    new_races = custom_races + source_races

    # Step 3: Deduplicate new races and align events
    print("\n[3/5] Deduplicating...")
    unique_races = deduplicate_races(new_races)
    event_ids_with_races = {r.event_id for r in unique_races}
    unique_events = [e for e in deduplicate_events(new_events) if e.id in event_ids_with_races]
    print(f"Unique new races: {len(unique_races)}")
    print(f"Unique new events: {len(unique_events)}")

    # Step 4: Write to JSONL
    print("\n[4/5] Writing output...")
    if incremental and unique_races:
        # Append new races to existing file
        write_jsonl(unique_events, unique_races, OUTPUT_DIR, append=True)
    elif not incremental:
        # Full mode - overwrite file
        write_jsonl(unique_events, unique_races, OUTPUT_DIR, append=False)
    else:
        print("No new races to add.")

    # Step 5: Download images (optional)
    images_downloaded = 0
    if args.images and unique_events:
        print("\n[5/5] Downloading images...")
        image_stats = download_images(unique_events, IMAGES_DIR)
        images_downloaded = image_stats["downloaded"]
        print(f"Images: {image_stats['downloaded']} downloaded, {image_stats['failed']} failed")
    elif args.images:
        print("\n[5/5] No new events to download images for.")
    else:
        print("\n[5/5] Skipping image download (use --images to enable)")

    # Summary
    total_races = existing_count + len(unique_races) if incremental else len(unique_races)
    print("\n" + "=" * 60)
    print("Summary:")
    if incremental:
        print(f"  Previously existing: {existing_count}")
        print(f"  New races added:     {len(unique_races)}")
    print(f"  Total races:         {total_races}")
    if args.images:
        print(f"  Images downloaded:   {images_downloaded}")
    print(f"  Output file:         {OUTPUT_FILE}")
    if args.images:
        print(f"  Images directory:    {IMAGES_DIR}")
    print("=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
