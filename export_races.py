#!/usr/bin/env python3
"""
Export races.jsonl to various formats (CSV, SQL, etc) for database import.

Usage:
    python export_races.py --csv
    python export_races.py --sql
    python export_races.py --json
    python export_races.py --all
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import date, datetime


INPUT_FILE = Path("data/clean/races.jsonl")
EXPORT_DIR = Path("data/export")


def load_races():
    """Load all events and races from races.jsonl."""
    events = []
    races = []
    
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found")
        return [], []
    
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event_data = json.loads(line)
                    events.append(event_data)
                    
                    # Extract races from event
                    for race_data in event_data.get('races', []):
                        race_data['_event_id'] = event_data.get('id')
                        race_data['_event_name'] = event_data.get('name')
                        race_data['_event_date'] = event_data.get('date')
                        races.append(race_data)
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not parse line: {e}")
                    continue
    except Exception as e:
        print(f"Error reading {INPUT_FILE}: {e}")
        return [], []
    
    return events, races


def export_csv(events, races):
    """Export races to CSV format."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    events_file = EXPORT_DIR / "events.csv"
    races_file = EXPORT_DIR / "races.csv"
    
    # Export events
    if events:
        with open(events_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                'id', 'name', 'date', 'country', 'region', 'location',
                'latitude', 'longitude', 'organizer', 'contact_email',
                'website', 'image_url', 'source', 'event_url',
                'description', 'fee_rsd', 'fee_eur'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(events)
        print(f"✓ Exported {len(events)} events to {events_file}")
    
    # Export races
    if races:
        with open(races_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                'id', 'event_id', 'name', 'distance_km', 'elevation_m',
                'race_type', 'terrain', 'fee_eur', 'fee_rsd', 'cutoff',
                'race_url', 'source', 'description', 'organizer',
                'contact_email', 'participants',
                '_event_id', '_event_name', '_event_date'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(races)
        print(f"✓ Exported {len(races)} races to {races_file}")


def export_sql(events, races):
    """Export races to SQL INSERT statements."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    sql_file = EXPORT_DIR / "races.sql"
    
    with open(sql_file, "w", encoding="utf-8") as f:
        f.write("-- Trail AI Races Database Import\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Events: {len(events)}\n")
        f.write(f"-- Races: {len(races)}\n\n")
        
        # Events table
        f.write("-- Events\n")
        for event in events:
            f.write(_build_event_insert(event))
        
        f.write("\n-- Races\n")
        # Races table
        for race in races:
            f.write(_build_race_insert(race))
    
    print(f"✓ Exported {len(events)} events and {len(races)} races to {sql_file}")


def _build_event_insert(event):
    """Build SQL INSERT statement for event."""
    fields = [
        'id', 'name', 'date', 'country', 'region', 'location',
        'latitude', 'longitude', 'organizer', 'contact_email',
        'website', 'image_url', 'source', 'event_url', 'description',
        'registration_opens', 'registration_closes', 'more_details',
        'fee_rsd', 'fee_eur'
    ]
    
    values = []
    for field in fields:
        val = event.get(field)
        if val is None:
            values.append("NULL")
        elif isinstance(val, str):
            # Escape single quotes
            escaped = val.replace("'", "''")
            values.append(f"'{escaped}'")
        elif isinstance(val, (int, float)):
            values.append(str(val))
        elif isinstance(val, bool):
            values.append("1" if val else "0")
        else:
            values.append(f"'{str(val)}'")
    
    fields_str = ", ".join(fields)
    values_str = ", ".join(values)
    
    return f"INSERT INTO events ({fields_str}) VALUES ({values_str});\n"


def _build_race_insert(race):
    """Build SQL INSERT statement for race."""
    fields = [
        'id', 'event_id', 'name', 'distance_km', 'elevation_m',
        'race_type', 'terrain', 'fee_eur', 'fee_rsd', 'cutoff',
        'race_url', 'source', 'description', 'organizer', 'contact_email', 'participants'
    ]
    
    values = []
    for field in fields:
        val = race.get(field)
        if val is None:
            values.append("NULL")
        elif isinstance(val, str):
            escaped = val.replace("'", "''")
            values.append(f"'{escaped}'")
        elif isinstance(val, (int, float)):
            values.append(str(val))
        elif isinstance(val, bool):
            values.append("1" if val else "0")
        else:
            values.append(f"'{str(val)}'")
    
    fields_str = ", ".join(fields)
    values_str = ", ".join(values)
    
    return f"INSERT INTO races ({fields_str}) VALUES ({values_str});\n"


def export_json(events, races):
    """Export to structured JSON format."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_file = EXPORT_DIR / "races.json"
    
    data = {
        "metadata": {
            "exported": datetime.now().isoformat(),
            "total_events": len(events),
            "total_races": len(races),
            "sources": list(set(e.get('source') for e in events if e.get('source')))
        },
        "events": events,
        "races": races
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Exported to {output_file}")


def backup_jsonl():
    """Create backup of races.jsonl."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    backup_file = EXPORT_DIR / f"races_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    
    if INPUT_FILE.exists():
        import shutil
        shutil.copy(INPUT_FILE, backup_file)
        print(f"✓ Backup created: {backup_file}")
    else:
        print(f"Warning: {INPUT_FILE} not found, skipping backup")


def main():
    parser = argparse.ArgumentParser(
        description="Export races.jsonl to various database import formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python export_races.py --csv      # Export to CSV files
  python export_races.py --sql      # Export to SQL INSERT statements
  python export_races.py --json     # Export to JSON
  python export_races.py --all      # Export all formats + backup
  
Output files are saved to: data/export/
        """
    )
    parser.add_argument("--csv", action="store_true", help="Export to CSV")
    parser.add_argument("--sql", action="store_true", help="Export to SQL")
    parser.add_argument("--json", action="store_true", help="Export to JSON")
    parser.add_argument("--all", action="store_true", help="Export all formats and backup")
    parser.add_argument("--backup", action="store_true", help="Backup races.jsonl")
    
    args = parser.parse_args()
    
    # If no format specified, show help
    if not any([args.csv, args.sql, args.json, args.all, args.backup]):
        parser.print_help()
        return 1
    
    print("="*60)
    print("Trail AI - Export Races")
    print("="*60)
    print()
    
    # Load data
    print("Loading races.jsonl...")
    events, races = load_races()
    print(f"Loaded: {len(events)} events, {len(races)} races")
    print()
    
    if not events and not races:
        print("No data to export")
        return 1
    
    # Export based on arguments
    if args.all:
        export_csv(events, races)
        export_sql(events, races)
        export_json(events, races)
        backup_jsonl()
    else:
        if args.csv:
            export_csv(events, races)
        if args.sql:
            export_sql(events, races)
        if args.json:
            export_json(events, races)
        if args.backup:
            backup_jsonl()
    
    print()
    print(f"Export directory: {EXPORT_DIR.resolve()}")
    print("="*60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
