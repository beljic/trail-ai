#!/usr/bin/env python3
"""
Pre-Scraping Priprema

Automatski backup postojećih podataka i priprema za scraping.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

def backup_data():
    """Backup postojeće podatke pre scraping-a."""
    
    print("=" * 70)
    print("🔄 PRE-SCRAPING PRIPREMA")
    print("=" * 70)
    
    data_dir = Path("/var/www/html/trail-ai/data")
    export_dir = data_dir / "export"
    clean_dir = data_dir / "clean"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Backup races.json
    races_json = export_dir / "races.json"
    if races_json.exists():
        backup_path = export_dir / f"races_backup_{timestamp}.json"
        shutil.copy2(races_json, backup_path)
        print(f"\n✅ Backup JSON: {backup_path.name}")
        
        # Load i prikaži statistiku
        with open(races_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"   📊 Stara statistika:")
        print(f"      - Eventi: {data['metadata'].get('total_events', 0)}")
        print(f"      - Trke: {data['metadata'].get('total_races', 0)}")
        print(f"      - Izvozeno: {data['metadata'].get('exported', 'N/A')}")
    else:
        print("\n⚠️ races.json ne postoji - prviput pokretanje")
    
    # 2. Backup races.jsonl
    races_jsonl = clean_dir / "races.jsonl"
    if races_jsonl.exists():
        backup_path = clean_dir / f"races_backup_{timestamp}.jsonl"
        shutil.copy2(races_jsonl, backup_path)
        print(f"\n✅ Backup JSONL: {backup_path.name}")
        
        # Count lines
        with open(races_jsonl, 'r', encoding='utf-8') as f:
            line_count = sum(1 for line in f if line.strip())
        print(f"   📊 Broj evenata: {line_count}")
    else:
        print("\n⚠️ races.jsonl ne postoji - prviput pokretanje")
    
    # 3. Backup geocoded
    races_geocoded = clean_dir / "races_geocoded.jsonl"
    if races_geocoded.exists():
        backup_path = clean_dir / f"races_geocoded_backup_{timestamp}.jsonl"
        shutil.copy2(races_geocoded, backup_path)
        print(f"\n✅ Backup Geocoded: {backup_path.name}")
    
    # 4. Proveri prostor na disku
    print(f"\n💾 Prostor na disku:")
    total_size = 0
    for file in export_dir.glob("*"):
        if file.is_file():
            total_size += file.stat().st_size
    print(f"   Export folder: {total_size / 1024 / 1024:.2f} MB")
    
    # 5. Preporuke
    print(f"\n💡 PREPORUKE:")
    print(f"   1. Pokreni scraper: python scrape_all.py")
    print(f"   2. Ili full scrape: python scrape_all.py --all")
    print(f"   3. Analiziraj rezultate: python analyze_scrape_results.py")
    print(f"   4. Uporedi sa backup-om:")
    print(f"      python analyze_scrape_results.py --compare \\")
    print(f"        {export_dir}/races_backup_{timestamp}.json \\")
    print(f"        {export_dir}/races.json")
    
    # 6. Cleanup starih backup-ova (drži samo zadnjih 5)
    print(f"\n🧹 Cleanup starih backup-ova...")
    all_backups = sorted(export_dir.glob("races_backup_*.json"))
    if len(all_backups) > 5:
        for old_backup in all_backups[:-5]:
            old_backup.unlink()
            print(f"   🗑️ Obrisan: {old_backup.name}")
    
    print("\n" + "=" * 70)
    print("✅ Priprema završena! Spremno za scraping.")
    print("=" * 70)


if __name__ == "__main__":
    backup_data()
