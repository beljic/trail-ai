# Backup Pre Upgrade - 11. februar 2026

**Backup kreiran:** 11. februar 2026  
**Razlog:** Čišćenje pre novog scrape-a sa poboljšanim funkcionalnostima

---

## 📦 Šta Je Sačuvano

### Export Fajlovi
- `races.json` (425 KB) - Glavni JSON export (71 event, 157 trka)
- `races_all.json` (153 KB) - Alternativna verzija
- `runtrace.json` (51 KB) - Samo runtrace izvor
- `races_backup_*.jsonl` - Stari backup-ovi
- `events.csv` - Eventi u CSV formatu
- `races.csv` - Trke u CSV formatu
- `races.sql` - SQL dump

### Clean Fajlovi
- `races.jsonl` (187 KB) - Raw JSONL data
- `races_geocoded.jsonl` (187 KB) - Sa koordinatama

---

## 📊 Statistika Starih Podataka

- **Eventi:** 71
- **Trke:** 157
- **Izvori:** trka.rs (47), runtrace.net (24)
- **Datum scrape-a:** 15. januar 2026
- **Vremenski raspon:** Januar - Decembar 2026

---

## ⚠️ Šta Je Nedostajalo

Stari podaci **nemaju**:
- ❌ Image URLs (0%)
- ❌ Elevation/D+ (0%)
- ❌ Registration URLs (0%)
- ❌ Descriptions (0%)
- ❌ Timestamp tracking (scraped_at, last_updated)

---

## 🔄 Restore Procedura

Ako treba da vratiš stare podatke:

```bash
cd /var/www/html/trail-ai

# Vrati sve export fajlove
cp data/backups/pre_upgrade_20260211/races*.json data/export/
cp data/backups/pre_upgrade_20260211/*.csv data/export/
cp data/backups/pre_upgrade_20260211/*.sql data/export/

# Vrati clean fajlove
cp data/backups/pre_upgrade_20260211/races.jsonl data/clean/
cp data/backups/pre_upgrade_20260211/races_geocoded.jsonl data/clean/
```

---

## 📝 Napomene

- Backup je bezbedan - svi fajlovi su sačuvani
- Prostor oslobođen: ~1 MB
- Novi scrape će kreirati nove, poboljšane fajlove
- Ovaj backup može biti obrisan nakon potvrde da novi scrape radi

---

**Status:** ✅ Backup kompletan, spremno za novi scrape!
