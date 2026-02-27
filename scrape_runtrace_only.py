#!/usr/bin/env python3
"""
Scraper script for runtrace.net only.

Scrapes runtrace.net and saves results to data/export/runtrace.json

Usage:
    python scrape_runtrace_only.py
"""

import json
from pathlib import Path
from scrapers import runtrace
from common.model import Event, Race

OUTPUT_DIR = Path("data/export")
OUTPUT_FILE = OUTPUT_DIR / "runtrace.json"


def write_events_with_races(events: list[Event], races: list[Race], output_file: Path) -> None:
    """
    Write events with their races to a single JSON file.
    
    Structure:
    [
        {
            "id": "...",
            "name": "...",
            ...event fields...,
            "races": [
                {"id": "...", "name": "...", ...race fields...},
                {"id": "...", "name": "...", ...race fields...}
            ]
        },
        ...
    ]
    """
    # Create a mapping of event_id to event
    events_dict = {event.id: event for event in events}
    
    # Build events with their races
    output_data = []
    for event in events:
        event_dict = event.dict()
        event_dict['races'] = []
        
        # Add all races for this event
        for race in races:
            if race.event_id == event.id:
                race_dict = race.dict()
                # Remove event_id from race to avoid duplication
                race_dict.pop('event_id', None)
                event_dict['races'].append(race_dict)
        
        output_data.append(event_dict)
    
    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Wrote {len(output_data)} events to {output_file}")


def main():
    print("Scraping runtrace.net...")
    events, races = runtrace.scrape()
    
    if not events and not races:
        print("✗ No events or races found")
        return
    
    print(f"Found {len(events)} events and {len(races)} races")
    
    # Write to JSON file
    write_events_with_races(events, races, OUTPUT_FILE)
    
    print(f"\n✓ Complete! Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
