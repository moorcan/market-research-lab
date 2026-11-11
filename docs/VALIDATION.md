# Current connection recheck and metadata retention

The user reports a working official ChatGPT Robinhood integration and a successful read-only SPY daily-price request. Current Codex verification still found **zero exposed Robinhood tools**, no managed Robinhood authorization binding, and proxy HTTP 403 CONNECT denial for the official MCP endpoint and support site. No trading/account tools were called, no connector credentials were extracted and no authenticated Robinhood response was obtained by this app. These are session-specific blockers, not a claim that the user's ChatGPT connection failed.

Latest code validation: **83 tests passed**, `pip check` passed and `git diff --check` passed. New tests verify timezone-aware provider timestamp retention across DST, session consistency, nullable interpolation flags, metadata roundtrips, version changes when flags change, rejection of malformed metadata, refusal of known interpolated bars in backtests, and comparison-report disclosure of unknown/flagged bars. Alpaca mock-adapter tests now assert preserved UTC instants and unknown interpolation status. All prices in these tests remain labeled fixtures.

Robinhood research remains the development priority, with Alpaca available as an explicit fallback. No live Robinhood adapter, data-accuracy comparison, historical coverage claim, or automated-storage permission is inferred from the ChatGPT success. The [evaluation recheck](ROBINHOOD_MCP_EVALUATION.md#recheck-after-the-successful-chatgpt-spy-request) documents supported next steps and the unverified official auth/terms requirements. The active application's read-only deny-by-default boundary is unchanged.

Earlier review evidence below is retained as implementation history; its test counts apply to those earlier revisions.

---

# Robinhood MCP candidate follow-up

This follow-up adds a provider-neutral selection/fallback boundary, an empty immutable MCP data-tool allowlist, a disabled Robinhood daily adapter, and a cached-data consistency comparison command. No production MCP authorization/HTTP transport or live tool binding is implemented. The Python application cannot inherit a Codex connector's authorization.

Current follow-up validation:

- Full offline suite: **74 passed**. Includes all prior tests plus research-operation denials, arbitrary order/account-name rejection, immutable allowlist enforcement, fixture-only argument validation before transport, opt-in fallback with honest provenance, refusal to mask data errors, instrument/adjustment comparison guards, truncated-range diagnosis, fixture-labeled comparison CLI, and dashboard refusal without silent Alpaca access.
- Dependency consistency: `pip check` passed; no dependencies added.
- Both provider-selection and comparison CLI help commands work. `git diff --check` passed.
- A direct request to the supplied Robinhood endpoint failed at the cloud egress proxy (HTTP 403 CONNECT denial). Official docs and authenticated access remain **blocked/unverified**, not failed-provider capability claims. No account data or real assets were accessed.
- The running policy has not yet shown the requested Robinhood/Alpaca domain additions. No Robinhood or Alpaca authorization is configured in this session. No genuine cross-provider comparison has run.

See [ROBINHOOD_MCP_EVALUATION.md](ROBINHOOD_MCP_EVALUATION.md) for the official-source verification matrix, exact unresolved prerequisites, app-owned authorization design and criteria for considering Robinhood primary. All currently enumerated capabilities remain denied; offline tests do not establish authenticated integration or data accuracy.

The earlier PR #1 review evidence below records checks from the preceding implementation, not live Robinhood verification.

---

# PR #1 review and validation evidence

## Findings resolved

- **One-session report failure:** sample-standard-deviation volatility was NaN and strict JSON report writing raised an exception. Metrics now return explicit null for unavailable one-session estimates; tests run both baseline strategies on one, two and five sessions and exercise saved reports, CLI and dashboard. Empty history is rejected.
- **Undefined/extreme metric handling:** zero variance/downside/drawdown and no completed exits retain undefined values rather than implying zero risk. Derived annualization overflow and nonfinite numerical values serialize as JSON null; unsupported object types still fail. Tests parse JSON with nonstandard NaN/Infinity tokens explicitly rejected.
- **Ambiguous execution claims:** dashboard, CLI and saved reports identify adjusted-price exploration. Unsupported executable-price engine modes and raw-dataset entry into the dashboard/CLI/report path are rejected. This does not implement a realistic raw-price engine.
- **Missing automation and live-data evidence procedure:** added Python 3.12 GitHub Actions dependency install, pip check and offline pytest, plus an opt-in read-only Alpaca smoke command and a manual adjustment-reconciliation checklist.

## Checks run in this review

A fresh virtual environment (`/tmp/market-lab-ci`) was created with Python 3.12.14. The same installation and validation commands used by CI were run:

```sh
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
python -m pip check
python -m pytest -q
```

- Pinned dependencies and editable package: installed successfully from scratch.
- `pip check`: no broken requirements.
- `pytest -q`: **43 passed**, with no skipped tests. Includes existing accounting/causality tests plus short datasets, undefined metrics, strict nested JSON serialization, CLI/dashboard report creation, raw-mode rejection, DST-aware adapter timestamps, complete holiday/session range checks, smoke-test provenance faults, inconclusive adjustment behavior, missing-key blocking and exception-content redaction.
- Chromium/Playwright smoke check: passed against the running Streamlit app. Verified the adjusted-price-only notice, no-data Strategy Lab refusal and explicit Event Intelligence Milestone 3 deferrals. Screenshot: `/tmp/market-lab-pr1-review-browser.png` (local validation artifact, not committed).
- `git diff --check`: passed.

All test prices and mocked provider responses are explicitly **development fixtures**. Tests and browser checks do not establish genuine-data quality, alpha, or out-of-sample performance. GitHub-hosted CI execution is separate from this local reproduction; it cannot be claimed passed without checking the hosted result. Windows-host execution remains unverified.

## Genuine-data smoke result: blocked, not passed

Executed:

```sh
python -m market_lab.smoke --symbol SPY --start 2024-03-01 --end 2024-04-05 --evidence reports/alpaca-smoke-review.json
```

Outcome: **exit 2**, `blocked_missing_credentials`. Both `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` are absent; only names/presence were inspected. No authenticated Alpaca request occurred and no real-market strategy results were generated. The current cloud network policy also does not allow `data.alpaca.markets`; that exact destination is required before a live check here. Never supply secrets in chat or commit them.

Follow [ALPACA_SMOKE_TEST.md](ALPACA_SMOKE_TEST.md) after securely provisioning read-only market-data access. A successful command checks source data and observed adjustment differences; exact split/dividend factor reconciliation remains a separate manual check. Offline harness tests are not a substitute for this evidence.

## Remaining completion gates

[RESEARCH.md](RESEARCH.md) documents raw-price corporate-action accounting, independent executable-fill validation, frozen chronological holdout/walk-forward evaluation and durable local forward paper trading. These are still unfinished. SEC Form 4 monitoring, insider alerts, historical political events and news analysis are explicitly Milestone 3 work; current event interfaces do not provide these services. No live trading or real financial account access has been introduced.
