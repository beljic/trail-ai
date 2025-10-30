#!/usr/bin/env python3
"""
Import races from JSONL file to PostgreSQL database.

Usage:
    python import_to_db.py [--file path/to/races.jsonl]
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2.extras import execute_values


def get_db_connection():
    """Create and return a PostgreSQL database connection."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "traildb"),
        user=os.getenv("DB_USER", "trailuser"),
        password=os.getenv("DB_PASSWORD", "trailpass"),
    )


def parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO timestamp string to datetime object."""
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def import_races_from_jsonl(jsonl_path: str, batch_size: int = 100) -> dict:
    """
    Import races from JSONL file to PostgreSQL database.

    Args:
        jsonl_path: Path to the JSONL file
        batch_size: Number of records to insert at once

    Returns:
        Dictionary with statistics (inserted, updated, errors)
    """
    stats = {"inserted": 0, "updated": 0, "errors": 0, "skipped": 0}

    if not Path(jsonl_path).exists():
        print(f"ERROR: File not found: {jsonl_path}")
        sys.exit(1)

    conn = get_db_connection()
    cur = conn.cursor()

    # SQL for inserting/updating races
    insert_sql = """
        INSERT INTO races (
            id, name, date, country, region, location,
            latitude, longitude, distance_km, elevation_m,
            race_type, terrain, website, registration_url,
            contact_email, registration_opens, registration_closes,
            fee_eur, fee_rsd, cutoff, organizer, source,
            event_url, race_url
        ) VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            date = EXCLUDED.date,
            country = EXCLUDED.country,
            region = EXCLUDED.region,
            location = EXCLUDED.location,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            distance_km = EXCLUDED.distance_km,
            elevation_m = EXCLUDED.elevation_m,
            race_type = EXCLUDED.race_type,
            terrain = EXCLUDED.terrain,
            website = EXCLUDED.website,
            registration_url = EXCLUDED.registration_url,
            contact_email = EXCLUDED.contact_email,
            registration_opens = EXCLUDED.registration_opens,
            registration_closes = EXCLUDED.registration_closes,
            fee_eur = EXCLUDED.fee_eur,
            fee_rsd = EXCLUDED.fee_rsd,
            cutoff = EXCLUDED.cutoff,
            organizer = EXCLUDED.organizer,
            source = EXCLUDED.source,
            event_url = EXCLUDED.event_url,
            race_url = EXCLUDED.race_url,
            updated_at = CURRENT_TIMESTAMP
        RETURNING (xmax = 0) AS inserted;
    """

    batch = []
    line_num = 0

    print(f"Starting import from: {jsonl_path}")

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line_num += 1
                line = line.strip()
                if not line:
                    continue

                try:
                    race = json.loads(line)

                    # Prepare values tuple
                    values = (
                        race.get("id"),
                        race.get("name"),
                        race.get("date"),
                        race.get("country"),
                        race.get("region"),
                        race.get("location"),
                        race.get("latitude"),
                        race.get("longitude"),
                        race.get("distance_km"),
                        race.get("elevation_m"),
                        race.get("race_type"),
                        race.get("terrain"),
                        race.get("website"),
                        race.get("registration_url"),
                        race.get("contact_email"),
                        parse_timestamp(race.get("registration_opens")),
                        parse_timestamp(race.get("registration_closes")),
                        race.get("fee_eur"),
                        race.get("fee_rsd"),
                        race.get("cutoff"),
                        race.get("organizer"),
                        race.get("source"),
                        race.get("event_url"),
                        race.get("race_url"),
                    )

                    batch.append(values)

                    # Execute batch insert when batch size is reached
                    if len(batch) >= batch_size:
                        try:
                            results = execute_values(
                                cur, insert_sql, batch, fetch=True
                            )
                            for (is_insert,) in results:
                                if is_insert:
                                    stats["inserted"] += 1
                                else:
                                    stats["updated"] += 1
                            conn.commit()
                            batch = []
                            print(f"Processed {line_num} lines... (Inserted: {stats['inserted']}, Updated: {stats['updated']})")
                        except Exception as e:
                            print(f"ERROR on batch ending at line {line_num}: {e}")
                            conn.rollback()
                            stats["errors"] += len(batch)
                            batch = []

                except json.JSONDecodeError as e:
                    print(f"ERROR parsing JSON on line {line_num}: {e}")
                    stats["errors"] += 1
                except Exception as e:
                    print(f"ERROR processing line {line_num}: {e}")
                    stats["errors"] += 1

        # Insert remaining batch
        if batch:
            try:
                results = execute_values(cur, insert_sql, batch, fetch=True)
                for (is_insert,) in results:
                    if is_insert:
                        stats["inserted"] += 1
                    else:
                        stats["updated"] += 1
                conn.commit()
            except Exception as e:
                print(f"ERROR on final batch: {e}")
                conn.rollback()
                stats["errors"] += len(batch)

    finally:
        cur.close()
        conn.close()

    return stats


def main():
    """Main entry point."""
    # Default path to JSONL file
    jsonl_path = "data/clean/races.jsonl"

    # Allow override from command line
    if len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print(__doc__)
            sys.exit(0)
        elif sys.argv[1] == "--file" and len(sys.argv) > 2:
            jsonl_path = sys.argv[2]
        else:
            jsonl_path = sys.argv[1]

    print("=" * 60)
    print("Trail AI - JSONL to PostgreSQL Import")
    print("=" * 60)

    # Test database connection
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"Connected to: {version}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        print("\nMake sure PostgreSQL is running and environment variables are set:")
        print("  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD")
        sys.exit(1)

    # Import races
    stats = import_races_from_jsonl(jsonl_path)

    print("=" * 60)
    print("Import completed!")
    print(f"  Inserted: {stats['inserted']}")
    print(f"  Updated:  {stats['updated']}")
    print(f"  Errors:   {stats['errors']}")
    print("=" * 60)

    # Show summary from database
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM races;")
        total = cur.fetchone()[0]
        print(f"\nTotal races in database: {total}")

        cur.execute("""
            SELECT country, COUNT(*)
            FROM races
            WHERE country IS NOT NULL
            GROUP BY country
            ORDER BY COUNT(*) DESC;
        """)
        print("\nRaces by country:")
        for country, count in cur.fetchall():
            print(f"  {country}: {count}")

        cur.execute("""
            SELECT source, COUNT(*)
            FROM races
            GROUP BY source
            ORDER BY COUNT(*) DESC;
        """)
        print("\nRaces by source:")
        for source, count in cur.fetchall():
            print(f"  {source}: {count}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"ERROR getting summary: {e}")


if __name__ == "__main__":
    main()
