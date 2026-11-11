"""Opt-in genuine-data validation. GET daily bars only; never trading APIs.

Run explicitly with market-data credentials; ordinary pytest and CI stay offline.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from .data import AlpacaDaily, UNIVERSE, validate
from .serialization import dumps


def check_provider(provider, symbol, start, end):
    expected = xcals.get_calendar("XNYS").sessions_in_range(start, end).tz_localize(None)
    frames, provenance, hashes = {}, {}, {}
    for adjustment in ("raw", "all"):
        frame, meta = provider.fetch(symbol, start, end, adjustment=adjustment)
        validate(frame, start, end)
        if not frame.index.equals(expected):
            raise ValueError("Provider session range differs from XNYS")
        retrieved = datetime.fromisoformat(meta.retrieved_at)
        if (meta.fixture or meta.provider != "Alpaca" or meta.adjustment != adjustment
                or meta.request_start != start or meta.request_end != end
                or meta.source_url != f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
                or "IEX" not in meta.coverage or not meta.dataset or not meta.limitations
                or retrieved.tzinfo is None or retrieved.utcoffset() is None):
            raise ValueError("Missing or inconsistent genuine-data provenance")
        frames[adjustment] = frame
        provenance[adjustment] = asdict(meta)
        hashes[adjustment] = hashlib.sha256(frame.to_csv().encode()).hexdigest()
    columns = ["open", "high", "low", "close"]
    raw = frames["raw"][columns].to_numpy()
    adjusted = frames["all"][columns].to_numpy()
    changed = ~np.isclose(raw, adjusted, rtol=1e-7, atol=1e-8).all(axis=1)
    ratios = adjusted / raw
    return {
        "status": "passed_provider_checks" if changed.any() else "inconclusive_adjustment",
        "scope": "read-only IEX daily data checks; not a strategy result or executable-price validation",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol, "requested_range": [start, end],
        "calendar": "XNYS", "session_timezone": "America/New_York",
        "session_count": len(expected), "first_session": str(expected[0].date()),
        "last_session": str(expected[-1].date()),
        "missing_sessions": 0, "unexpected_sessions": 0,
        "adjustment_comparison": {
            "ohlc_changed_sessions": int(changed.sum()),
            "changed_session_dates": [str(day.date()) for day in expected[changed]],
            "adjusted_to_raw_price_ratio_min": float(ratios.min()),
            "adjusted_to_raw_price_ratio_max": float(ratios.max()),
            "volume_changed_sessions": int((frames["raw"].volume != frames["all"].volume).sum()),
            "interpretation": "Observed provider differences only; exact dividend/split factors require independent source reconciliation. Identical series are inconclusive, never proof of adjustment correctness.",
        },
        "dataset_sha256": hashes, "provenance": provenance,
        "manual_corporate_action_reconciliation": "required; not performed by this command",
        "executable_price_simulation": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", choices=UNIVERSE, default="SPY")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--evidence", default="reports/alpaca-smoke.json")
    args = parser.parse_args()
    missing = [name for name in ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY") if not os.environ.get(name)]
    if missing:
        report = {"status": "blocked_missing_credentials", "missing_variable_names": missing}
        code = 2
    else:
        try:
            start, end = pd.Timestamp(args.start), pd.Timestamp(args.end)
            today = pd.Timestamp.now(tz="America/New_York").tz_localize(None).normalize()
            if start.tzinfo is not None or end.tzinfo is not None or start > end or end >= today:
                raise ValueError("Use ordered, completed historical session dates")
            report = check_provider(AlpacaDaily(), args.symbol, start.date().isoformat(), end.date().isoformat())
            code = 0 if report["status"] == "passed_provider_checks" else 2
        except Exception as exc:
            # Never emit headers, exception text, response bodies or key values.
            report = {"status": "failed", "error_type": type(exc).__name__}
            code = 1
    evidence = Path(args.evidence)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    text = dumps(report, indent=2)
    evidence.write_text(text, encoding="utf-8")
    print(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
