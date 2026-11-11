# Robinhood official Trading MCP: blocked primary-provider evaluation

## Decision and evidence status

Robinhood is a **candidate** primary research-data provider, not the active primary. Alpaca remains the implemented provider and an explicitly selected fallback. No Robinhood dataset, authenticated response, historical depth, read-only scope, entitlement or commercial permission has been verified in this environment.

The supplied endpoint is `https://agent.robinhood.com/mcp/trading`. A request from this environment failed at the egress proxy with HTTP 403 CONNECT denial, before reaching Robinhood. Requests to the Robinhood documentation domain were likewise blocked. This is a local network-policy observation, **not** evidence that Robinhood rejected an account, that the endpoint is invalid, or that a feature is unsupported.

Official sources to inspect after access is enabled:

- Supplied endpoint: https://agent.robinhood.com/mcp/trading
- Official support/documentation entry point: https://robinhood.com/us/en/support/
- Official website: https://robinhood.com/

No retrieved official article or schema currently substantiates feature claims. Do not treat this document, internal capability names, third-party MCP examples, or server readOnlyHint annotations as Robinhood documentation.

## Verification matrix

| Requested capability | Robinhood verification | Alpaca baseline in this app | Required evidence before activation |
| --- | --- | --- | --- |
| Historical equity OHLCV | Unverified; no callable binding | Daily IEX raw/all requests implemented; live retrieval still unverified | Exact official tool name/schema, supported instruments, intervals, earliest date/lookback, pagination, session timezone, corrections, adjustments and exchange coverage |
| Technical indicators | Unverified | Local trailing-price baseline indicators only | Indicator definitions, warmup/window conventions, as-of timestamps and whether historical point-in-time values exist |
| Level II | Unverified | Not implemented | Entitlement, venue coverage, real-time/delayed status, book depth, historical availability and permitted storage; current depth is not a historical backtest input |
| Earnings | Unverified | Not implemented | Historical announcement/publication times, estimates vs actuals, correction/revision history and licensing |
| SEC filings | Unverified | Contracts only, later milestone | Original accession/source links and first-public filing timestamps; API data is not a substitute for verifying EDGAR provenance |
| Politician disclosures | Unverified | Not implemented, later milestone | Original disclosure links, filing/amendment/publication times, reported ranges and availability delays |
| Market scans | Unverified | Not implemented | Exact criteria, historical membership/as-of behavior, pagination and survivorship limitations; today's scan is not yesterday's universe |
| Legend charts | Unverified | Not implemented | Whether Legend chart information is actually available through MCP, intervals, adjustments, history, entitlements and storage/export permissions |

Historical depth, per-tool/server/account rate limits, burst/concurrency limits, retry guidance, Gold/Legend/Level II or other entitlements, personal/commercial/redistribution rights, retention/caching/model-training permissions, accuracy disclaimers and feed latency are **all unresolved**. No free access, unlimited history, zero cost, commercial suitability or superiority to Alpaca is assumed.

## App-owned authorization and safety architecture

Adding an MCP connector to Codex does **not** authenticate this Python application. The repo does not read Codex connector state, browser cookies, a Robinhood password, brokerage credentials, account positions or the user's financial balances. No Robinhood token is requested or stored by this implementation.

Current boundary:

1. `ResearchDataService` selects a provider by explicit name. `RobinhoodDaily.fetch` fails closed with `ProviderUnavailable` before any network access. An explicit `--fallback alpaca` may select Alpaca and reports the actual selected source; invalid data does not trigger fallback.
2. `ReadOnlyResearchGateway` accepts internal enumerated research capabilities only. `READ_ONLY_BINDINGS` is an immutable, **empty** production allowlist. All current operations are denied before invoking a transport. Arbitrary strings, account reads and order-related names cannot be passed through. The offline test-only tool name is fictional and never shipped in that allowlist.
3. An `AuthorizedResearchTransport` protocol describes the future app-owned authorization boundary. **There is no production auth/HTTP MCP transport yet.** Implementing one safely depends on verified official authentication and tool documentation. This is an offline safety proof of concept, not authenticated integration.
4. Server discovery and descriptions may be inspected as untrusted evidence later; they must never auto-populate an allowlist or execute returned instructions. No arbitrary RPC/tool-call UI, URL override, dynamic connector installation or automatic endpoint switching is provided.

