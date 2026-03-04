#!/usr/bin/env python3
"""Scrape only trka_rs and runtrace, combine with existing, then naturalize."""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Paths
JSONL_FILE = Path("data/clean/races.jsonl")
EXPORT_JSON = Path("data/export/races.json")
FINAL_JSON = Path("data/export/races_naturalized.json")

def load_existing_custom_events() -> List[Dict[str, Any]]:
    """Load custom events that already exist in JSONL."""
    events = []
    if not JSONL_FILE.exists():
        return events
    
    try:
        with open(JSONL_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        print(f"⚠️ Error loading existing events: {e}")
    
    return events

def scrape_trka_rs() -> List[Dict[str, Any]]:
    """Scrape events from trka.rs."""
    print("\n🔄 Scraping trka.rs...")
    try:
        from scrapers import trka_rs
        events, races = trka_rs.scrape()
        
        # Convert to dict format
        result_events = []
        races_by_event = {}
        
        for race in races:
            event_id = race.event_id
            if event_id not in races_by_event:
                races_by_event[event_id] = []
            races_by_event[event_id].append(race.model_dump() if hasattr(race, 'model_dump') else dict(race))
        
        for event in events:
            event_dict = event.model_dump() if hasattr(event, 'model_dump') else dict(event)
            event_dict['races'] = races_by_event.get(event.id, [])
            result_events.append(event_dict)
        
        print(f"✅ Got {len(result_events)} events from trka.rs with {len(races)} races")
        return result_events
    except Exception as e:
        print(f"❌ Error scraping trka.rs: {e}")
        return []

def scrape_runtrace() -> List[Dict[str, Any]]:
    """Scrape events from runtrace.net."""
    print("\n🔄 Scraping runtrace.net...")
    try:
        from scrapers import runtrace
        events, races = runtrace.scrape()
        
        # Convert to dict format
        result_events = []
        races_by_event = {}
        
        for race in races:
            event_id = race.event_id
            if event_id not in races_by_event:
                races_by_event[event_id] = []
            races_by_event[event_id].append(race.model_dump() if hasattr(race, 'model_dump') else dict(race))
        
        for event in events:
            event_dict = event.model_dump() if hasattr(event, 'model_dump') else dict(event)
            event_dict['races'] = races_by_event.get(event.id, [])
            result_events.append(event_dict)
        
        print(f"✅ Got {len(result_events)} events from runtrace with {len(races)} races")
        return result_events
    except Exception as e:
        print(f"❌ Error scraping runtrace: {e}")
        return []

def combine_events(custom: List[Dict], trka_events: List[Dict], runtrace_events: List[Dict]) -> List[Dict]:
    """Combine events from all sources, deduplicating by ID."""
    all_events = custom + trka_events + runtrace_events
    
    # Deduplicate by ID, keeping first occurrence
    seen_ids = set()
    unique_events = []
    
    for event in all_events:
        event_id = event.get('id')
        if event_id not in seen_ids:
            seen_ids.add(event_id)
            unique_events.append(event)
    
    return unique_events

def export_combined(all_events: List[Dict]):
    """Export combined events to JSON."""
    print(f"\n📤 Exporting {len(all_events)} combined events → {EXPORT_JSON}")
    
    EXPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    
    with open(EXPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_events, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Exported to {EXPORT_JSON}")

def naturalize():
    """Run naturalize_data.py."""
    print(f"\n🔄 Naturalizing → {FINAL_JSON}")
    
    import subprocess
    
    try:
        result = subprocess.run([
            sys.executable,
            'naturalize_data.py',
            str(EXPORT_JSON),
            '-o', str(FINAL_JSON),
            '--no-ai'
        ], check=True, capture_output=True, text=True, timeout=300)
        
        print(result.stdout)
        if result.stderr:
            print("Warnings:", result.stderr)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Naturalize failed: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("❌ Naturalize timed out")
        return False

def main():
    print("=" * 70)
    print("SCRAPERS: trka.rs + runtrace → Combined → Naturalized")
    print("=" * 70)
    
    # Load existing custom events
    custom_events = load_existing_custom_events()
    print(f"\n📊 Loaded {len(custom_events)} custom events from {JSONL_FILE}")
    
    # Scrape trka.rs
    trka_events = scrape_trka_rs()
    
    # Scrape runtrace
    runtrace_events = scrape_runtrace()
    
    # Combine all
    total_new = len(trka_events) + len(runtrace_events)
    print(f"\n📊 Combined sources: {len(custom_events)} custom + {len(trka_events)} trka.rs + {len(runtrace_events)} runtrace = {len(custom_events) + total_new} total")
    
    all_events = combine_events(custom_events, trka_events, runtrace_events)
    
    total_races = sum(len(e.get('races', [])) for e in all_events)
    print(f"   Total unique events: {len(all_events)}")
    print(f"   Total races: {total_races}")
    
    # Export combined
    export_combined(all_events)
    
    # Naturalize
    if not naturalize():
        return 1
    
    # Summary
    print("\n" + "=" * 70)
    if FINAL_JSON.exists():
        size_kb = FINAL_JSON.stat().st_size / 1024
        print(f"✅ COMPLETE! Final JSON: {FINAL_JSON} ({size_kb:.1f} KB)")
        
        with open(FINAL_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
            final_races = sum(len(e.get('races', [])) for e in data)
            print(f"   Events: {len(data)}")
            print(f"   Races: {final_races}")
    
    print("=" * 70)
    return 0

if __name__ == '__main__':
    sys.exit(main())
