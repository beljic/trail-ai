#!/usr/bin/env python3
"""Quick test of timisoara21k scraper."""

import sys
sys.path.insert(0, '/var/www/html/trail-ai')

from scrapers.custom.timisoara21k import scrape_timisoara21k

url = "https://timisoara.21k.ro/curse/?lang=en"
event, races = scrape_timisoara21k(url)

if event:
    print(f"✓ Event: {event.name}")
    print(f"  Date: {event.date}")
    print(f"  Location: {event.location}")
    print(f"  Organizer: {event.organizer}")
    print(f"  Races: {len(races)}")
    print()
    
    for race in races:
        print(f"  - {race.name}: {race.distance_km}km")
        print(f"    Registration: {race.registration_url}")
else:
    print("✗ Failed to scrape event")
    sys.exit(1)
