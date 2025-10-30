# Trail Race Scraper

Minimalan ali kvalitetan scraping pipeline za trail trke. Ovaj projekat je fokusiran **SAMO na scraping i normalizaciju** podataka u JSONL format.

## Šta projekat radi

✅ Skrejpuje trail trke sa više izvora (trenutno **samo trka.rs**, runtrace.net pauziran)
✅ Fetchuje detail stranice za svaki event i ekstraktuje:
   - Pojedinačne trke (jedan event može imati više trka različitih distanci)
   - Lokaciju
   - Organizatora
   - Registration URL
   - Distance (parsira iz teksta poput "[27.0 km]")
✅ Normalizuje podatke u standardizovan format (Pydantic model)
✅ Deduplikuje trke po jedinstvenom ID-u
✅ Piše rezultate u `data/clean/races.jsonl` (UTF-8 JSONL format)
✅ Robusno rukovanje: retry logika, UA rotacija, rate limiting

## Dodatne funkcionalnosti

✅ PostgreSQL baza podataka za čuvanje trka (videti [DATABASE.md](DATABASE.md))

## Šta projekat NE radi (van opsega)

❌ Nema vektorske baze (Chroma)
❌ Nema LLM/RAG funkcionalnosti
❌ Nema API servera ili UI-a
❌ Nema autentikacije ili složenog logovanja

Ove funkcionalnosti će biti dodate u narednim fazama.

## Brzi start

### Preduslovi

- Docker i Docker Compose instalirani

### ⚠️ Testni mod

Scraper je trenutno u **testnom modu** i ograničen na **3 eventa po URL-u** (ukupno ~6 evenata).

Da bi skrejpovao sve trke:
1. Otvori `scrapers/trka_rs.py`
2. Promeni `MAX_EVENTS_PER_URL = 3` u `MAX_EVENTS_PER_URL = None`
3. Rebuild Docker image

### Pokretanje

```bash
# 1. Build Docker image
docker compose build

# 2. Pokreni scraper
docker compose run --rm scraper
```

Ili koristi Makefile:

```bash
make build
make run
```

### Izlazni fajl

Nakon pokretanja, rezultati se nalaze u:

```
data/clean/races.jsonl
```

**Format:** UTF-8 JSONL (jedan JSON objekat po liniji)

**Primer:**

```jsonl
{"id":"a1b2c3d4e5f67890","name":"Povlen Trail - Red Race 27km","date":"2025-10-19","country":"Serbia","region":null,"location":"Мравињци","distance_km":27.0,"elevation_m":null,"terrain":null,"website":"https://www.trka.rs/events/760-povlen-trail/","registration_url":"https://www.instagram.com/westserbiatrails/","fee_eur":null,"cutoff":null,"organizer":"SU West Trails Vlasinska 2 Valjevo 14000","source":"trka.rs","event_url":"https://www.trka.rs/events/760-povlen-trail/","race_url":"https://www.trka.rs/races/1829-povlen-trail-red-race-27km/"}
{"id":"b2c3d4e5f6789012","name":"Povlen Trail - Blue Race 18km","date":"2025-10-19","country":"Serbia","region":null,"location":"Мравињци","distance_km":18.0,"elevation_m":null,"terrain":null,"website":"https://www.trka.rs/events/760-povlen-trail/","registration_url":"https://www.instagram.com/westserbiatrails/","fee_eur":null,"cutoff":null,"organizer":"SU West Trails Vlasinska 2 Valjevo 14000","source":"trka.rs","event_url":"https://www.trka.rs/events/760-povlen-trail/","race_url":"https://www.trka.rs/races/1830-povlen-trail-blue-race-18km/"}
```

Napomena: **Jedan event može imati više trka** (npr. Povlen Trail ima 4 distanci: 27km, 18km, 12km, 10km). Svaka trka postaje zaseban JSON objekat sa istim `event_url` ali različitim `race_url`.

## Struktura projekta

