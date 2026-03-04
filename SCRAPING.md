# Scraping Workflow

**OBAVEZNO: Inkrementalni scraping je implementiran i mora se koristiti!**

## TL;DR

```bash
# Inkrementalno - samo nove trke (PREPORUČENO)
python3 scrape_all.py

# Full - sve iznova
python3 scrape_all.py --all
```

## Detaljno

### 1. Inkrementalni scraping (Preporučeno)

```bash
python3 scrape_all.py
```

**Šta radi:**
- Čita `data/clean/races.jsonl` i zna koje trke već ima
- **Preskače** već skrapovane event URL-e (`existing_urls`)
- **Preskače** već skrapovane race ID-e (`existing_ids`)
- **Dodeljuje** samo NOVE race objekte na kraj JSONL fajla (`append=True`)
- Brže je jer ne predownloaduje stare podatke

**Output:**
```
data/clean/races.jsonl  (old races + new races appended)
```

**Kada koristiti:**
- Daily scheduled runs (novi evenati se dodaju)
- After new sports websites added
- Regular updates

---

### 2. Full scrape (Overwrite mode)

```bash
python3 scrape_all.py --all
```

**Šta radi:**
- Skrapuje SVE sources opet (`existing_ids = None`)
- **Prebrisuje** `data/clean/races.jsonl` sa novim podacima
- Deduplikuje novoizgrađene podatke
- Sporije, ali čini kompletan refresh

**Output:**
```
data/clean/races.jsonl  (completely new file)
```

**Kada koristiti:**
- Početna inicijalizacija
- Posle ažuriranja scraper koda (fix bugs, dodaj nove sources)
- Kada trebate čist dataset

---

## Izvora (Sources)

### 1. Custom Site Scrapers

Lokacija: `scrapers/custom/*.py`

URLs (iz `scrape_all.py`):
```python
CUSTOM_EVENT_URLS = [
    "https://bjelasicatrail.me/",
    "https://visitbjelasnica.com/vucko-trail-2025/",
    "https://vuckotrail.ba/",
    "https://timisoara.21k.ro/curse/?lang=en",
]
```

**Obrada:** HTML parsing sa BeautifulSoup  
**Brzina:** ~1-2 sec po event-u  
**Status:** ✅ Radi

---

### 2. trka.rs

**URL:** https://trka.rs/events

**Obrada:** 
- Parsira listu sa ~76 evenata
- Fetchuje detail stranicu za SVAKI event (SPORO!)
- Ekstraktuje multiple race distances iz tog event-a
- Geocoduje lokaciju

**Brzina:** ~5-10 minuta (76 evenata × ~5 sec/event + geocoding)

**Status:** ✅ Radi  
**Issues:**  
- ⚠️ **Geocoding timeouts** (DNSPython na spore internete)  
- ⚠️ **Rate limiting** (biti pažljiv sa broj zahteva)

**Fix ako timeout-a:**
```python
# scrapers/trka_rs.py, line ~50
GEOCODE_TIMEOUT = 20  # Porasti sa 10 na 20 sekundi
```

---

### 3. runtrace.net

**URL:** https://www.runtrace.net

**Obrada:**
- **JavaScript rendering** - koristi Selenium WebDriver
- Parsira sve evente sa stranice
- Fetchuje detaljne informacije

**Brzina:** ~15-30 minuta (runtrace liste su veće, Selenium je spora)

**Status:** ❓ Pauziran (ne testiran u full mod-u)  
**Issues:**  
- ⚠️ **Selenium je BAJNA spora** (2-3 sec po event-u)
- ⚠️ Browser timeouts
- ⚠️ Chrome/Chromium dependency

**Aktivirati runtrace:**

U `scrape_all.py`, line ~225:

```python
# SADA:
if False:  # runtrace (disabled - too slow)
    source_events, source_races = runtrace.scrape()

# TREBALO BI:
if True:  # runtrace (enabled)
    source_events, source_races = runtrace.scrape()
```

---

## Output

### data/clean/races.jsonl

- **Format:** JSONL (jedan JSON objekat po liniji)
- **Encoding:** UTF-8
- **Struktura:** Flat – **Jedan race po liniji**, NE events sa nested races

```jsonl
{"id":"a1b2c3d4","name":"Povlen Trail - 27km","distance_km":27.0,"event_id":"event-123","source":"trka.rs",...}
{"id":"b2c3d4e5","name":"Povlen Trail - 18km","distance_km":18.0,"event_id":"event-123","source":"trka.rs",...}
```

**Zašto JSONL sa flat strukturom?**
- ✅ Jedan race per linija = lako append u inkrementalnom modu
- ✅ Lako deduplicate po `id`
- ✅ Kompatibilno sa BigQuery, Pandas, streaming procesima

---

### data/export/races.json

Kreira se iz `data/clean/races.jsonl` sa:
```bash
python3 run_pipeline.py
```

- **Format:** JSON array
- **Struktura:** Nested – **Events sa nested races**

```json
[
  {
    "id": "event-123",
    "name": "Povlen Trail",
    "source": "trka.rs",
    "races": [
      {"id": "a1b2c3d4", "name": "27km", "distance_km": 27.0},
      {"id": "b2c3d4e5", "name": "18km", "distance_km": 18.0}
    ]
  }
]
```

---

### data/export/races_naturalized.json

Final output za import u drugi sistem.

**Transformacije:**
- ✅ Image dimensions + query params (`?w=800&h=600`)
- ✅ Description reformulation
- ✅ Company name normalization (`d.o.o`, `doo`)
- ✅ Grammar/diacritics fixes

