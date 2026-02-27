# Izveštaj o Kvalitetu Skrapovanih Podataka
**Datum analize:** 11. februar 2026  
**Poslednje skrapovanje:** 15. januar 2026  
**Vreme od poslednjeg skrepa:** ~27 dana

---

## 📊 Opšti Pregled

- **Ukupno evenata:** 71
- **Ukupno trka:** 157 (prosek 2.2 trke po eventu)
- **Izvori:** 
  - trka.rs: 47 evenata (66.2%)
  - runtrace.net: 24 eventa (33.8%)
- **Vremenski raspon:** Januar - Decembar 2026
- **Peak sezona:** Maj 2026 (16 evenata), Mart (12), Jun (9)

---

## 🔍 Analiza Kvaliteta Podataka

### EVENTI - Nedostajući Podaci

| Polje | Popunjeno | Nedostaje | % Popunjeno |
|-------|-----------|-----------|-------------|
| **Koordinate (lat/lng)** | 62/71 | 9 | ✅ 87.3% |
| **Website** | 71/71 | 0 | ✅ 100% |
| **Contact Email** | 47/71 | 24 | ⚠️ 66.2% |
| **Registration Opens** | 47/71 | 24 | ⚠️ 66.2% |
| **Image URL** | 0/71 | 71 | ❌ 0% |
| **Description** | 0/71 | 71 | ❌ 0% |
| **Fee (RSD/EUR)** | 0/71 | 71 | ❌ 0% |

### TRKE - Nedostajući Podaci

| Polje | Popunjeno | Nedostaje | % Popunjeno |
|-------|-----------|-----------|-------------|
| **Distance (km)** | 131/157 | 26 | ✅ 83.4% |
| **Fee (EUR)** | 104/157 | 53 | ⚠️ 66.2% |
| **Terrain** | 59/157 | 98 | ❌ 37.6% |
| **Elevation (D+)** | 0/157 | 157 | ❌ 0% |
| **Registration URL** | 0/157 | 157 | ❌ 0% |

---

## ⚠️ Kritični Nedostaci

### 1. **Slike Evenata (100% nedostaje)**
- **Problem:** Nijedan event nema `image_url`
- **Uticaj:** Vizuelna prezentacija u UI je neadekvatna
- **Rešenje:** 
  - Dodati ekstrakciju `og:image` ili glavne slike iz event stranice
  - Fallback na default placeholder sliku

### 2. **Elevacija/D+ (100% nedostaje)**
- **Problem:** Nema podataka o pozitivnoj elevaciji
- **Uticaj:** Trail runneri ne mogu planirati težinu trke
- **Rešenje:**
  - Parsirati D+ iz opisa trke (često se navodi kao "D+ 1500m")
  - Ekstraktovati iz table sa detaljima trke

### 3. **Opis Eventa (100% nedostaje)**
- **Problem:** Nema tekstualnog opisa eventa
- **Uticaj:** Korisnici nemaju kontekst o trci
- **Rešenje:**
  - Ekstraktovati glavni tekst sa event stranice
  - Parsirati sekciju "O trci" ili sličnu

### 4. **Registration URL (100% nedostaje za trke)**
- **Problem:** Link za prijavu nije dostupan direktno
- **Uticaj:** Korisnici moraju ručno tražiti
- **Rešenje:**
  - Ekstraktovati "Prijavi se" button URL
  - Često je na event_url + "/register" ili sličnom

### 5. **Fee/Cena (100% nedostaje na event nivou)**
- **Problem:** Na event nivou nema cene, ali trke često imaju
- **Uticaj:** Komplikovano filtriranje po ceni
- **Rešenje:**
  - Već postoji fee ekstrakcija za pojedinačne trke
  - Event level fee može biti min/max od trka

---

## ⚡ Moguća Poboljšanja

### A) **Teren Detection**
- Trenutno: 37.6% popunjenosti
- **Implementirano:** Osnovna detekcija iz race_type (trail/road/mountain)
- **Poboljšanje:** 
  - Proširiti keywords (ultratrail, skyrace, vertical, etc)
  - Parsirati iz opisa ako race_type ne postoji