```
trail-scraper/
├── common/                  # Zajedničke utilities
│   ├── __init__.py
│   ├── model.py            # Pydantic Race model
│   ├── normalize.py        # Parsing funkcije (datum, razdaljina, D+)
│   └── fetch.py            # HTTP sa retry, UA rotacija, sleep
├── scrapers/               # Scraper moduli
│   ├── __init__.py
│   ├── trka_rs.py          # Scraper za trka.rs
│   └── runtrace.py         # Scraper za runtrace.net
├── scrape_all.py           # Orkestrator: poziva sve scrapere
├── data/
│   ├── raw/                # (opciono) sirovi HTML
│   └── clean/              # Izlaz: races.jsonl
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── Makefile
└── README.md
```

## Race model (schema)

Svaka trka sadrži sledeća polja:

| Polje | Tip | Opis |
|-------|-----|------|
| `id` | str | Jedinstveni ID (SHA1 hash: source\|name\|date) |
| `name` | str | Naziv trke |
| `date` | date\|null | Datum trke (ISO 8601) |
| `country` | str\|null | Država |
| `region` | str\|null | Region |
| `location` | str\|null | Lokacija/mesto |
| `distance_km` | float\|null | Razdaljina u kilometrima |
| `elevation_m` | int\|null | Pozitivna nadmorska razlika (D+) |
| `terrain` | str\|null | Tip terena (mountain, alpine, itd.) |
| `website` | HttpUrl\|null | Zvanični sajt trke |
| `registration_url` | HttpUrl\|null | Link za prijavu |
| `fee_eur` | float\|null | Kotizacija u evrima |
| `cutoff` | str\|null | Cutoff vreme |
| `organizer` | str\|null | Organizator |
| `source` | str | Izvor podataka (npr. "trka.rs") |
| `event_url` | HttpUrl\|null | URL parent eventa (glavni event) |
| `race_url` | HttpUrl\|null | URL individual trke (ako postoji) |

## Kako dodati novi izvor

### Korak 1: Kreiraj novi scraper modul

Kreiraj fajl `scrapers/novi_izvor.py`:

```python
"""Scraper for novi-izvor.com"""

import hashlib
from typing import List
from bs4 import BeautifulSoup
from common.fetch import get_safe
from common.model import Race
from common.normalize import parse_date, parse_distance_km, parse_elev_m, clean_text

SOURCE = "novi-izvor.com"
BASE_URL = "https://www.novi-izvor.com"
LIST_URL = f"{BASE_URL}/races"

def _mk_id(source: str, name: str, date_str: str) -> str:
    """Generate unique race ID."""
    composite = f"{source}|{name}|{date_str}".lower()
    return hashlib.sha1(composite.encode("utf-8")).hexdigest()[:16]

def scrape() -> List[Race]:
    """Scrape races from novi-izvor.com"""
    races = []

    try:
        print(f"Scraping {SOURCE}...")
        response = get_safe(LIST_URL)
        if not response:
            return races

        soup = BeautifulSoup(response.content, "lxml")

        # TODO: adjust selectors based on actual HTML
        race_elements = soup.select(".race-item")

        for elem in race_elements:
            try:
                # Extract and parse data
                name_elem = elem.select_one(".name")  # TODO: adjust
                # ... ostali selektori ...

                name = clean_text(name_elem.get_text() if name_elem else None)
                if not name:
                    continue

                race_id = _mk_id(SOURCE, name, date_str or "")

                race = Race(
                    id=race_id,
                    name=name,
                    # ... ostala polja ...
                    source=SOURCE,
                )

                races.append(race)

            except Exception as e:
                print(f"Error parsing race: {e}")
                continue

    except Exception as e:
        print(f"Error scraping {SOURCE}: {e}")

    return races
```

### Korak 2: Registruj scraper u orkestratoru

Otvori `scrape_all.py` i dodaj import i registraciju:

```python
# Import
from scrapers import trka_rs, runtrace, novi_izvor  # dodaj novi_izvor

# U scrape_all_sources() funkciji
scrapers = [
    trka_rs,
    runtrace,
    novi_izvor,  # dodaj ovde
]
```

### Korak 3: Testiraj

```bash
make build
make run
```

## Kako prilagoditi selektore

Trenutni scraperi (`trka_rs.py` i `runtrace.py`) sadrže **stub implementacije** sa placeholder selektorima.

