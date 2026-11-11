# Research contract and roadmap

## Data-source decision

Alpaca is the initial implementation because its documented stock-bars REST endpoint supports daily bars, pagination, an explicit adjustment mode and IEX feed selection. Authentication is required; account entitlements and historical availability vary. The adapter does not assume consolidated US exchange volume. Data use and redistribution must follow the user's provider agreement.

Massive is the alternative evaluated for a future adapter: its aggregate bars, reference and corporate-action datasets could improve action coverage, but historical depth, adjusted-series conventions, licensing and subscription entitlements must be checked before implementation. No Massive adapter is claimed here.

Official references:
- https://docs.alpaca.markets/reference/stockbars-1
- https://docs.alpaca.markets/docs/market-data-faq
- https://massive.com/docs/rest/stocks/aggregates/custom-bars
- https://massive.com/docs/rest/stocks/corporate-actions/dividends
- https://www.sec.gov/edgar/search-and-access
- https://fred.stlouisfed.org/docs/api/fred/

## Critical adjustment limitation

Current downloads use `adjustment=all` on OHLCV, and the simulator operates entirely in those adjusted research units. Prices are **not historical executable dollar quotes**. These runs approximate reinvested-distribution research returns, subject to provider adjustment methodology; they are not a validated total-return index. No dividends are separately credited and no split share changes are applied, preventing double counting. Fractional research units and volume participation on adjusted bars are approximations.

An execution-grade raw-price ledger with separately validated splits, dividends, ex-dates, pay dates and delistings is unfinished. It is required before claiming realistic corporate-action accounting. Full-range refreshes deliberately create a new snapshot because past provider adjustments may change; incremental fetch/merge is not implemented. Missing sessions fail closed; truncated history and delistings are not silently accepted. The fixed current ETF universe has selection/survivorship limitations and does not support claims about a historical stock universe.

## Baseline rules

Trend: after at least N complete sessions, target long when closing price is strictly above its trailing N-session simple moving average; target cash on or below it. Mean reversion: enter when close is below its trailing mean by the configured fraction, hold until close reaches the mean, otherwise remain cash. Warmup stays in cash. Default N=50 and mean-reversion threshold=3%; no automated parameter search.

Each strategy targets at most 95% of equity in one ETF. These are allocation rules, not stop-loss guarantees. Signals calculated after close t execute no earlier than open t+1. The final close signal is unfilled. On a target change, orders expire after that next-open attempt; there is no daily rebalance or retry of unfilled remainders. Gaps use the actual next open. Missing/invalid bars reject the dataset, rather than inventing fills. End positions remain marked to final close, not force-liquidated.

Defaults per side: 1 bp proportional fee, half of a 5 bp full spread, and 5 bp slippage. Buys increase and sells decrease fill price. Fractional units, no borrowing, no short selling; buys are clipped to available cash including fees. Quantity is capped at 1% of reported daily volume. This cap uses daily volume retrospectively as a **liquidity proxy**, not information known at the open, and cannot establish executable opening liquidity. A zero-volume attempt is rejected. Queue position, halts, opening-auction depth, minimum fees, taxes and market impact beyond fixed slippage are not modeled. The higher-cost scenario doubles fees and triples spread/slippage.

Passive benchmark enters at the second session open (same signal timing, cash reserve, fees and liquidity limits), then holds. Cash earns zero; metrics use a zero risk-free rate. Annualization assumes 252 sessions. Historical 95% VaR/ES use empirical daily equity returns; small samples are unstable. Drawdown includes initial cash as a peak. Sharpe, Sortino and Calmar are undefined when denominators vanish. Realized P&L uses average-cost adjusted units including fees; win rate, profit factor and expectancy count filled sell exits (partial exits count separately). Open positions are excluded from exit statistics; unrealized P&L is separately reported.

## Integrity gates and next milestones

MVP checks verify causal features, timing, arithmetic, missing sessions and cache provenance. They do not establish alpha. No holdout claim is made. Repeated dashboard parameter changes are multiple testing and can overfit.

Milestone 1 remaining: independently validate accounting against a reference engine; raw-price corporate actions; incremental updates; real-provider integration test and Windows-host validation. Current simulation is single-instrument, not a multi-asset allocator.

Milestone 2: frozen training/validation/final holdout manifests, horizon-aware purge/embargo, walk-forward evaluation, sensitivity analysis, logistic baseline, base-rate comparison, Brier/log loss/calibration, uncertainty and time-series block bootstrap. Final test data must not tune parameters. Registry currently records dataset versions, fixed strategy configuration, engine version and exploratory periods, but not a holdout-access audit.

