# Opt-in Alpaca genuine-data smoke test

This procedure checks the **read-only market-data adapter**, not profitability, execution realism, corporate-action ledger correctness, or brokerage connectivity. Ordinary pytest and GitHub Actions use explicitly synthetic fixtures/mocked HTTP, require no keys, and do not run this command.

## Prerequisites and safe credentials

1. Install Python 3.12 dependencies using README.md. Use an Alpaca market-data subscription/entitlement with IEX historical bars access. Do not supply Robinhood credentials or connect any real financial account. If credential provisioning requires an unwanted brokerage connection, stop and use a separate permitted market-data source instead.
2. Supply `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` through the local process environment or an approved secret manager. Request market-data-only/read-only credentials where supported. The code itself uses only GET requests to `https://data.alpaca.markets/v2/stocks/{symbol}/bars`; it never tests account or order endpoints. Do not assume that an API key's existence makes it read-only at the provider.
3. Never put credentials in source, GitHub issues, command arguments, reports or committed `.env` files. Do not run shell tracing or dump environment values. In GitHub Actions, do not add these keys: CI stays offline.
4. The runtime's egress policy must permit **data.alpaca.markets**. That domain is not included in this cloud environment's current package-manager preset. Add that exact hostname in environment settings if performing the live check here; do not disable TLS verification or broaden network access to all hosts.

## Run from the repository root

After credentials are securely set in the current process, use this completed range spanning the March 2024 daylight-saving transition, Good Friday market holiday, and a period to investigate SPY dividend adjustment:

```powershell
.\.venv\Scripts\python.exe -m market_lab.smoke --symbol SPY --start 2024-03-01 --end 2024-04-05 --evidence reports/alpaca-smoke.json
$LASTEXITCODE
```

Linux equivalent:

```sh
python -m market_lab.smoke --symbol SPY --start 2024-03-01 --end 2024-04-05 --evidence reports/alpaca-smoke.json
```

The command makes two paginated market-data retrievals: `feed=iex`, `timeframe=1Day`, one `adjustment=raw` and one `adjustment=all`. It does not cache raw bars into the backtest catalog or generate strategy returns. The evidence is saved under Git-ignored `reports/`; use a distinct filename to retain each run.

## Required evidence and interpretation

- XNYS calendar equality across the **entire requested range**, not just the returned endpoints. Expected: 25 sessions, first March 1, last April 5; no weekends or March 29. Missing first, interior or last sessions, extra sessions, duplicates, invalid OHLCV and nonfinite values fail the check. IEX missing bars are a failure to investigate, never a reason to fill synthetic prices.
- The adapter converts bar timestamps from UTC to America/New_York and requires local midnight before extracting session dates. The range exercises both EST and EDT. Calendar session dates are not timestamps when information first became public.
- Raw and adjusted datasets must cover identical sessions. The report lists OHLC differences, observed price-ratio bounds and volume differences. A nonzero difference establishes only that the two provider requests produced different series. Do not assume an adjustment direction, volume adjustment, or exact dividend amount without the provider's conventions and independent corporate-action evidence.
- Provenance must include provider, dataset, partial IEX exchange coverage, explicit `raw`/`all` adjustment, timezone-aware retrieval time, requested bounds, original data endpoint, limitations and `fixture=false`. SHA-256 digests identify returned normalized datasets. Reports never include request headers or credential values.
- Before declaring **adjustment accounting verified**, independently obtain an authoritative dated split/dividend record and provider methodology, retain source links and retrieval date locally, and reconcile factors on and around the action date. Check ex-date vs pay date, split ratio, adjusted volume convention and the provider's adjustment anchor. This reconciliation is manual and **not performed by the command**. Do not substitute an assumed dividend or force a numeric match. Future corporate-action ledger work needs separate fixtures and accounting tests.

Exit status:

| Code | Meaning |
| --- | --- |
| 0 | `passed_provider_checks`: session, OHLCV, provenance and observed raw-vs-adjusted difference checks passed; manual action reconciliation remains required. |
| 1 | `failed`: malformed data, missing sessions, request/authentication/network failure or other validation error. Only the exception type is emitted, to keep credentials and server bodies out of evidence. |
| 2 | `blocked_missing_credentials` or `inconclusive_adjustment`: not a pass. Identical series do not prove adjustment correctness; investigate historical range and provider methodology. |

Record the command, exit code, evidence file, current Git commit, Python version and the manual reconciliation outcome. An entitlement error does not justify switching feed silently. Report provider limitations and blocked/unrun checks separately from passing offline tests.

## Current review outcome

Both required variable names were checked and are absent; no secret values were inspected. The command returned `blocked_missing_credentials` (exit 2) in this review. No authenticated Alpaca request was made, and genuine-data/adjustment checks remain **unverified**. The smoke harness itself is covered by offline tests, which are not live-data evidence.
