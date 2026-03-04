#!/usr/bin/env python3
"""Quick pipeline: export JSONL → JSON → naturalize → final JSON."""

import json
import subprocess
import sys
from pathlib import Path

# Paths
JSONL_FILE = Path("data/clean/races.jsonl")
EXPORT_JSON = Path("data/export/races.json")
FINAL_JSON = Path("data/export/races_naturalized.json")

def count_events():
    """Count events in JSONL."""
    if not JSONL_FILE.exists():
        print(f"❌ {JSONL_FILE} not found")
        return 0
    
    count = 0
    with open(JSONL_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                count += 1
    return count

def export_to_json():
    """Export JSONL to JSON format for naturalize."""
    print(f"📤 Exporting {JSONL_FILE} → {EXPORT_JSON}")
    
    if not JSONL_FILE.exists():
        print(f"❌ {JSONL_FILE} not found")
        return False
    
    events = []
    with open(JSONL_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                events.append(event)
            except json.JSONDecodeError as e:
                print(f"⚠️ Skipping malformed line: {e}")
    
    # Create export directory
    EXPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    
    # Write JSON array (what naturalize_data.py expects)
    with open(EXPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Exported {len(events)} events to {EXPORT_JSON}")
    return True

def naturalize():
    """Run naturalize_data.py on exported JSON."""
    print(f"\n🔄 Naturalizing {EXPORT_JSON} → {FINAL_JSON}")
    
    try:
        result = subprocess.run([
            sys.executable,
            'naturalize_data.py',
            str(EXPORT_JSON),
            '-o', str(FINAL_JSON),
            '--no-ai'  # Fast mode without AI (synonym substitution only)
        ], check=True, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Warnings:", result.stderr)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Naturalize failed: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False

def main():
    print("=" * 60)
    print("TRAIL AI PIPELINE: Export → Naturalize → Final JSON")
    print("=" * 60)
    
    # Step 1: Count events
    count = count_events()
    print(f"\n📊 Found {count} events in {JSONL_FILE}")
    
    if count == 0:
        print("❌ No data to process")
        return 1
    
    # Step 2: Export to JSON
    if not export_to_json():
        return 1
    
    # Step 3: Naturalize
    if not naturalize():
        return 1
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE!")
    print(f"📁 Final JSON ready: {FINAL_JSON}")
    print("=" * 60)
    
    # Show file size
    if FINAL_JSON.exists():
        size_kb = FINAL_JSON.stat().st_size / 1024
        print(f"   Size: {size_kb:.1f} KB")
        
        with open(FINAL_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"   Events: {len(data)}")
            total_races = sum(len(e.get('races', [])) for e in data)
            print(f"   Races: {total_races}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
