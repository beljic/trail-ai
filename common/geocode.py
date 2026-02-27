"""Geocoding utilities to convert locations to latitude/longitude."""

import time
from typing import Optional, Tuple
import requests


# Cache to avoid repeated geocoding requests
_GEOCODE_CACHE = {}


def geocode_location(location: str, country: str = "Serbia") -> Tuple[Optional[float], Optional[float]]:
    """
    Convert location name to latitude/longitude using Nominatim (OpenStreetMap).
    
    Args:
        location: Location name (e.g., "Beograd", "Ivanjica")
        country: Country name (default: "Serbia")
        
    Returns:
        Tuple of (latitude, longitude) or (None, None) if geocoding fails
    """
    if not location:
        return None, None
    
    location = location.strip()
    
    # Check cache first
    cache_key = f"{location}|{country}"
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key]
    
    try:
        # Use Nominatim API (free, OpenStreetMap)
        query = f"{location}, {country}"
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 1
        }
        
        headers = {
            "User-Agent": "TrailAI/1.0 (https://trail-ai.rs)"
        }
        
        # Politeness: respect rate limit (1 req/sec)
        time.sleep(1.1)
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        results = response.json()
        if results:
            lat = float(results[0].get('lat'))
            lng = float(results[0].get('lon'))
            
            # Cache result
            _GEOCODE_CACHE[cache_key] = (lat, lng)
            return lat, lng
        
        # Cache negative result too
        _GEOCODE_CACHE[cache_key] = (None, None)
        return None, None
        
    except Exception as e:
        print(f"Geocoding failed for '{location}': {e}")
        _GEOCODE_CACHE[cache_key] = (None, None)
        return None, None


def clear_geocode_cache():
    """Clear geocoding cache."""
    global _GEOCODE_CACHE
    _GEOCODE_CACHE = {}


def get_cache_stats():
    """Get geocoding cache statistics."""
    return {
        "cached_locations": len(_GEOCODE_CACHE),
        "cache": _GEOCODE_CACHE
    }
