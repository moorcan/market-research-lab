# Validation evidence

Validated in the Linux cloud workspace using Python 3.12.14. Windows commands are documented but have not been executed on a Windows host.

- `python -m pytest -q`: **15 passed**, including both strategies' future invariance, next-session gap execution, missing-session and malformed-bar rejection, fees/spread/slippage, cash/position limits, zero-volume rejection with expiry, flat-price independent closed-form accounting, realized/unrealized reconciliation, immutable DuckDB/Parquet roundtrip, provenance preservation, mocked provider pagination, event first-public availability/deduplication, all dashboard sections without credentials, and a labeled synthetic-fixture dashboard run.
- `python -m pip check`: no broken requirements.
- `python -m market_lab --help`: CLI entry point works.
- `git diff --check`: passed.
- Streamlit starts on loopback; UI is exercised with Streamlit AppTest. Browser smoke-test outcome is recorded below.

Fixtures and mocked HTTP responses are **development tests only**, not genuine market observations, investment findings or alpha evidence. No performance claim is made from those runs.

Alpaca market-data keys were absent (presence checked without printing values). Genuine provider retrieval is **unrun**, not passed. No real-market strategy results were generated. Windows-host validation, raw-price corporate actions, external reference-engine comparison, walk-forward/final holdout validation, and persistent forward paper trading remain unfinished. See RESEARCH.md for the full boundary and roadmap.

Browser smoke check: **passed** with Playwright using system Chromium (`/usr/bin/chromium`). Verified the rendered research-only warning, Strategy Lab's no-data state and Event Intelligence's explicit unfinished status. Playwright's bundled browser was initially absent; selecting the installed system Chromium resolved it. Screenshot retained outside the repository at `/tmp/market-lab-browser.png`.

The fully pinned lockfile was reinstalled successfully in the current virtual environment; dependency consistency still passed. This verifies refresh in this instance, not installation on a fresh Windows machine.
