# PostgreSQL Baza Podataka - Uputstvo

## Kratak pregled

Trail AI sada podržava čuvanje podataka u PostgreSQL bazi. Podaci se mogu skrepovati u JSONL fajl (`data/clean/races.jsonl`) i zatim importovati u bazu podataka.

## Brzo pokretanje

```bash
# 1. Pokrenuti PostgreSQL bazu
make db-up

# 2. Importovati podatke iz JSONL fajla
make db-import

# 3. Pristupiti bazi (psql shell)
make db-shell
```

## Komande

### Pokretanje i zaustavljanje

```bash
# Pokrenuti PostgreSQL
make db-up

# Zaustaviti sve servise (scraper + PostgreSQL)
make db-down

# Videti logove baze
make db-logs
```

### Import podataka

```bash
# Importovati data/clean/races.jsonl u bazu
make db-import

# Ili direktno sa Docker Compose
docker compose run --rm scraper python import_to_db.py
```

### Rad sa bazom

```bash
# Otvoriti PostgreSQL shell (psql)
make db-shell

# Resetovati bazu (BRIŠE SVE PODATKE!)
make db-reset
```

## SQL primeri

Kada ste u `psql` shell-u (preko `make db-shell`):

```sql
-- Broj svih trka
SELECT COUNT(*) FROM races;

-- Trke po zemljama
SELECT country, COUNT(*)
FROM races
WHERE country IS NOT NULL
GROUP BY country;

-- Nadolazeće trail trke u Srbiji
SELECT name, date, location, distance_km, website
FROM races
WHERE country = 'Serbia'
  AND race_type = 'Trail'
  AND date >= CURRENT_DATE
ORDER BY date
LIMIT 10;

-- Trke sa GPS koordinatama
SELECT name, location, latitude, longitude
FROM races
WHERE latitude IS NOT NULL
  AND longitude IS NOT NULL;

-- Prosečna distanca po tipu trke
SELECT race_type,
       COUNT(*) as broj_trka,
       ROUND(AVG(distance_km), 2) as prosecna_distanca_km
FROM races
WHERE race_type IS NOT NULL
GROUP BY race_type
ORDER BY broj_trka DESC;
```

## Konfiguracija

PostgreSQL parametri se nalaze u `docker-compose.yml`:

```yaml
POSTGRES_DB: traildb
POSTGRES_USER: trailuser
POSTGRES_PASSWORD: trailpass
```

Ove vrednosti se mogu promeniti pre prvog pokretanja.

## Šema baze

Tabela `races` ima sledeća polja:

- `id` - Unique ID (SHA1 hash)
- `name` - Naziv trke
- `date` - Datum trke
- `country`, `region`, `location` - Lokacija
- `latitude`, `longitude` - GPS koordinate
- `distance_km` - Distanca u kilometrima
- `elevation_m` - Pozitivna nadmorska razlika (D+)
- `race_type` - Tip trke (Trail, Marathon, Ultra, itd.)
- `terrain` - Teren (Trail, Road, Mixed)
- `website`, `registration_url` - Web linkovi
- `contact_email` - Kontakt email
- `registration_opens`, `registration_closes` - Datum otvaranja/zatvaranja prijava
- `fee_eur`, `fee_rsd` - Cena u EUR/RSD
- `organizer` - Organizator
- `source` - Izvor podataka (npr. "trka.rs")
- `event_url`, `race_url` - URL-ovi
- `created_at`, `updated_at` - Timestamp-ovi

Detaljna šema je u `db/init.sql`.

## Pristup bazi izvan Docker-a

Ako želite pristupiti bazi iz lokalnog alata (DBeaver, pgAdmin, itd.):

```
Host: localhost
Port: 5432
Database: traildb
Username: trailuser
Password: trailpass
```

## Upsert logika

Import skript koristi `ON CONFLICT DO UPDATE` - ako trka sa istim ID-jem već postoji, podaci će biti ažurirani umesto da se kreira duplikat.

## Troubleshooting

**Problem:** "Could not connect to database"
**Rešenje:** Proverite da li je PostgreSQL pokrenut sa `make db-up`

**Problem:** Import ne radi
**Rešenje:** Proverite da li fajl `data/clean/races.jsonl` postoji

**Problem:** Želim da počnem ispočetka
**Rešenje:** Koristite `make db-reset` da obrišete sve podatke