### B) **Email Ekstrakcija**
- Trenutno: 66.2% popunjenosti
- **Problem:** Neki eventi imaju email samo kao sliku ili link
- **Rešenje:**
  - OCR za email u slikama (teže)
  - Parsiranje mailto: linkova

### C) **Geocoding**
- Trenutno: 87.3% uspešnosti
- **Problem:** 9 evenata nema koordinate
- **Rešenje:**
  - Retry sa različitim formatima lokacije
  - Manuelno dodati poznate lokacije
  - Fallback na region/grad centar

---

## 🔄 Inkrementalno Skrapovanje - Trenutno Stanje

### Šta Radi ✅
```python
# Existing infrastructure:
python scrape_all.py          # Inkremental mode (preskače postojeće ID-jeve)
python scrape_all.py --all    # Full mode (sve ispočetka)
```

**Trenutna logika:**
1. ✅ Učitava postojeće race ID-jeve iz `data/clean/races.jsonl`
2. ✅ Preskače trke koje već postoje (po ID-ju)
3. ✅ Dodaje samo nove trke na kraj fajla
4. ✅ Cache za već skrapovane URL-ove

### Šta Ne Radi Dobro ❌

1. **Nema Timestamp Tracking**
   - Ne pamti se kada je event poslednji put skrapovan
   - Ne znamo da li se podaci promenili na sajtu

2. **Ne Detektuje Izmene**
   - Ako se promeni cena, datum ili lokacija - ostaje staro

3. **Ne Briše Stare Eventi**
   - Eventi iz prošlosti ostaju zauvek
   - Nema auto-cleanup starih trka

4. **Nema Last-Modified Check**
   - Ne koristi HTTP Last-Modified header
   - Uvek fetchuje HTML čak i ako nije promenjen

---

## 🎯 Plan za Inkrementalno Skrapovanje v2

### Faza 1: Dodaj Timestamp Tracking

**Šta dodati u model:**
```python
class Event(BaseModel):
    # ... existing fields ...
    scraped_at: datetime          # Kada je prvi put skrapovano
    last_updated: datetime        # Poslednja provera/update
    last_check: datetime          # Poslednji put když smo proverili sajt
    content_hash: str             # Hash HTML sadržaja za detekciju promena
```

**Export format update:**
```json
{
  "metadata": {
    "last_scrape": "2026-02-11T14:30:00",
    "next_recommended_scrape": "2026-02-18T14:30:00",
    "scrape_frequency_days": 7
  }
}
```

### Faza 2: Strategija Skrepa

**Weekly Scraping Schedule:**
```
- Ponedeljak: Full check svih izvora
- Sreda: Provera samo evenata u narednih 30 dana
- Petak: Quick check novih evenata (samo list stranice)
```

**Smart Scraping Logic:**
```python
def should_scrape_event(event: Event, today: date) -> bool:
    """Odluči da li treba ponovo skrapovati event."""
    
    # 1. Ako je event u prošlosti > 7 dana, preskači
    if event.date < today - timedelta(days=7):
        return False
    
    # 2. Ako je event u narednih 14 dana, proveri svaki dan
    if event.date < today + timedelta(days=14):
        return event.last_check < today
    
    # 3. Ako je event u narednih 30 dana, proveri svake 3 dana
    if event.date < today + timedelta(days=30):
        return event.last_check < today - timedelta(days=3)
    
    # 4. Ako je event daleko, proveri svake nedelje
    return event.last_check < today - timedelta(days=7)
```

### Faza 3: Change Detection

**HTML Content Hashing:**
```python
import hashlib

def compute_content_hash(html: str) -> str:
    """Compute SHA256 hash of relevant HTML content."""
    # Extract only relevant parts (dates, prices, descriptions)
    relevant_content = extract_event_data_section(html)
    return hashlib.sha256(relevant_content.encode()).hexdigest()

def has_changed(event: Event, new_html: str) -> bool:
    """Check if event content has changed."""
    new_hash = compute_content_hash(new_html)
    return new_hash != event.content_hash
```

### Faza 4: Database Integration

