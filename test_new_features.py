#!/usr/bin/env python3
"""Quick test script for new scraper features."""

import sys
sys.path.insert(0, '/var/www/html/trail-ai')

from scrapers.trka_rs import _extract_image_url, _extract_registration_url, _extract_elevation_from_text, _determine_terrain
from common.normalize import parse_elev_m
from bs4 import BeautifulSoup

print("=" * 60)
print("Testing New Scraper Features")
print("=" * 60)

# Test terrain detection
print("\n1. Testing terrain detection:")
test_terrains = [
    ("Trail", "trail"),
    ("Ultra Trail", "trail"),
    ("Road Race", "road"),
    ("Mountain Skyrace", "mountain"),
    ("Cross Country", "cross"),
    ("Vertical Run", "vertical"),
]
for race_type, expected in test_terrains:
    result = _determine_terrain(race_type)
    status = "✅" if result == expected else "❌"
    print(f"  {status} '{race_type}' -> '{result}' (expected: '{expected}')")

# Test elevation extraction
print("\n2. Testing elevation extraction from text:")
test_elevations = [
    ("D+ 1500m trail race", 1500),
    ("Race with 850m D+ total", 850),
    ("Elevation: 1250 meters", 1250),
    ("Pozitivna uspon: 2000m", 2000),
    ("Beautiful trail, no elevation data", None),
]
for text, expected in test_elevations:
    result = _extract_elevation_from_text(text)
    status = "✅" if result == expected else "❌"
    print(f"  {status} '{text}' -> {result} (expected: {expected})")

# Test parse_elev_m
print("\n3. Testing parse_elev_m function:")
test_parse_elev = [
    ("850 m", 850),
    ("D+ 1500", 1500),
    ("1250 meters", 1250),
    ("elevation: 2000m", 2000),
]
for text, expected in test_parse_elev:
    result = parse_elev_m(text)
    status = "✅" if result == expected else "❌"
    print(f"  {status} '{text}' -> {result} (expected: {expected})")

# Test image extraction (mock HTML)
print("\n4. Testing image extraction:")
test_html_og = """
<html>
<head>
    <meta property="og:image" content="https://trka.rs/images/event123.jpg" />
</head>
<body></body>
</html>
"""
soup_og = BeautifulSoup(test_html_og, "lxml")
img_url = _extract_image_url(soup_og)
print(f"  {'✅' if img_url == 'https://trka.rs/images/event123.jpg' else '❌'} OG image extraction: {img_url}")

test_html_content = """
<html>
<body>
    <div class="content-panel">
        <img src="/images/event456.jpg" />
    </div>
</body>
</html>
"""
soup_content = BeautifulSoup(test_html_content, "lxml")
img_url2 = _extract_image_url(soup_content)
print(f"  {'✅' if 'event456.jpg' in (img_url2 or '') else '❌'} Content image extraction: {img_url2}")

# Test registration URL extraction
print("\n5. Testing registration URL extraction:")
test_html_reg = """
<html>
<body>
    <a href="/events/123/register">Prijavi se</a>
</body>
</html>
"""
soup_reg = BeautifulSoup(test_html_reg, "lxml")
reg_url = _extract_registration_url(soup_reg, "https://trka.rs/events/123")
print(f"  {'✅' if '/register' in (reg_url or '') else '❌'} Registration URL: {reg_url}")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
