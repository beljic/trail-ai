#!/usr/bin/env python3
"""Helper script to inspect HTML structure of trka.rs"""

import sys
from bs4 import BeautifulSoup
from common.fetch import get_safe


def inspect_page(url):
    """Fetch and inspect HTML structure"""
    print(f"Fetching {url}...")
    response = get_safe(url)

    if not response:
        print("Failed to fetch page")
        return

    soup = BeautifulSoup(response.content, "lxml")

    # Try different common selectors
    selectors_to_try = [
        ".event-grid > *",
        ".event-grid .event-item",
        ".event-card",
        ".race-item",
        ".event",
        "article",
        ".card",
    ]

    print("\n" + "="*60)
    print("TRYING DIFFERENT SELECTORS:")
    print("="*60)

    for selector in selectors_to_try:
        elements = soup.select(selector)
        print(f"\n{selector}: Found {len(elements)} elements")

        if elements and len(elements) > 0:
            print(f"\n--- First element HTML (truncated) ---")
            first = str(elements[0])[:800]
            print(first)
            if len(str(elements[0])) > 800:
                print("... (truncated)")

    # Also show the event-grid container if it exists
    print("\n" + "="*60)
    print("EVENT-GRID CONTAINER:")
    print("="*60)
    event_grid = soup.select_one(".event-grid")
    if event_grid:
        print(f"Found .event-grid container")
        print(f"Number of direct children: {len(event_grid.find_all(recursive=False))}")
        print(f"\nFirst child HTML (truncated):")
        if event_grid.find_all(recursive=False):
            first_child = str(event_grid.find_all(recursive=False)[0])[:800]
            print(first_child)
            if len(str(event_grid.find_all(recursive=False)[0])) > 800:
                print("... (truncated)")
    else:
        print("No .event-grid found")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.trka.rs/events"
    inspect_page(url)
