# Market Research Lab

Local, research-only ETF backtesting with **fictional $2,700 cash**. There is no brokerage connector, real order submission, leverage, shorting, options, or Robinhood integration. Never supply brokerage credentials.

## Windows setup (PowerShell)

Install Python **3.12**, then from this checkout:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Open the local URL Streamlit prints. No paid hosting is required. Direct dependencies are pinned in `requirements.txt`; the full tested Python 3.12 dependency resolution is in `requirements-lock.txt`. Windows execution has not yet been verified on a Windows host.

For genuine data, set **market-data-only** Alpaca keys in the same PowerShell session before launch:

```powershell
$env:APCA_API_KEY_ID = "YOUR_MARKET_DATA_KEY"
$env:APCA_API_SECRET_KEY = "YOUR_MARKET_DATA_SECRET"
```

Do not commit keys or paste them into research journals. The app only requests HTTPS GETs from `data.alpaca.markets`; it has no order endpoints. In Overview, choose a completed historical range and retrieve bars. Without keys, the dashboard remains usable but shows no research results. There is no synthetic fallback.

Linux equivalent: create a Python 3.12 virtual environment, install the lockfile and editable package, then run `python -m pytest -q` and `python -m streamlit run app.py --server.address 127.0.0.1`.

## What works

- Provider interface and Alpaca paginated IEX daily OHLCV adapter for SPY, QQQ, IWM, TLT, GLD, XLF, XLK.
- XNYS session completeness, duplicate, numeric and OHLC consistency validation; no silent missing-session interpolation.
- Immutable Parquet snapshots with provenance and DuckDB catalog; versioned experiment JSON, equity CSV and trade journals.
- Two causal baseline strategies, next-session open simulation, long-only fractional research units, cash accounting, configurable fee/spread/slippage, volume-cap partial fills/rejections.
- Passive benchmark under identical constraints, zero-interest cash baseline, higher-cost scenario, drawdowns and basic historical risk metrics.
- Streamlit Overview, Strategy Lab, Risk Center, simulated Paper Portfolio and Research Journal.
- Public-event/news contracts with timezone-aware publication, ingestion, uncertainty and duplicate safeguards. SEC transaction code P classification is descriptive, not proof of discretionary activity.

All strategy runs are **exploratory in-sample historical simulations**, not validated investment findings or forward paper results. The Paper Portfolio section is a historical simulated ledger, not a persistent forward-trading service.

See [research assumptions and remaining work](docs/RESEARCH.md) and [validation evidence](docs/VALIDATION.md).

## Local persistence

`data/` and `reports/` are ignored by Git. Keep them between updates; back up both together while the app is stopped. The catalog records absolute Parquet paths, so restore at the same location or rebuild the catalog before using a relocated backup. New retrievals create new versions and never overwrite older experiments. Do not delete these directories during upgrades.

## Development

`src/market_lab/data.py` holds provider and storage contracts; `strategies.py` creates close-time targets; `backtest.py` handles execution and metrics; `events.py` enforces public availability; `experiments.py` records runs. `app.py` is the local UI. Test fixtures are explicitly synthetic and created only in tests.

No strategy is qualified for forward paper testing yet. The remaining integrity and data work in the roadmap must pass before that status changes.

## Reproducible command-line runs

With the environment activated and market-data keys configured:

```powershell
python -m market_lab fetch SPY 2020-01-01 2025-12-31
# Copy the immutable dataset version printed by fetch:
python -m market_lab backtest DATASET_VERSION --strategy trend --window 50
python -m market_lab backtest DATASET_VERSION --strategy mean_reversion --window 20 --threshold 0.03
```

Use the same dataset version and parameters to reproduce a run. CLI output explicitly labels test fixtures and exploratory evaluation. JSON/CSV reports remain local; execution errors return a failing command status.

## Review checks and data validation

GitHub Actions runs the pinned dependency installation, `python -m pip check` and `python -m pytest -q` on Python 3.12 for pushes and pull requests. Tests are offline; no API keys are required or passed to CI.

For genuine market data, follow the [opt-in Alpaca smoke-test procedure](docs/ALPACA_SMOKE_TEST.md). It checks complete market sessions, timestamps, raw-vs-adjusted behavior and provenance without submitting orders. Live provider validation is blocked until market-data credentials and exact-domain network access are available.

**Only adjusted-price exploratory backtests are implemented.** Reports identify that mode explicitly; raw/executable-price simulation is unavailable, and raw datasets are rejected at the dashboard/CLI/report boundary. The [completion gates](docs/RESEARCH.md#simulation-modes-and-completion-gates-pr-1-review) cover corporate actions, untouched holdout testing and forward paper trading. SEC Form 4 monitoring, insider alerts, historical political events and news analysis are explicitly deferred to Milestone 3.


## Robinhood Trading MCP evaluation

Robinhood's supplied official MCP endpoint is being evaluated as a primary **research-data candidate**, but it is disabled pending official-documentation, authorization, schema, licensing and quality verification. This change does not connect to Robinhood accounts or use Codex connector credentials. The production data-tool allowlist is empty; no authenticated MCP request or genuine cross-provider comparison has passed.

The [evaluation matrix and app-owned authorization architecture](docs/ROBINHOOD_MCP_EVALUATION.md) state what is blocked and how to complete a safe proof of concept. Alpaca remains usable. Selection is explicit, and fallback is opt-in:

```powershell
python -m market_lab fetch SPY 2024-03-01 2024-04-05 --provider alpaca
# Robinhood is currently blocked; this command uses Alpaca only when explicitly permitted:
python -m market_lab fetch SPY 2024-03-01 2024-04-05 --provider robinhood_mcp --fallback alpaca
```

Fetch now prints JSON containing `dataset_version`, `requested_provider`, `selected_provider` and `used_fallback`. A fallback dataset retains its actual Alpaca provenance; it must never be reported as Robinhood data. The dashboard also makes source selection explicit.
