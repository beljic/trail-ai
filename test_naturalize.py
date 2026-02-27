#!/usr/bin/env python3
"""
Test the naturalization script with sample data.
"""

import json
from pathlib import Path
from naturalize_data import DataNaturalizer

def create_test_data():
    """Create a small sample dataset for testing."""
    test_data = [
        {
            "id": "test123",
            "name": "Zlatibor Ultra Trail",
            "date": "2026-06-15",
            "country": "Serbia",
            "region": "Zlatibor",
            "location": "Zlatibor",
            "organizer": "Trail Running Klub doo Beograd",
            "source": "trka.rs",
            "event_url": "https://trka.rs/event/zlatibor-ultra-trail",
            "description": "Zlatibor Ultra Trail je trka koja se održava na Zlatiboru. Trka ima tri distance: 50km, 30km i 15km. Start je u 8:00 ujutru. Sve distance prolaze kroz prelepe planinske predele. Ucesnici imaju mogucnost da uzivaju u najlepsem pogledu.",
            "image_url": "https://example.com/images/zlatibor.jpg",
            "races": [
                {
                    "id": "race1",
                    "event_id": "test123",
                    "name": "Ultra",
                    "distance_km": 50.0,
                    "elevation_gain_m": 2500,
                    "terrain": "trail",
                    "description": "Ultra trka od 50 kilometara sa 2500 metara uspona. Trka prolazi kroz najlepse delove Zlatibora. Starni paket ukljucuje majcu, medalju i hranu. Idealna za iskusne ucesnike.",
                    "organizer": "TRK doo",
                    "source": "trka.rs",
                    "race_url": "https://trka.rs/event/zlatibor-ultra-trail/ultra"
                },
                {
                    "id": "race2",
                    "event_id": "test123",
                    "name": "Middle Distance",
                    "distance_km": 30.0,
                    "elevation_gain_m": 1500,
                    "terrain": "trail",
                    "description": "Srednja distanca od 30km sa 1500m D+. Idealna za pocetnike u ultra trkama. Ucesnici dobijaju startni paket koji ukljucuje sve potrebno.",
                    "organizer": "Planinarski klub Zlatibor ad",
                    "source": "trka.rs",
                    "race_url": "https://trka.rs/event/zlatibor-ultra-trail/middle"
                }
            ]
        }
    ]
    
    return test_data

def main():
    """Run test."""
    print("🧪 Testing naturalization script\n")
    
    # Create test data
    test_file = Path("data/test_naturalize.json")
    test_data = create_test_data()
    
    print("📝 Creating test data...")
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Created test file: {test_file}\n")
    
    # Test without AI first (fast)
    print("=" * 60)
    print("TEST 1: Without AI (fast mode)")
    print("=" * 60)
    
    naturalizer = DataNaturalizer(use_ai=False)
    output_file = Path("data/test_naturalized_no_ai.json")
    naturalizer.naturalize_file(test_file, output_file)
    
    # Show results
    print("\n" + "=" * 60)
    print("RESULTS (No AI):")
    print("=" * 60)
    
    with open(output_file, 'r', encoding='utf-8') as f:
        naturalized = json.load(f)
    
    event = naturalized[0]
    print(f"\nEvent name: {event['name']}")
    print(f"Organizer: {event['organizer']}")
    print(f"Image URL: {event['image_url']}")
    print(f"\nRace 1 name: {event['races'][0]['name']}")
    print(f"Race 1 organizer: {event['races'][0]['organizer']}")
    print(f"Race 2 organizer: {event['races'][1]['organizer']}")
    
    # Test with AI (if available)
    print("\n\n" + "=" * 60)
    print("TEST 2: With AI (reformulation)")
    print("=" * 60)
    
    naturalizer_ai = DataNaturalizer(use_ai=True)
    output_file_ai = Path("data/test_naturalized_with_ai.json")
    
    if naturalizer_ai.use_ai:
        naturalizer_ai.naturalize_file(test_file, output_file_ai)
        
        print("\n" + "=" * 60)
        print("RESULTS (With AI):")
        print("=" * 60)
        
        with open(output_file_ai, 'r', encoding='utf-8') as f:
            naturalized_ai = json.load(f)
        
        event_ai = naturalized_ai[0]
        print(f"\nOriginal description:")
        print(f"  {test_data[0]['description']}")
        print(f"\nReformulated description:")
        print(f"  {event_ai['description']}")
        
        print(f"\n\nOriginal race description:")
        print(f"  {test_data[0]['races'][0]['description']}")
        print(f"\nReformulated race description:")
        print(f"  {event_ai['races'][0]['description']}")
    else:
        print("⚠️ AI not available, skipping AI test")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    print(f"\nTest files created:")
    print(f"  - {test_file}")
    print(f"  - {output_file}")
    if naturalizer_ai.use_ai:
        print(f"  - {output_file_ai}")

if __name__ == '__main__':
    main()
