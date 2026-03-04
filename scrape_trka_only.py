#!/usr/bin/env python3
"""Scrape samo trka.rs, dodaj custom events, naturalize."""

import json
import sys
from pathlib import Path
from typing import List, Dict

def load_custom():
    """Load existing custom events."""
    events = []
    jsonl = Path('data/clean/races.jsonl')
    if jsonl.exists():
        with open(jsonl, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        events.append(json.loads(line))
                    except:
                        pass
    print(f"📊 Loaded {len(events)} custom events")
    return events

def scrape_trka():
    """Scrape trka.rs and convert to dicts."""
    print("\n🔄 Scraping trka.rs...")
    try:
        from scrapers import trka_rs
        events, races = trka_rs.scrape()
        
        result = []
        by_event = {}
        for r in races:
            eid = r.event_id
            if eid not in by_event:
                by_event[eid] = []
            by_event[eid].append(r.model_dump() if hasattr(r, 'model_dump') else dict(r))
        
        for e in events:
            ed = e.model_dump() if hasattr(e, 'model_dump') else dict(e)
            ed['races'] = by_event.get(e.id, [])
            result.append(ed)
        
        print(f"✅ Got {len(result)} events, {len(races)} races from trka.rs")
        return result
    except Exception as ex:
        print(f"❌ Error: {ex}")
        import traceback
        traceback.print_exc()
        return []

def combine(custom, trka_events):
    """Combine and dedupe."""
    all_ev = custom + trka_events
    seen = set()
    unique = []
    for e in all_ev:
        eid = e.get('id')
        if eid not in seen:
            seen.add(eid)
            unique.append(e)
    return unique

def save_json(events, path):
    """Save to JSON."""
    Path(path).parent.mkdir(exist_ok=True, parents=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False, default=str)
    print(f"💾 Saved {len(events)} events to {path}")

def naturalize(inp, out):
    """Run naturalize."""
    import subprocess
    print(f"\n🔄 Naturalizing...")
    try:
        subprocess.run([
            sys.executable, 'naturalize_data.py',
            str(inp), '-o', str(out), '--no-ai'
        ], check=True, timeout=300)
        print(f"✅ Naturalized → {out}")
        return True
    except Exception as e:
        print(f"❌ Naturalize failed: {e}")
        return False

def main():
    print("=" * 70)
    print("SCRAPE: Custom + trka.rs → Naturalized")
    print("=" * 70)
    
    custom = load_custom()
    trka_events = scrape_trka()
    
    all_ev = combine(custom, trka_events)
    print(f"\n📊 Combined: {len(all_ev)} total events")
    
    races_json = Path('data/export/races.json')
    save_json(all_ev, races_json)
    
    # Naturalize
    nat_json = Path('data/export/races_naturalized.json')
    if naturalize(races_json, nat_json):
        # Stats
        with open(nat_json, encoding='utf-8') as f:
            data = json.load(f)
        total_races = sum(len(e.get('races', [])) for e in data)
        print(f"\n✅ Final: {len(data)} events, {total_races} races")
        print(f"📁 {nat_json}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
