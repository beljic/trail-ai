#!/usr/bin/env python3
"""
Complete scrape: Custom + trka.rs + runtrace → Combined → Naturalized

THIS IS THE MASTER SCRAPER - Uses incremental mode from scrape_all.py
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

JSONL_FILE = Path("data/clean/races.jsonl")
EXPORT_JSON = Path("data/export/races.json")
FINAL_JSON = Path("data/export/races_naturalized.json")

def run_command(cmd, description):
    """Run shell command, return success status."""
    print(f"\n{'='*70}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {description}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e}")
        return False

def load_stats():
    """Load and display current stats."""
    if not FINAL_JSON.exists():
        print("❌ No naturalized data yet")
        return 0, 0
    
    with open(FINAL_JSON, encoding='utf-8') as f:
        data = json.load(f)
    
    events = len(data)
    races = sum(len(e.get('races', [])) for e in data)
    
    return events, races

def main():
    print("\n" + "=" * 70)
    print("TRAIL AI: Complete Scrape Pipeline")
    print("Izvora: Custom + trka.rs + runtrace.net")
    print("=" * 70)
    
    # Step 1: Full scrape with all sources
    if not run_command(
        "source venv/bin/activate && python3 scrape_all.py --all",
        "Step 1/3: Full scrape (custom + trka.rs + runtrace)"
    ):
        print("⚠️  Scrape failed, but continuing...")
    
    # Check what we got
    if JSONL_FILE.exists():
        lines = sum(1 for _ in open(JSONL_FILE))
        print(f"\n✅ Scraped {lines} events to {JSONL_FILE}")
    
    # Step 2: Export to JSON
    if not run_command(
        "source venv/bin/activate && python3 run_pipeline.py",
        "Step 2/3: Export & Naturalize"
    ):
        print("❌ Pipeline failed")
        return 1
    
    # Step 3: Display final stats
    print(f"\n{'='*70}")
    print("Final Statistics")
    print(f"{'='*70}")
    
    events, races = load_stats()
    if events > 0:
        print(f"✅ Events: {events}")
        print(f"✅ Races:  {races}")
        print(f"✅ Output: {FINAL_JSON} ({FINAL_JSON.stat().st_size / 1024:.1f} KB)")
        
        # Show source breakdown
        with open(EXPORT_JSON, encoding='utf-8') as f:
            data = json.load(f)
        from collections import Counter
        sources = Counter(e.get('source') for e in data)
        print(f"\n📍 Po izvorima:")
        for src, cnt in sorted(sources.items(), key=lambda x: -x[1]):
            print(f"   {src}: {cnt}")
    
    print(f"{'='*70}\n")
    return 0

if __name__ == '__main__':
    sys.exit(main())
