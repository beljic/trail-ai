#!/usr/bin/env python3
"""
Collect all races from all sources and merge into a single file.

Usage:
    python collect_all_races.py          # Collect from existing files
    python collect_all_races.py --scrape # Scrape all sources first
    python collect_all_races.py --full   # Full scrape (overwrite existing)
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Import scraper modules
from common.model import Event, Race
from scrapers import trka_rs, runtrace, racesmanager
from scrapers.custom import get_scraper_for_url
import scrapers.custom.ivanjicatrail
import scrapers.custom.bjelasicatrail
import scrapers.custom.vuckotrail


OUTPUT_DIR = Path("data/export")
RACES_ALL_FILE = OUTPUT_DIR / "races_all.json"
RACES_ALL_DIR = OUTPUT_DIR / "races_all"

CUSTOM_EVENT_URLS = [
    "https://bjelasicatrail.me/",
    "https://visitbjelasnica.com/vucko-trail-2025/",
    "https://vuckotrail.ba/",
]


def scrape_all_sources() -> tuple[List[Event], List[Race]]:
    """Scrape all sources and return events and races."""
    all_events = []
    all_races = []

    scrapers = [
        ("trka.rs", trka_rs),
        ("runtrace.net", runtrace),
        ("racesmanager.com", racesmanager),
    ]

    for source_name, scraper_module in scrapers:
        try:
            print(f"Scraping {source_name}...")
            events, races = scraper_module.scrape()
            all_events.extend(events)
            all_races.extend(races)
            print(f"  Found {len(races)} races from {source_name}")
        except Exception as e:
            print(f"  Error scraping {source_name}: {e}")
            continue

    # Scrape custom URLs
    print("\nScraping custom event URLs...")
    for url in CUSTOM_EVENT_URLS:
        try:
            scraper = get_scraper_for_url(url)
            if not scraper:
                print(f"  No scraper for {url}")
                continue
            event, event_races = scraper(url)
            if event and event_races:
                all_events.append(event)
                all_races.extend(event_races)
                print(f"  Found {len(event_races)} races from {url}")
        except Exception as e:
            print(f"  Error scraping {url}: {e}")
            continue

    return all_events, all_races


def deduplicate_races(races: List) -> List:
    """Remove duplicate races by ID."""
    seen_ids = set()
    unique = []
    for race in races:
        race_id = race.id if hasattr(race, 'id') else race.get('id', None)
        if race_id and race_id not in seen_ids:
            seen_ids.add(race_id)
            unique.append(race)
    return unique


def races_to_dicts(races: List) -> List[Dict[str, Any]]:
    """Convert Race objects to dictionaries."""
    result = []
    for race in races:
        if isinstance(race, dict):
            result.append(race)
        elif hasattr(race, 'model_dump'):
            result.append(race.model_dump(mode="json"))
        else:
            result.append(dict(race))
    return result


def load_existing_races() -> List[Race]:
    """Load races from existing files."""
    races = []

    # Try to load from races_all.json
    if RACES_ALL_FILE.exists():
        print(f"Loading from {RACES_ALL_FILE}...")
        try:
            with open(RACES_ALL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "races" in data:
                    races_data = data["races"]
                elif isinstance(data, list):
                    races_data = data
                else:
                    races_data = []
                
                for race_dict in races_data:
                    try:
                        race = Race(**race_dict) if isinstance(race_dict, dict) else race_dict
                        races.append(race)
                    except Exception as e:
                        # Try to add as dict if model construction fails
                        races.append(race_dict)
        except Exception as e:
            print(f"  Error loading from {RACES_ALL_FILE}: {e}")

    # Try to load from races_all/ directory
    if RACES_ALL_DIR.exists():
        print(f"Loading from {RACES_ALL_DIR}...")
        for json_file in RACES_ALL_DIR.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        races.extend(data)
                    elif isinstance(data, dict):
                        if "races" in data:
                            races.extend(data["races"])
                        else:
                            races.append(data)
            except Exception as e:
                print(f"  Error loading {json_file}: {e}")

    # Try to load from data/clean/races.jsonl
    clean_file = Path("data/clean/races.jsonl")
    if clean_file.exists():
        print(f"Loading from {clean_file}...")
        try:
            with open(clean_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        event_dict = json.loads(line)
                        if "races" in event_dict:
                            races.extend(event_dict["races"])
                    except Exception as e:
                        pass
        except Exception as e:
            print(f"  Error loading from {clean_file}: {e}")

    # Try to load from data/export/races.json
    export_races_file = Path("data/export/races.json")
    if export_races_file.exists():
        print(f"Loading from {export_races_file}...")
        try:
            with open(export_races_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    races.extend(data)
                elif isinstance(data, dict) and "races" in data:
                    races.extend(data["races"])
        except Exception as e:
            print(f"  Error loading from {export_races_file}: {e}")

    print(f"Loaded {len(races)} existing races")
    return races


def write_races_all_json(races: List, filepath: Path) -> None:
    """Write races to a single JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    race_dicts = races_to_dicts(races)
    
    # Extract sources from races
    sources = set()
    for r in race_dicts:
        if isinstance(r, dict) and "source" in r:
            sources.add(r["source"])
    
    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_races": len(race_dicts),
            "sources": sorted(list(sources)),
        },
        "races": race_dicts,
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Written {len(race_dicts)} races to {filepath}")


def write_races_all_dir(races: List, dirpath: Path) -> None:
    """Write races to separate files in a directory by source."""
    dirpath.mkdir(parents=True, exist_ok=True)
    
    # Group races by source
    races_by_source = {}
    for race in races:
        source = race.source if hasattr(race, 'source') else race.get("source", "unknown") if isinstance(race, dict) else "unknown"
        if source not in races_by_source:
            races_by_source[source] = []
        races_by_source[source].append(race)
    
    # Write each source to its own file
    for source, source_races in races_by_source.items():
        filename = dirpath / f"{source.replace('.', '_').replace('/', '_')}.json"
        race_dicts = races_to_dicts(source_races)
        
        output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "source": source,
                "total_races": len(race_dicts),
            },
            "races": race_dicts,
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"Written {len(race_dicts)} races from {source} to {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Collect all races from all sources into a single file."
    )
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Scrape all sources and merge with existing",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full scrape - ignore existing files and start fresh",
    )
    parser.add_argument(
        "--dir",
        action="store_true",
        help="Also create separate files in races_all/ directory by source",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Collecting All Races")
    print("=" * 60)

    all_races = []

    # Load existing races unless --full is specified
    if not args.full:
        print("\n[1/3] Loading existing races...")
        all_races.extend(load_existing_races())
    else:
        print("\n[1/3] Full mode - starting fresh")

    # Scrape if requested
    if args.scrape or args.full:
        print("\n[2/3] Scraping all sources...")
        events, new_races = scrape_all_sources()
        all_races.extend(new_races)
        print(f"Total races after scraping: {len(all_races)}")
    else:
        print("\n[2/3] Skipping scraping (use --scrape to enable)")

    # Deduplicate
    print("\n[3/3] Deduplicating and writing output...")
    unique_races = deduplicate_races(all_races)
    print(f"Unique races: {len(unique_races)}")

    # Write to races_all.json
    write_races_all_json(unique_races, RACES_ALL_FILE)

    # Write to races_all/ directory if requested
    if args.dir:
        write_races_all_dir(unique_races, RACES_ALL_DIR)

    print("\n" + "=" * 60)
    print(f"All races collected: {len(unique_races)}")
    print(f"Output: {RACES_ALL_FILE}")
    if args.dir:
        print(f"Also in directory: {RACES_ALL_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
