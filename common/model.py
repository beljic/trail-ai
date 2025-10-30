"""Pydantic model for normalized race data."""

from datetime import date as DateType, datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, ConfigDict, field_serializer


class Race(BaseModel):
    """Normalized race model."""

    # Use ConfigDict for Pydantic v2
    model_config = ConfigDict(
        # Allow arbitrary types if needed
        arbitrary_types_allowed=False,
    )

    id: str
    name: str
    date: Optional[DateType] = None
    country: Optional[str] = None
    region: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    elevation_m: Optional[int] = None
    race_type: Optional[str] = None  # e.g., "Trail", "Polumaraton", "Ultra"
    terrain: Optional[str] = None
    website: Optional[HttpUrl] = None
    registration_url: Optional[HttpUrl] = None
    contact_email: Optional[str] = None
    registration_opens: Optional[datetime] = None
    registration_closes: Optional[datetime] = None
    fee_eur: Optional[float] = None
    fee_rsd: Optional[float] = None
    cutoff: Optional[str] = None
    organizer: Optional[str] = None
    source: str  # e.g., "trka.rs", "runtrace.net"

    # Additional URLs for traceability
    event_url: Optional[HttpUrl] = None  # URL of parent event (e.g., /events/760-povlen-trail/)
    race_url: Optional[HttpUrl] = None   # URL of individual race (e.g., /races/1829-povlen-trail-red-race-27km/)

    # Custom serializers for Pydantic v2
    @field_serializer('date')
    def serialize_date(self, dt: Optional[DateType], _info):
        """Serialize date to ISO format string."""
        if dt:
            return dt.isoformat()
        return None

    @field_serializer('registration_opens', 'registration_closes')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """Serialize datetime to ISO format string."""
        if dt:
            return dt.isoformat()
        return None

    @field_serializer('website', 'registration_url', 'event_url', 'race_url')
    def serialize_url(self, url: Optional[HttpUrl], _info):
        """Serialize HttpUrl to string."""
        if url:
            return str(url)
        return None