Da bi prilagodio selektore za stvarni sajt:

1. **Inspekcija HTML-a:** Otvori target sajt u browseru i inspekcijom (F12) pronađi CSS selektore za elemente.

2. **Pronađi TODO komentare:** Traži `# TODO: adjust selector` u scraper fajlovima.

3. **Ažuriraj selektore:** Zameni placeholder selektore (npr. `.race-item`, `.race-name`) sa stvarnim selektorima.

**Primer:**

```python
# PRE (placeholder):
race_elements = soup.select(".race-item")  # TODO: adjust selector

# POSLE (stvarni selektor za trka.rs):
race_elements = soup.select(".event-list-item")
```

**Ključna mesta za ažuriranje:**

- `scrapers/trka_rs.py`: ✅ Ažurirano sa pravim selektorima (.event-list-item, .card-title, itd.)
- `scrapers/runtrace.py`: linija ~67 (race_elements) i selektori unutar petlje - **TREBA PRILAGODITI**

## Konfiguracija

### Podešavanje sleep delay-a

Podrazumevano, scraper čeka 800-1400ms između zahteva (politeness delay).

Da promeniš:

```yaml
# docker-compose.yml
environment:
  - SCRAPER_SLEEP_BASE_MS=1200  # 1200ms ± 25%
```

Ili direktno pri pokretanju:

```bash
docker compose run --rm -e SCRAPER_SLEEP_BASE_MS=1500 scraper
```

## Etika i robots.txt

**VAŽNO:** Pre skrejpovanja bilo kog sajta:

1. **Proveri `robots.txt`**: npr. `https://www.trka.rs/robots.txt`
2. **Poštuj rate limiting**: projekat već implementira politeness delay
3. **Ne preopterećuj server**: koristi razumne intervale između zahteva

Trenutno projekat **ne parsira** `robots.txt` automatski - to je odgovornost korisnika.

## Održavanje

### Brisanje izlaznog fajla

```bash
make clean
```

### Rebuild (posle izmena koda)

```bash
make build
make run
```

### Debug

Ako želiš da vidiš detaljan output:

```bash
docker compose run --rm scraper
```

Output prikazuje:
- Broj pronađenih elemenata
- Greške pri parsiranju
- Ukupan broj skrejpovanih trka
- Broj unique trka nakon deduplikacije

## AI i RAG funkcionalnosti ✨

✅ **Chroma vektorska baza** - semantička pretraga trka
✅ **Ollama LLM integracija** - lokalni AI modeli
✅ **RAG sistem** - kombinacija pretrage i generacije
✅ **Chat interface** - konverzacijski AI asistent
✅ **REST API** - HTTP endpoints za AI funkcionalnosti

### Brzo pokretanje AI funkcionalnosti

```bash
# 1. Pokretanje baze i importovanje podataka
make db-up
make db-import

# 2. Kreiranje embeddings-a (jednom)
docker compose run --rm scraper python embed_races.py

# 3. Pokretanje API servera
docker compose up -d api

# 4. Testiranje
curl http://localhost:8000/health
```

### API endpointi

- **Chat**: `POST /chat` - Razgovor sa AI asistentom
- **Pretraga**: `POST /query` - RAG upiti o trkama  
- **Preporuke**: `POST /recommendations` - Personalizovane preporuke
- **Analiza**: `POST /analyze` - Analiza podataka o trkama
- **Docs**: `http://localhost:8000/docs` - Swagger dokumentacija

### Primeri korišćenja

**Chat sa AI asistentom:**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Preporuči mi trail trku u Srbiji za početnike"}'
```

**Pretraga trka:**
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "trail race 10km Serbia", "n_results": 5}'
```

**Analiza podataka:**
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '"Koja je prosečna distanca trail trka u bazi?"'
```

## Sledeće faze (TODO)

- [ ] Admin UI za pregled i upravljanje trkama
- [ ] Napredni filtering i sortiranje
- [ ] Notifikacije za nove trke
- [ ] Social features (reviews, ratings)

## Licenca

MIT (ili po potrebi)

## Autor

Trail AI Team
