#!/usr/bin/env python3
"""
Analiza Kvaliteta Podataka posle Scraping-a

Koristi se nakon scraping-a da proveri šta je novo dodato.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def analyze_data_quality(json_file: Path):
    """Analiziraj kvalitet podataka u JSON export fajlu."""
    
    print("=" * 70)
    print(f"📊 ANALIZA KVALITETA PODATAKA: {json_file.name}")
    print("=" * 70)
    
    if not json_file.exists():
        print(f"❌ Fajl ne postoji: {json_file}")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metadata = data.get('metadata', {})
    events = data.get('events', [])
    
    print(f"\n📅 Poslednji export: {metadata.get('exported', 'N/A')}")
    print(f"📊 Ukupno:")
    print(f"   - Eventi: {metadata.get('total_events', 0)}")
    print(f"   - Trke: {metadata.get('total_races', 0)}")
    print(f"   - Izvori: {', '.join(metadata.get('sources', []))}")
    
    # Analiziraj po izvorima
    by_source = defaultdict(int)
    for event in events:
        by_source[event.get('source', 'unknown')] += 1
    
    print(f"\n🌐 Distribucija po izvorima:")
    for source, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        print(f"   - {source}: {count} evenata")
    
    # Proveri nove funkcionalnosti
    print(f"\n✨ NOVE FUNKCIONALNOSTI - Uspešnost:")
    
    # 1. Images
    events_with_images = sum(1 for e in events if e.get('image_url'))
    img_pct = (events_with_images / len(events) * 100) if events else 0
    status_img = "✅" if img_pct > 50 else "⚠️" if img_pct > 20 else "❌"
    print(f"   {status_img} Slike (image_url): {events_with_images}/{len(events)} ({img_pct:.1f}%)")
    
    # 2. Descriptions
    events_with_desc = sum(1 for e in events if e.get('description'))
    desc_pct = (events_with_desc / len(events) * 100) if events else 0
    status_desc = "✅" if desc_pct > 50 else "⚠️" if desc_pct > 20 else "❌"
    print(f"   {status_desc} Opisi (description): {events_with_desc}/{len(events)} ({desc_pct:.1f}%)")
    
    # 3. Timestamps
    events_with_scraped = sum(1 for e in events if e.get('scraped_at'))
    ts_pct = (events_with_scraped / len(events) * 100) if events else 0
    status_ts = "✅" if ts_pct > 90 else "⚠️" if ts_pct > 50 else "❌"
    print(f"   {status_ts} Timestamp (scraped_at): {events_with_scraped}/{len(events)} ({ts_pct:.1f}%)")
    
    # 4. Elevacija na trke
    total_races = 0
    races_with_elevation = 0
    races_with_reg_url = 0
    
    for event in events:
        for race in event.get('races', []):
            total_races += 1
            if race.get('elevation_m'):
                races_with_elevation += 1
            if race.get('registration_url'):
                races_with_reg_url += 1
    
    elev_pct = (races_with_elevation / total_races * 100) if total_races else 0
    status_elev = "✅" if elev_pct > 40 else "⚠️" if elev_pct > 20 else "❌"
    print(f"   {status_elev} Elevacija (elevation_m): {races_with_elevation}/{total_races} ({elev_pct:.1f}%)")
    
    reg_pct = (races_with_reg_url / total_races * 100) if total_races else 0
    status_reg = "✅" if reg_pct > 60 else "⚠️" if reg_pct > 30 else "❌"
    print(f"   {status_reg} Registration URL: {races_with_reg_url}/{total_races} ({reg_pct:.1f}%)")
    
    # Proveri datume - najnoviji eventi
    print(f"\n📅 NAJNOVIJI EVENTI (sledećih 30 dana):")
    now = datetime.now().date()
    upcoming = []
    for event in events:
        date_str = event.get('date')
        if date_str:
            try:
                event_date = datetime.fromisoformat(date_str).date()
                if event_date >= now:
                    days_until = (event_date - now).days
                    if days_until <= 30:
                        upcoming.append((event_date, days_until, event.get('name'), event.get('source')))
            except:
                pass
    
    if upcoming:
        for date, days, name, source in sorted(upcoming)[:10]:
            emoji = "🔥" if days <= 7 else "📅"
            print(f"   {emoji} {date} (za {days} dana) - {name} [{source}]")
    else:
        print("   (nema evenata u narednih 30 dana)")
    
    # Proveri koje podatke još uvek nedostaju
    print(f"\n⚠️ ŠTO JOŠ NEDOSTAJE:")
    
    missing_coords = sum(1 for e in events if not e.get('latitude') or not e.get('longitude'))
    if missing_coords > 0:
        print(f"   - Koordinate: {missing_coords} evenata nema lat/lng")
    
    missing_email = sum(1 for e in events if not e.get('contact_email'))
    if missing_email > 0:
        print(f"   - Email: {missing_email} evenata nema kontakt email")
    
    missing_fee = sum(1 for e in events if not e.get('fee_rsd') and not e.get('fee_eur'))
    if missing_fee > 0:
        print(f"   - Cena: {missing_fee} evenata nema fee info")
    
    races_missing_distance = sum(1 for e in events for r in e.get('races', []) if not r.get('distance_km'))
    if races_missing_distance > 0:
        print(f"   - Distanca: {races_missing_distance} trka nema distance_km")
    
    print("\n" + "=" * 70)
    print("✅ Analiza završena!")
    print("=" * 70)


def compare_before_after(before_file: Path, after_file: Path):
    """Uporedi podatke pre i posle scraping-a."""
    
    print("\n" + "=" * 70)
    print("📊 POREĐENJE PRE I POSLE SCRAPING-A")
    print("=" * 70)
    
    if not before_file.exists():
        print(f"⚠️ 'Before' fajl ne postoji: {before_file}")
        return
    
    if not after_file.exists():
        print(f"⚠️ 'After' fajl ne postoji: {after_file}")
        return
    
    with open(before_file, 'r', encoding='utf-8') as f:
        before = json.load(f)
    
    with open(after_file, 'r', encoding='utf-8') as f:
        after = json.load(f)
    
    before_events = len(before.get('events', []))
    after_events = len(after.get('events', []))
    diff_events = after_events - before_events
    
    before_races = before.get('metadata', {}).get('total_races', 0)
    after_races = after.get('metadata', {}).get('total_races', 0)
    diff_races = after_races - before_races
    
    print(f"\n📊 Statistika:")
    print(f"   Eventi: {before_events} → {after_events} ({'+' if diff_events >= 0 else ''}{diff_events})")
    print(f"   Trke: {before_races} → {after_races} ({'+' if diff_races >= 0 else ''}{diff_races})")
    
    # Nove funkcionalnosti - before vs after
    before_imgs = sum(1 for e in before.get('events', []) if e.get('image_url'))
    after_imgs = sum(1 for e in after.get('events', []) if e.get('image_url'))
    
    before_desc = sum(1 for e in before.get('events', []) if e.get('description'))
    after_desc = sum(1 for e in after.get('events', []) if e.get('description'))
    
    before_ts = sum(1 for e in before.get('events', []) if e.get('scraped_at'))
    after_ts = sum(1 for e in after.get('events', []) if e.get('scraped_at'))
    
    print(f"\n✨ Poboljšanja:")
    if after_imgs > before_imgs:
        print(f"   ✅ Slike: {before_imgs} → {after_imgs} (+{after_imgs - before_imgs})")
    if after_desc > before_desc:
        print(f"   ✅ Opisi: {before_desc} → {after_desc} (+{after_desc - before_desc})")
    if after_ts > before_ts:
        print(f"   ✅ Timestamps: {before_ts} → {after_ts} (+{after_ts - before_ts})")


if __name__ == "__main__":
    data_dir = Path("/var/www/html/trail-ai/data/export")
    
    # Glavni JSON fajl
    races_json = data_dir / "races.json"
    
    if len(sys.argv) > 1 and sys.argv[1] == "--compare":
        # Uporedi dva fajla
        if len(sys.argv) >= 4:
            before = Path(sys.argv[2])
            after = Path(sys.argv[3])
            compare_before_after(before, after)
        else:
            print("Usage: python analyze_scrape_results.py --compare <before.json> <after.json>")
    else:
        # Analiziraj trenutno stanje
        analyze_data_quality(races_json)
        
        # Ako postoji backup, uporedi
        backups = sorted(data_dir.glob("races_backup_*.jsonl"))
        if backups:
            print(f"\n💡 Tip: Možeš uporediti sa backup-om:")
            print(f"   python analyze_scrape_results.py --compare {backups[-1]} {races_json}")
