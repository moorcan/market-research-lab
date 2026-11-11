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

## Recheck after the successful ChatGPT SPY request

The user reports that the official Robinhood integration is connected in ChatGPT and returned historical SPY daily prices in a read-only request. That establishes a useful **user-reported ChatGPT result**. The response/tool schema was not supplied to this app, so it does not establish Codex tool availability, local Python authorization, adjustment definitions, complete history, storage rights or the absence of interpolated bars.

The current Codex session was rechecked independently:

| Layer | Observed result | Consequence |
| --- | --- | --- |
| Codex tools exposed to this session | No Robinhood tools in the available tool catalog | There is no authorized Robinhood historical-price tool for this agent to call. No guessed tool names were invoked. |
| Cloud network policy | Restricted, enforced, no custom allowed hosts | The supplied MCP endpoint and official support entry point both still fail at the proxy with HTTP 403 CONNECT denial. The requests did not reach Robinhood. |
| App authorization | No managed secret/runtime bindings for Robinhood | The ChatGPT connector does not supply an application grant. No connector credentials, browser sessions or financial-account details were extracted. |
| App data transport | No verified official auth flow/schema/binding | `RobinhoodDaily` and the empty MCP allowlist remain disabled. No authenticated Robinhood request or actual cross-provider comparison was run. |

**Development priority:** unblock and verify Robinhood research access first; do not label it an operational primary before those gates pass. Alpaca remains the functioning code path and explicitly selected fallback. Its genuine-data validation is still separate and requires market-data credentials.

### Supported path forward, without inventing an integration

1. For immediate Robinhood research, use the **already-working official ChatGPT integration** for data-reading requests only. This is the one connection the user has reported working. It does not automatically write datasets into this application.
2. To use Robinhood inside Codex, the client must actually expose its authorized Robinhood tools to this task. If the Codex client offers the official connector for this workspace/session, attach it there and recheck the available tool catalog. A ChatGPT-only connection cannot be repurposed by copying its credentials. If the client does not support exposing it here, connector access remains unavailable in Codex.
3. A standalone Python integration requires a **Robinhood-documented supported client/API and application authorization path**. No such path has been verified here because official documentation is blocked. Do not fabricate OAuth URLs, scopes, token exchange endpoints, tool names, schemas or undocumented brokerage APIs. MCP exposure to an agent alone is not an app-owned API grant.
4. Enable exact documentation/service domains in the runtime policy and verify the live status before retrying. Read the official authentication, data licensing, automation and retention terms. If they do not permit this app's automated retrieval and local caching, do not activate Robinhood storage; continue with Alpaca under its own terms.
5. Once an authorized data tool is exposed, inspect its exact read-only input/output contract and official terms, then request a small SPY sample. Preserve the original source response outside Git where retention is permitted; confirm session timestamps, volume units, adjustment semantics, pagination, delay and interpolation flags. Do not ask an LLM to reconstruct missing bars or infer fields from prose summaries.
6. Only then implement the verified schema normalizer and the documented application transport, add exact allowlisted bindings in a reviewed source change, and run the independent SPY/provider comparison. If a documented export is available and licensed for this purpose, a separately reviewed user-supplied export/import path is an option; **no Robinhood export format or permission is assumed or implemented**.

No additional login, account-balance query or trading-tool invocation is necessary to establish this blocker. Never use order endpoints to probe whether authorization works.

### Normalization and metadata retention ready for a future verified adapter

The existing storage pipeline now preserves optional `provider_timestamp` (timezone-aware original daily bar-start instant) and nullable `is_interpolated` flags alongside OHLCV. It retains `session_timezone`, `timestamp_semantics`, the explicit adjustment mode, original endpoint, request bounds and retrieval timestamp in provenance. These are internal normalization fields, **not claims about Robinhood's response schema**.

Alpaca retains the provider's original UTC bar timestamp instead of discarding it when constructing the New York session index. Its current response does not establish a per-bar interpolation field, so flags remain unknown (`null`), never invented `false`. Known interpolated rows may be retained as labeled source evidence but cannot enter dashboard/backtest execution. Missing legacy flags remain unknown; that limitation is exposed by comparison reports. The engine does not silently replace missing bars.

DuckDB/Parquet roundtrip tests retain UTC instants across EST/EDT, adjustment metadata, all three interpolation states and source identity. Flag changes produce a new dataset version. Metadata checks reject naive/missing/mismatched timestamps and string flags. Stored bar-start time must never be treated as first-public availability time for earnings, filings or news.

### Public-research-source investigation remains separate

| Research input | Original public source to investigate | Integrity requirement / present status |
| --- | --- | --- |
| SEC filings and Form 4 transactions | SEC EDGAR: https://www.sec.gov/edgar/search-and-access | Preserve accession, public acceptance/publication time, original transaction date and amendments; distinguish code-P purchases from exercises/awards and automatic plans. Live retrieval, fair-access terms and retention remain unverified here. |
| House transaction disclosures | Official House disclosure portal: https://disclosures-clerk.house.gov/ | Preserve filing/publication dates, amendment identity and value ranges; transaction dates are not public-availability dates. No ingestion or rights verification has run. |
| Senate transaction disclosures | Official Senate disclosure portal: https://efdsearch.senate.gov/search/ | Review portal access/use restrictions before any automation; no scraping or ingestion is implemented. |
| Political/historical events, earnings and news | Original government/issuer releases and appropriately licensed timestamped archives | Retain original source, first-public time, revisions, expectations and delayed ingestion. No historical election outcomes, insider alerts or news-derived predictions are fabricated. |

These are official-source **investigation targets**, not newly retrieved evidence or a claim that automated access/storage is permitted. Robinhood availability of any of these datasets remains unverified. SEC monitoring, insider alerts, politician/event ingestion and news analysis remain future Milestone 3 work; no service has been silently activated by this connection recheck.