**Umesto JSONL, koristi PostgreSQL:**
```sql
ALTER TABLE events ADD COLUMN scraped_at TIMESTAMP DEFAULT NOW();
ALTER TABLE events ADD COLUMN last_updated TIMESTAMP DEFAULT NOW();
ALTER TABLE events ADD COLUMN last_check TIMESTAMP DEFAULT NOW();
ALTER TABLE events ADD COLUMN content_hash VARCHAR(64);

CREATE INDEX idx_events_date ON events(date);
CREATE INDEX idx_events_last_check ON events(last_check);
```

**Benefits:**
- Brže queries
- Efikasnije update-ovanje pojedinačnih evenata
- Lakše filtriranje starih podataka

---

## 🛠️ Akcioni Plan - Prioritet

### VISOK PRIORITET (1-2 dana)

1. **Dodaj Image Ekstrakciju**
   - Implementiraj u `scrapers/trka_rs.py`: ekstraktuj `og:image` meta tag
   - Implementiraj u `scrapers/runtrace.py`: pronađi glavnu sliku eventa
   - Update `common/model.py` da prihvata image URL
   - Test: proveri da li sve slike rade

2. **Dodaj Elevation (D+) Parsing**
   - Kreiraj `common/normalize.py::parse_elevation()` funkciju
   - Regex patterns: "D+ 1500m", "1500m D+", "elevation gain: 1500"
   - Integriši u postojeće scrapere
   - Test: proveri parsiranje različitih formata

3. **Dodaj Description Ekstrakciju**
   - Ekstraktuj glavni tekst sa event stranice
   - Limit: prvih 500 karaktera
   - Clean HTML tags i whitespace
   - Store u Event.description

### SREDNJI PRIORITET (3-5 dana)

4. **Implementiraj Timestamp Tracking**
   - Dodaj `scraped_at`, `last_updated`, `last_check` u model
   - Update scrape_all.py da popunjava ove vrednosti
   - Kreiraj `should_scrape_event()` logiku
   - Test incremental logic

5. **Dodaj Registration URL**
   - Pronađi "Prijavi se" button na stranici
   - Ekstraktuj href
   - Store per-race basis

6. **Poboljšaj Terrain Detection**
   - Proširi keyword listu
   - Fallback na opis ako race_type ne postoji

### NIZAK PRIORITET (kad ima vremena)

7. **HTML Content Hashing**
   - Implementiraj change detection
   - Skip scrape ako se HTML nije promenio

8. **Database Migration**
   - Prebaci sa JSONL na PostgreSQL
   - Indeksiraj kritična polja
   - Kreiraj migration script

9. **Auto-Cleanup Starih Evenata**
   - Arhiviraj evenimente starije od 6 meseci
   - Opciono: eksportuj u archive JSON

---

## 💡 Preporuke za Tebe

### Kako Možeš Pomoći

1. **Manuelna Validacija Parsera**
   - Otvori par event stranica (trka.rs, runtrace.net)
   - Proveri gde se nalaze slike, opisi, D+
   - Pomozi mi da napišem precizne CSS selektore

2. **Testiranje Custom Scrapers**
   - Proveri da li custom scrapers rade:
     - bjelasicatrail.me
     - vuckotrail.ba
     - ivanjicatrail (ako postoji sajt)
   - Javi ako neki ne radi

3. **Dodavanje Novih Izvora**
   - Da li postoje drugi trail race calendari za Srbiju/region?
   - Predloži URL-ove koje treba skrapovati

4. **Quality Check Postojećih Podataka**
   - Proveri par random evenata u `data/export/races.json`
   - Javi ako nešto nije tačno (datum, lokacija, ime)

---

## 🚀 Sledeći Koraci

1. **Odluči prioritete:** Šta je najbitnije za tvoj use case?
2. **Odredi frekvenciju skrapovanja:** Svaki dan? Nedelja? On-demand?
3. **Odaberi format:** Nastavi sa JSONL ili pređi na PostgreSQL?

**Kada mi kažeš šta je prioritet, mogu odmah da krenem sa implementacijom!**