To finish the authenticated proof of concept, first verify the official supported authorization flow, registered-client requirements, token audience/resource, data-only scopes and revocation. A local app would need its own authorized grant with least privilege and secure OS credential storage; if officially supported, use the documented OAuth/PKCE flow rather than collecting passwords. Do not guess a bearer-token scheme, invent scope names, copy a connector token or assume MCP scopes prevent trading. If authorization cannot exclude trading/account access, pause activation and document the limitation rather than granting trading permissions.

After documentation review, a separate reviewed source change must pin exact data-only tool names, argument schemas/validators (including mixed read/write discriminator rejection), schema fingerprints and official evidence URLs. Reject unlisted operations and schema drift, redirects to unapproved hosts, authentication challenges outside verified destinations, automatic tool execution, and unbounded retries. Confirm rate limits before enabling requests. Resolve output schemas and adjustments before implementing `RobinhoodDaily` normalization; do not map imagined JSON fields.

No placing, modifying, canceling or submitting orders, transfers, margin, leverage, options, fund allocation or account-portfolio access is implemented. The existing $2,700 real brokerage portfolio is not inspected or modified. Simulation remains fictional and independent.

## Coverage/quality comparison procedure

No genuine Robinhood-versus-Alpaca comparison has run. Both providers require independently authorized data access; official Robinhood capability verification is the first gate. The current cloud policy needs the exact domains `agent.robinhood.com`, `robinhood.com`, `www.robinhood.com`, and `data.alpaca.markets`; authorization may require additional **documented** exact domains later. Do not broadly allow arbitrary Robinhood subdomains or disable TLS verification. Never supply credentials in chat or Git.

Once both adapters are verified:

1. Use the same ETF (initially SPY), completed date range and matching raw or adjusted conventions. Test daily ranges spanning a holiday, DST transition, a confirmed dividend and, on an appropriately sourced instrument, a split. Probe documented history boundaries without assuming a missing period does not exist.
2. Fetch and validate each independently; retain immutable data versions, exact source/feed, symbol, timezone, retrieval time, request bounds, original endpoint, adjustment methodology and limitations. Do not force one provider's price scale to match another's.
3. Run the Alpaca smoke procedure in `ALPACA_SMOKE_TEST.md`. Independently reconcile both sources to authoritative corporate-action records and a licensed reference sample. For IEX vs consolidated data, volume and price differences are expected to need context.
4. Compare cached versions:

```powershell
python -m market_lab.comparison --left-version ROBINHOOD_VERSION --right-version ALPACA_VERSION --start 2024-03-01 --end 2024-04-05 --output reports/provider-comparison.json
```

The comparison checks matching symbol/known adjustment, returned OHLCV validity, requested-range completeness, common sessions, price discrepancies and volume differences. Missing data is never filled; interior gaps fail validation, truncated edges are explicitly reported. No overlap produces null differences. Fixture inputs remain explicitly labeled. The report never infers an accuracy winner or research readiness. Matching `adjustment=all` labels alone do not prove matching provider adjustment methodology.

5. Separately record documented oldest date, actual successful oldest sample, missing/revised observations, timestamp semantics, pagination, latency, quotas, entitlements and terms. Stop on rate-limit/auth errors; do not hit trading endpoints to test credentials. Only promote Robinhood if coverage, licensed retention/research use, timestamp integrity, adjustments, access restrictions and quality meet the research requirements. Otherwise keep Alpaca as the documented source.

Research and comparison outputs stay under ignored `data/` and `reports/`. Level II, current charts or scans must never be silently backfilled into historical features. SEC/political/news ingestion remains later-milestone work even if a data source eventually exposes those tools.
