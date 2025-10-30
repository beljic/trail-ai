#!/usr/bin/env python3
"""
Orchestrator script for scraping all race sources.

Runs all configured scrapers, deduplicates races by ID,
and writes normalized output to data/clean/races.jsonl.
"""

import json
import os
from pathlib import Path
from typing import List

from common.model import Race

# Import all scrapers
from scrapers import trka_rs
# from scrapers import runtrace  # PAUSED: uncomment when ready to test


# Configure output path
OUTPUT_DIR = Path("data/clean")
OUTPUT_FILE = OUTPUT_DIR / "races.jsonl"


def scrape_all_sources() -> List[Race]:
    """
    Run all scrapers and collect races.

    Returns:
        Combined list of all scraped races (may contain duplicates)
    """
    all_races = []

    # List of scraper modules to run
    # Add new scrapers here as you create them
    scrapers = [
        trka_rs,
        # runtrace,  # PAUSED: uncomment when ready to test
        # Add more scrapers here
    ]

    for scraper_module in scrapers:
        try:
            races = scraper_module.scrape()
            all_races.extend(races)
        except Exception as e:
            print(f"Error running scraper {scraper_module.__name__}: {e}")
            continue

    return all_races


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
        print(f"Removed {duplicates_removed} duplicate(s)")

    return unique_races


def write_jsonl(races: List[Race], output_path: Path) -> None:
    """
    Write races to JSONL file (UTF-8, one race per line).

    Args:
        races: List of Race objects to write
        output_path: Path to output JSONL file
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSONL
    with open(output_path, "w", encoding="utf-8") as f:
        for race in races:
            # Convert to dict and handle special types
            race_dict = race.model_dump(mode="json")

            # Write as single-line JSON
            json_line = json.dumps(race_dict, ensure_ascii=False)
            f.write(json_line + "\n")

    print(f"Wrote {len(races)} race(s) to {output_path}")


def main():
    """Main orchestration function."""
    print("=" * 60)
    print("Trail Race Scraper - Starting")
    print("=" * 60)

    # Step 1: Scrape all sources
    print("\n[1/3] Scraping all sources...")
    all_races = scrape_all_sources()
    print(f"Total races scraped: {len(all_races)}")

    # Step 2: Deduplicate
    print("\n[2/3] Deduplicating...")
    unique_races = deduplicate_races(all_races)
    print(f"Unique races: {len(unique_races)}")

    # Step 3: Write to JSONL
    print("\n[3/3] Writing output...")
    write_jsonl(unique_races, OUTPUT_FILE)

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Total scraped: {len(all_races)}")
    print(f"  Unique races:  {len(unique_races)}")
    print(f"  Output file:   {OUTPUT_FILE}")
    print("=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
