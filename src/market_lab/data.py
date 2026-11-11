from dataclasses import dataclass, asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
import json
import os
import duckdb
import numpy as np
import pandas as pd
import requests
import exchange_calendars as xcals

UNIVERSE = ("SPY", "QQQ", "IWM", "TLT", "GLD", "XLF", "XLK")

@dataclass(frozen=True)
class Provenance:
    provider: str
    dataset: str
    coverage: str
    adjustment: str
    retrieved_at: str
    limitations: str
    fixture: bool = False
    request_start: str | None = None
    request_end: str | None = None
    source_url: str | None = None
    symbol: str | None = None

class PriceProvider(Protocol):
    def fetch(self, symbol: str, start: str, end: str) -> tuple[pd.DataFrame, Provenance]: ...

def validate(frame, start=None, end=None):
    required = ["open", "high", "low", "close", "volume"]
    if frame.empty or not set(required).issubset(frame.columns):
        raise ValueError("Empty data or missing OHLCV columns")
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is not None:
        raise ValueError("Use timezone-naive session dates, not publication timestamps")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("Duplicate or unordered sessions")
    values = frame[required].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (frame[required[:4]] <= 0).any().any() or (frame.volume < 0).any():
        raise ValueError("Invalid price or volume")
    if ((frame.high < frame[["open", "close", "low"]].max(axis=1)) | (frame.low > frame[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("Inconsistent OHLC")
    calendar = xcals.get_calendar("XNYS")
    expected = calendar.sessions_in_range(start or frame.index.min(), end or frame.index.max()).tz_localize(None)
    if not frame.index.equals(expected):
        raise ValueError("Missing or unexpected trading sessions; never fill prices silently")
    return frame

class AlpacaDaily:
    """Read-only IEX daily bars. No trading endpoint or order API."""
    def fetch(self, symbol, start, end, *, adjustment="all"):
        if adjustment not in ("all", "raw"):
            raise ValueError("Only all or raw adjustment is supported")
        if symbol not in UNIVERSE:
            raise ValueError("MVP supports the documented ETF universe only")
        headers = {"APCA-API-KEY-ID": os.environ["APCA_API_KEY_ID"], "APCA-API-SECRET-KEY": os.environ["APCA_API_SECRET_KEY"]}
        params = {"timeframe": "1Day", "start": start + "T00:00:00Z", "end": end + "T23:59:59Z", "adjustment": adjustment, "feed": "iex", "limit": 10000}
        rows = []
        while True:
            response = requests.get(f"https://data.alpaca.markets/v2/stocks/{symbol}/bars", headers=headers, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            rows.extend(payload.get("bars", []))
            token = payload.get("next_page_token")
            if not token:
                break
            params["page_token"] = token
        if not rows:
            raise ValueError("Provider returned no bars")
        frame = pd.DataFrame(rows).rename(columns={"o":"open", "h":"high", "l":"low", "c":"close", "v":"volume"})
        timestamps = pd.to_datetime(frame.pop("t"), utc=True).dt.tz_convert("America/New_York")
        local = timestamps.dt.tz_localize(None)
        if not local.eq(local.dt.normalize()).all():
            raise ValueError("Daily bar timestamps must identify New York session midnight")
        frame.index = pd.DatetimeIndex(local)
        frame = frame[["open", "high", "low", "close", "volume"]].sort_index()
        validate(frame, start, end)
        meta = Provenance("Alpaca", "stocks/v2 daily IEX", "IEX only, not consolidated SIP", adjustment, datetime.now(timezone.utc).isoformat(), ("Dividend/split-adjusted research units, NOT executable prices; no separate dividends credited. " if adjustment == "all" else "Raw IEX bars for inspection only; corporate-action ledger is not implemented. ") + "IEX volume is partial. Fixed ETF universe has selection bias.", request_start=start, request_end=end, source_url=f"https://data.alpaca.markets/v2/stocks/{symbol}/bars", symbol=symbol)
        return frame, meta

class Store:
    def __init__(self, directory="data"):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
    def save(self, symbol, frame, meta):
        if symbol not in UNIVERSE:
            raise ValueError("Unknown symbol")
        if meta.symbol is not None and meta.symbol != symbol:
            raise ValueError("Dataset symbol does not match provenance")
        meta = replace(meta, symbol=symbol)
        validate(frame)
        # Immutable versions preserve experiment inputs and provider adjustment vintages.
        import hashlib
        content = frame.to_csv().encode() + json.dumps(asdict(meta), sort_keys=True).encode()
        version = hashlib.sha256(content).hexdigest()[:20]
        path = self.root / f"{symbol}-{version}.parquet"
        frame.rename_axis("session").to_parquet(path)
        path.with_suffix(".json").write_text(json.dumps(asdict(meta), indent=2))
        with duckdb.connect(str(self.root / "catalog.duckdb")) as db:
            db.execute("CREATE TABLE IF NOT EXISTS datasets(symbol VARCHAR, version VARCHAR PRIMARY KEY, path VARCHAR, metadata VARCHAR)")
            db.execute("INSERT OR IGNORE INTO datasets VALUES (?, ?, ?, ?)", [symbol, version, str(path.resolve()), json.dumps(asdict(meta))])
        return version
    def versions(self):
        if not (self.root / "catalog.duckdb").exists():
            return pd.DataFrame(columns=["symbol", "version", "path", "metadata"])
        with duckdb.connect(str(self.root / "catalog.duckdb"), read_only=True) as db:
            return db.execute("SELECT * FROM datasets ORDER BY rowid DESC").df()
    def load(self, version):
        rows = self.versions()
        row = rows.loc[rows.version == version].iloc[0]
        frame = pd.read_parquet(row.path)
        validate(frame)
        meta = Provenance(**json.loads(row.metadata))
        if meta.symbol is None:
            meta = replace(meta, symbol=row.symbol)
        elif meta.symbol != row.symbol:
            raise ValueError("Catalog symbol does not match provenance")
        return frame, meta


def require_adjusted_provenance(provenance):
    """Do not mix smoke-test raw quotes into the adjusted-unit simulator."""
    if provenance.adjustment != "all":
        raise ValueError("Only adjustment=all datasets can enter exploratory backtests; executable-price simulation is not implemented")
