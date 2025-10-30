"""Normalization and parsing utilities for race data."""

import re
from datetime import date
from typing import Optional
from dateutil import parser as date_parser


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """
    Parse date string into date object.

    Handles various date formats, prioritizing day-first parsing (European style).

    Args:
        date_str: String containing date (e.g., "15.05.2025", "15/05/2025", "2025-05-15")

    Returns:
        Parsed date object or None if parsing fails

    Examples:
        >>> parse_date("15.05.2025")
        date(2025, 5, 15)
        >>> parse_date("15/05/2025")
        date(2025, 5, 15)
        >>> parse_date("invalid")
        None
    """
    if not date_str or not isinstance(date_str, str):
        return None

    try:
        # dayfirst=True for European date format (DD.MM.YYYY)
        parsed = date_parser.parse(date_str.strip(), dayfirst=True)
        return parsed.date()
    except (ValueError, TypeError, date_parser.ParserError):
        return None


def parse_distance_km(distance_str: Optional[str]) -> Optional[float]:
    """
    Parse distance string into kilometers as float.

    Handles various formats like "27 km", "27km", "27.5 KM", "42K", etc.

    Args:
        distance_str: String containing distance

    Returns:
        Distance in kilometers as float, or None if parsing fails

    Examples:
        >>> parse_distance_km("27 km")
        27.0
        >>> parse_distance_km("27.5km")
        27.5
        >>> parse_distance_km("42K")
        42.0
    """
    if not distance_str or not isinstance(distance_str, str):
        return None

    try:
        # Remove common words and normalize
        text = distance_str.lower().strip()

        # Look for patterns like "27 km", "27.5km", "42K"
        # Match: optional digits, decimal point, digits, optional space, km/k
        pattern = r'(\d+(?:\.\d+)?)\s*k(?:m)?'
        match = re.search(pattern, text)

        if match:
            return float(match.group(1))

        return None
    except (ValueError, AttributeError):
        return None


def parse_elev_m(elevation_str: Optional[str]) -> Optional[int]:
    """
    Parse elevation gain string into meters as integer.

    Handles various formats like "850 m", "D+ 850", "850m", "850 meters", etc.

    Args:
        elevation_str: String containing elevation gain

    Returns:
        Elevation gain in meters as integer, or None if parsing fails

    Examples:
        >>> parse_elev_m("850 m")
        850
        >>> parse_elev_m("D+ 850")
        850
        >>> parse_elev_m("1250 meters")
        1250
    """
    if not elevation_str or not isinstance(elevation_str, str):
        return None

    try:
        # Remove common prefixes and normalize
        text = elevation_str.lower().strip()

        # Remove common prefixes like "d+", "d-", "elevation:"
        text = re.sub(r'^(d[+-]|elevation|elev)[\s:]*', '', text)

        # Look for patterns like "850 m", "850m", "850 meters"
        # Match: digits, optional space, optional m/meters/metre
        pattern = r'(\d+)\s*(?:m(?:et(?:er|re)s?)?)?'
        match = re.search(pattern, text)

        if match:
            return int(match.group(1))

        return None
    except (ValueError, AttributeError):
        return None


def clean_text(text: Optional[str]) -> Optional[str]:
    """
    Clean and normalize text fields.

    Args:
        text: Raw text string

    Returns:
        Cleaned text or None if empty
    """
    if not text or not isinstance(text, str):
        return None

    # Strip whitespace and normalize
    cleaned = ' '.join(text.strip().split())

    return cleaned if cleaned else None