**Komande za generisanje:**
```bash
# Fast - bez AI
python3 run_pipeline.py

# Sa AI opisima (SPORIJE)
python3 run_pipeline.py --with-ai
```

---

## Workflow: Od scraping-a do importa

### 1. Inkrementalni scrape (svakodnevno)

```bash
python3 scrape_all.py
```

Output: `data/clean/races.jsonl` sa NOVIM race objektima appended-enim

---

### 2. Export i naturalize

```bash
python3 run_pipeline.py
```

Šta radi:
```
data/clean/races.jsonl (flat, all races)
    ↓ export_to_json()
data/export/races.json (nested, events with races)
    ↓ naturalize_data.py
data/export/races_naturalized.json (final for import)
```

---

### 3. Import u drugi sistem

```bash
# Prebriši races u svom sistemu
DELETE FROM races WHERE 1=1;

# Učitaj iz JSON-a
python3 import_from_json.py data/export/races_naturalized.json
```

---

## Greške i kako ih rešiti

### ❌ `geocode_location timeout`

```
ssl.py: wrap_socket timeout
KeyboardInterrupt
```

**Uzrok:** Geocoding API (OpenStreetMap) sporo odgovara

**Rešenje 1 - Povećaj timeout:**
```python
# scrapers/trka_rs.py, line ~50
GEOCODE_TIMEOUT = 20  # umesto 10
```

**Rešenje 2 - Skip geocoding:**
```python
# common/geocode.py, line ~15
SKIP_GEOCODING = True  # Preskočiti geocoding, koristiti None za lat/lon
```

**Rešenje 3 - Retry sa exponential backoff:**
Već je implementirao u `common/fetch.py`:
```python
@retry(max_retries=3, backoff=2)
def requests.get(...)
```

---

### ❌ `Selenium timeout` (runtrace)

```
WebDriverException: timeout at...
```

**Uzrok:** Runtrace JavaScript loaders su spora, browser ne render-uje

**Rešenje:**
```python
# scrapers/runtrace.py, line ~40
IMPLICIT_WAIT = 20  # umesto 10 sekundi
```

---

### ❌ `Rate limiting` (trka.rs blocks requests)

```
HTTP 429 Too Many Requests
```

**Uzrok:** Skrapujete brže nego što trka.rs dozvoljava

**Rešenje:**
```python
# scrapers/trka_rs.py, line ~60
SLEEP_BETWEEN_REQUESTS = 2  # dodaj pauzu između requests-a
```

---

### ❌ `Duplicate races`

```
Race ID: 'abc123' already exists, skipping...
```

**Uzrok:** Isti race skrapovan iz dva izvora

**Auto-deduplicate:**
```bash
python3 << 'EOF'
import json
from pathlib import Path

races = []
seen_ids = set()
with open('data/clean/races.jsonl', encoding='utf-8') as f:
    for line in f:
        r = json.loads(line)
        if r['id'] not in seen_ids:
            seen_ids.add(r['id'])
            races.append(r)

# Rewrite
Path('data/clean/races.jsonl').unlink()  # delete
with open('data/clean/races.jsonl', 'w', encoding='utf-8') as f:
    for r in races:
        f.write(json.dumps(r) + '\n')

print(f"✅ Deduplicated: {len(races)} unique races")
EOF
```

---

## Status Quo (March 4, 2026)

```
data/clean/races.jsonl:
  - 4 custom events (12+4+8+4 = 28 races)
  - 59 trka.rs events (~150+ races)
  - 0 runtrace events (NIJE SKRAPOVANO)
  
  = ~63 evenata, ~195 races
```

**Šta trebam da dodam za runtrace:**
1. Uključi `if True:` za runtrace u `scrape_all.py` line 225
2. Testiraj da li Selenium driver startuje
3. Monitor timeouts
4. Prirodno će biti + 20-30 events sa runtrace-a

---

## Checklist za Production

Kad trebate deployovati full pipeline:

- [ ] Test `python3 scrape_all.py` na dev okruženju
- [ ] Proverite `data/clean/races.jsonl` je validna
- [ ] Testirajte `python3 run_pipeline.py`
- [ ] Proverite JSON output je valid: `jq . data/export/races_naturalized.json > /dev/null`
- [ ] Deployuj u production
- [ ] Setup daily cron job za `scrape_all.py` (inkrementalno)

**Cron job primer:**
```bash
# /etc/cron.d/trail-ai-scraper
0 3 * * * cd /var/www/html/trail-ai && source venv/bin/activate && python3 scrape_all.py >> logs/scraper.log 2>&1
```

---

## FAQ

**P: Koliko često trebam da skrapujem?**  
Ž: Svakodnevno inkrementalno (`python3 scrape_all.py`). Full scrape samo kad trebate refresh.

**P: Da li mogu da dodam novi izvor?**  
Ž: Da! Kreiraj `scrapers/custom/my_site.py` sa `@register_scraper("domain.com")`, onda dodaj URL u `CUSTOM_EVENT_URLS`.

**P: Šta ako trebam samo konkretne izvore?**  
Ž: Prosledi `--only-custom`, `--only-trka`, `--only-runtrace` u `scrape_all.py` arg parser (NIJE IMPLEMENTIRANO - može se dodati).

**P: Mogu li da skinim stare race-ove?**  
Ž: `rm data/clean/races.jsonl && python3 scrape_all.py --all` = čist start.

