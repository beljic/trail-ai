#!/usr/bin/env python3
"""
Geocode existing events in races.jsonl (add latitude/longitude).

Usage:
    python geocode_existing.py
    python geocode_existing.py --force  # Re-geocode all locations
"""

import argparse
import json
import sys
from pathlib import Path
from common.geocode import geocode_location


INPUT_FILE = Path("data/clean/races.jsonl")
OUTPUT_FILE = Path("data/clean/races_geocoded.jsonl")


def geocode_events(force=False):
    """Geocode all events that have location but no coordinates."""
    
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found")
        return False
    
    events = []
    geocoded_count = 0
    skipped_count = 0
    failed_count = 0
    
    print("Loading events...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                events.append(event)
            except json.JSONDecodeError:
                continue
    
    print(f"Loaded {len(events)} events")
    print()
    
    print("Geocoding...")
    for i, event in enumerate(events, 1):
        event_name = event.get('name', 'Unknown')
        location = event.get('location')
        country = event.get('country', 'Serbia')
        has_coords = event.get('latitude') is not None and event.get('longitude') is not None
        
        if not location:
            skipped_count += 1
            continue
        
        if has_coords and not force:
            print(f"[{i}/{len(events)}] Skip (has coords): {event_name}")
            skipped_count += 1
            continue
        
        print(f"[{i}/{len(events)}] Geocoding: {location}, {country}...")
        
        try:
            lat, lng = geocode_location(location, country)
            if lat and lng:
                event['latitude'] = lat
                event['longitude'] = lng
                geocoded_count += 1
                print(f"  ✓ ({lat:.4f}, {lng:.4f})")
            else:
                failed_count += 1
                print(f"  ✗ Not found")
        except Exception as e:
            failed_count += 1
            print(f"  ✗ Error: {e}")
    
    # Write output
    print()
    print(f"Writing to {OUTPUT_FILE}...")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for event in events:
            json_line = json.dumps(event, ensure_ascii=False)
            f.write(json_line + "\n")
    
    print()
    print("="*60)
    print(f"Geocoded: {geocoded_count}")
    print(f"Skipped:  {skipped_count}")
    print(f"Failed:   {failed_count}")
    print(f"Total:    {len(events)}")
    print()
    print(f"Output: {OUTPUT_FILE}")
    print("="*60)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Geocode existing events in races.jsonl"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Re-geocode all locations (even if already geocoded)"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("Geocode Existing Events")
    print("="*60)
    print()
    
    success = geocode_events(force=args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