Milestone 3: FRED/ALFRED vintages with public release times, SEC Form 4 parsing and original accession links, historical news archive licensing, delayed sentiment, regime filters and event studies. No live event ingestion or research alerts exist yet. Form 4 transaction date must never replace public filing availability. Code P alone does not establish an unusual discretionary purchase; inspect ownership, footnotes, 10b5-1 plans and amendments. Deduplicate underlying events across sources before aggregate studies. 13F reflects delayed reported holdings, not trade-time intent; congressional disclosures have reporting delays and value ranges.

Initial political case: November 3, 2026 US midterm election. Store sourced public outcomes and archived expectations separately, without partisan return assumptions. No election outcome or market reaction is fabricated in this repository. Before using event-study results, specify benchmark, horizons, overlapping-event treatment, sample size, confidence intervals and out-of-sample evaluation. Event contracts conservatively use max(publication, ingestion)+timestamp uncertainty; this can exclude legitimate archived history and must be explicitly justified for each archival source.

Milestone 4: durable forward paper portfolios, idempotent local orders, realized/unrealized P&L and reconciliation. Optional paper-only Alpaca execution is not implemented. Milestone 5: opt-in local scheduling, health checks, reports and requested notifications. No emails or background tasks are sent or installed.

## Simulation modes and completion gates (PR #1 review)

| Capability | Current behavior | Completion requirement |
| --- | --- | --- |
| Adjusted-price exploratory backtest | Implemented; `simulation_mode=adjusted_exploratory` and `executable_price_simulation=false` in saved reports and CLI output. No separate dividend cash or split-share credits. | Only `adjustment=all` provenance may enter dashboard/CLI backtests or experiment reports. Treat after-cost results as exploratory approximations. |
| Executable-price historical simulation | **Not implemented**; requesting another engine mode raises an error. Raw quotes fetched by the smoke tool are inspection data only. | Add a distinct raw-price/accounting path, raw share units, action ledger and independent fill/accounting validation. Never relabel adjusted units as historical executable quotes. |
| Corporate actions | Provider-adjusted bars only. | Validate split ratios, fractional entitlements, ex-date holdings, dividend receivables/pay-date cash, reinvestment assumptions and delisting proceeds. Reconcile provider adjustments against original action sources and prove dividends/splits are not credited twice. Keep adjusted feature prices separate from raw execution prices. |
| Statistical/holdout validation — Milestone 2 | **Not implemented**; all current runs are in-sample exploration. | Freeze strategy/version/parameters and data vintages before an untouched final test; separate chronological train/validation/test, purge overlapping label horizons, use walk-forward validation, cost stress and multiple-testing/sensitivity reporting. Log final holdout access; never tune on it. Require sufficient sample sizes and benchmark comparisons. |
| Forward paper trading — Milestone 4 | **Not implemented**; Paper Portfolio currently shows historical fictional accounting. | Durable local-only fictional $2,700 portfolios; idempotent timestamped decisions/orders, next-available simulated fills, stale-data refusal, restart recovery, realized/unrealized P&L, ledger reconciliation and backtest-vs-forward monitoring. Complete integrity and holdout gates first. No real-money endpoints or account connections. |

### Explicitly deferred Event Intelligence scope — Milestone 3

SEC Form 4 **monitoring**, unusual/clustered public **insider alerts**, sourced **historical political events** (including the November 2026 election case), and historical **news ingestion/classification/sentiment/event studies** remain scheduled for **Milestone 3**, not part of the price-based MVP. Current event code provides contracts, basic code-P classification, availability filtering and tests only. It does not download filings, continuously monitor disclosures, issue alerts, or calculate political/news predictions. Optional Form 13F and congressional-disclosure ingestion are also future research work.

Future alerts require public source links, first-publication/ingestion timestamps, amended-record and cross-source deduplication, discretionary-vs-compensation/plan distinctions, sample sizes, uncertainty and out-of-sample evidence. Scheduling/notification delivery is a later Milestone 5 capability and is opt-in. Nothing in these milestones authorizes brokerage access or real-money trading.

### Metric availability and report format

A one-session series supports cumulative equity/accounting and drawdown, but annualized return/volatility, Sharpe/Sortino/Calmar and historical VaR/ES are unavailable (`null`). At two or more sessions, computable estimates are still statistically weak; the report includes the session count and the dashboard warns on short samples. Zero variance, zero downside or zero drawdown make the respective ratios undefined. Nonfinite derived numerical estimates (including annualization overflow) serialize as JSON `null`, never `NaN` or `Infinity`; malformed/empty equity is rejected. A missing estimate never means zero risk. No-exit win rate/profit factor/expectancy are unavailable, not fabricated zeros.

See [the opt-in real-data procedure](ALPACA_SMOKE_TEST.md) for genuine-data prerequisites, evidence and the required manual corporate-action reconciliation.
