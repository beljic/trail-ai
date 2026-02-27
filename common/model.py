"""Pydantic models for normalized race data."""

from datetime import date as DateType, datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, ConfigDict, field_serializer


class Event(BaseModel):
    """Trail running event (parent)."""

    model_config = ConfigDict(
        arbitrary_types_allowed=False,
    )

    id: str  # SHA1 hash
    name: str
    date: Optional[DateType] = None
    country: Optional[str] = None
    region: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    organizer: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[HttpUrl] = None
    image_url: Optional[HttpUrl] = None
    source: str  # e.g., "trka.rs"
    event_url: HttpUrl  # Unique per source
    description: Optional[str] = None
    registration_opens: Optional[datetime] = None
    registration_closes: Optional[datetime] = None
    more_details: Optional[str] = None
    fee_rsd: Optional[float] = None
    fee_eur: Optional[float] = None
    runners_stats: Optional[dict] = None
    races: Optional[List["Race"]] = None
    
    # Timestamp tracking for incremental scraping
    scraped_at: Optional[datetime] = None  # First time scraped
    last_updated: Optional[datetime] = None  # Last time data was updated
    last_check: Optional[datetime] = None  # Last time we checked the source

    @field_serializer('date')
    def serialize_date(self, dt: Optional[DateType], _info):
        """Serialize date to ISO format string."""
        if dt:
            return dt.isoformat()
        return None
    
    @field_serializer('scraped_at', 'last_updated', 'last_check', 'registration_opens', 'registration_closes')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """Serialize datetime to ISO format string."""
        if dt:
            return dt.isoformat()
        return None

    @field_serializer('website', 'image_url', 'event_url')
    def serialize_event_url(self, url: Optional[HttpUrl], _info):
        """Serialize HttpUrl to string."""
        if url:
            return str(url)
        return None


class Race(BaseModel):
    """Trail running race variant (child of Event)."""

    model_config = ConfigDict(
        arbitrary_types_allowed=False,
    )

    id: str  # SHA1 hash
    event_id: str  # Foreign key to parent event
    name: str
    distance_km: Optional[float] = None
    elevation_m: Optional[int] = None
    race_type: Optional[str] = None
    terrain: Optional[str] = None
    registration_url: Optional[HttpUrl] = None
    fee_eur: Optional[float] = None
    fee_rsd: Optional[float] = None
    cutoff: Optional[str] = None
    race_url: Optional[HttpUrl] = None
    source: str  # e.g., "trka.rs"
    description: Optional[str] = None
    organizer: Optional[str] = None
    contact_email: Optional[str] = None
    participants: Optional[int] = None  # Number of participants for this race
    
    # Timestamp tracking for incremental scraping
    scraped_at: Optional[datetime] = None  # First time scraped
    last_updated: Optional[datetime] = None  # Last time data was updated

    @field_serializer('registration_url', 'race_url')
    def serialize_race_url(self, url: Optional[HttpUrl], _info):
        """Serialize HttpUrl to string."""
        if url:
            return str(url)
        return None

# Forward reference fix for Event.races
Event.model_rebuild()

# Forward reference fix for Event.races
Event.model_rebuild()
