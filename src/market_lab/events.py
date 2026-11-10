"""Timestamp-safe contracts for public news and disclosure research; no live ingestion yet."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

@dataclass(frozen=True)
class PublicEvent:
    source_id: str
    source_url: str
    category: str
    symbol: str
    occurred_at: datetime
    published_at: datetime
    ingested_at: datetime
    description: str
    transaction_code: str | None = None
    timestamp_uncertainty: timedelta = timedelta(0)
    def __post_init__(self):
        if any(t.tzinfo is None or t.utcoffset() is None for t in (self.occurred_at,self.published_at,self.ingested_at)):
            raise ValueError("Event timestamps must include timezone")
        if self.timestamp_uncertainty < timedelta(0) or not self.source_url.startswith("https://"):
            raise ValueError("Invalid provenance")
    @property
    def available_at(self):
        return max(self.published_at,self.ingested_at) + self.timestamp_uncertainty
    @property
    def open_market_purchase(self):
        return self.category == "sec_form4" and self.transaction_code == "P"

class NewsProvider(Protocol):
    def events(self, start: datetime, end: datetime) -> list[PublicEvent]: ...

def known_events(events, decision_time):
    if decision_time.tzinfo is None:
        raise ValueError("Decision time must include timezone")
    unique = {}
    for event in events:
        if event.available_at <= decision_time:
            key = (event.source_id, event.source_url)
            unique[key] = event
    return sorted(unique.values(), key=lambda e: e.available_at)
