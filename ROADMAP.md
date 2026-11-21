# Aurelius Roadmap — FinTrack Transformation

Last updated: 2026-11-18

## Product direction

**Aurelius** is the planned AI financial intelligence and investment operating system evolving from the FinTrack personal-finance MVP.

**Current status: Foundations 0.3–0.6 in active development.** The versioned ISO 4217 registry, ledger persistence, PostgreSQL constraints, atomic posting/reversals, and authenticated v1 ledger API have been implemented and CI-tested on stacked branches. The global asset/instrument ontology and persistence, provider adapter framework, market-observation ingestion, and long-only portfolio-lot accounting are the next implementation layers. PR #25 merged the provider-neutral adapter framework; PRs #26–#27 and the portfolio-lot persistence branch remain under review. No brokerage execution, paid market-data subscription, hosted database migration, or deployment is authorized.

**Guiding principle:** evidence, exact calculations, transparency, and downside protection over confident-sounding answers.

## Phase 0 — Repository and financial-core stabilization (first priority)

### Repository baseline and release coordination
- [x] Inspect the default-branch repository structure, backend/frontend implementation, tests, Render Blueprint, branches, open PRs, and open issue.
- [x] Identify the difference between deployed/main code and the more advanced integration/documentation draft branches.
- [x] Produce the Aurelius transformation assessment and initial architecture recommendation.
- [x] Record preliminary provider options and licensing/cost caveats.
- [ ] Reconcile overlapping documentation PRs #8 and #11; do not merge automatically.
- [ ] Review PR #9 (FastAPI form-parser security fix) independently; it is not included in integration PR #12.
- [ ] Resolve issue #6's status against the fixed-precision implementation in PRs #10/#12.
- [ ] Complete a clean, reviewed integration plan for PRs #3, #4, #5, #7, #9, and #10. PR #12 currently integrates #3/#5/#7/#10, but is not a substitute for reviewing each source PR.
- [ ] Keep all PRs draft until security, data migration, and deployment gates are satisfied.

### Aurelius Foundation 0.1 — active work
- [x] Add an infrastructure-independent `Money` value object using Python `Decimal`.
- [x] Replace the initial eight-code exponent allowlist with the versioned SIX ISO 4217 registry (178 current codes, 165 with published exponents).
- [x] Add fixed-scale decimal-string serialization, exact construction from integer minor units, minor-unit conversion, canonical zero, same-currency arithmetic, and cross-currency rejection.
- [x] Add deterministic unit tests for scale, rounding, float rejection, invalid values, and FX boundary behavior.
- [x] Record ADR-0001 for modular-monolith boundaries and read-only AI decision support.
- [x] Obtain passing CI on the feature branch and preserve all legacy MVP tests (run #125: backend compile, Alembic upgrade, pytest; frontend tests and production build).
- [x] Define account ownership, immutable identity, account types, currency invariants, and normal balance rules in the Foundation 0.2 domain contract.
- [x] Define balanced single-currency journal entries, positive postings, append-only corrections, one-time reversals, and same-currency asset transfers.
- [x] Add accounting golden cases for opening balances, income, expenses, transfers, reversals, ownership, currency, and closed-account validation.
- [x] Obtain passing CI on the Foundation 0.2 branch and complete static review before considering API/persistence design (run #136).

### Financial correctness and data model
- [x] Establish the versioned global money contract: ISO 4217 currency definitions, explicit minor-unit exponents, Decimal/integer calculations, exact NUMERIC persistence, and string-based API serialization. See `docs/finance/MONEY_CONTRACT.md`.
- [ ] Migrate legacy FinTrack transaction/budget/goal endpoints away from binary-float monetary fields; the new Aurelius v1 ledger API already uses integer minor-unit strings.
- [x] Define and persist financial account identity, owner scope, currency, account types, and derived normal-side balances.
- [x] Persist balanced journal postings, same-currency account constraints, and reversal-based corrections; opening-balance workflows remain to be exposed.
- [x] Model and persist owner-scoped financial accounts and liability account types in the Aurelius ledger schema; net-worth reporting and valuation are still pending.
- [x] Support multiple native account currencies and an independent owner reporting-currency preference in the persistence model.
- [ ] Add timestamped FX observations and reproducible functional/reporting-currency valuation.
- [x] Implement balanced immutable journal postings, idempotency, audit events, and reversal-based corrections.
- [ ] Add reconciliation status, immutable statement-import history, and correction workflows.
- [ ] Add golden-case tests for rounding, aggregation, negative balances, refunds, transfers, FX conversion, leap/month boundaries, and currency precision.
- [ ] Preserve account isolation across every new table, endpoint, report, export, and background task.

### Operational and security prerequisites
- [ ] Plan durable PostgreSQL hosting, backups, and a tested restore before the documented free database expiry on 2026-12-02.
- [ ] Confirm current live Render health and correct service URLs before relying on the existing deployment; no Blueprint sync or deployment without approval.
- [ ] Configure shared rate-limit storage and verify trusted-proxy/client-IP handling before multi-instance production.
- [ ] Review JWT lifecycle, password recovery/email verification, security headers, audit logging, secret handling, dependency updates, and access-control tests.
- [ ] Establish a privacy/data-retention policy before storing brokerage statements, tax documents, or AI conversation context.

**Phase 0 exit criteria:** clean integration CI; reviewed security fixes; exact money/currency contract; passing accounting golden tests; explicit deployment/backup plan; no unresolved critical security or data-loss risks.

## Foundation 0.6 — Portfolio lots and execution history

- [x] Add deterministic long-only trade/lot domain with FIFO, LIFO, and specific-lot disposal methods.
- [x] Add exact Decimal quantities, prices, fees, acquisition costs, disposal proceeds, and realized gain/loss calculations.
- [x] Add execution-ID replay protection and atomic in-memory validation.
- [ ] Persist owner-scoped portfolios, immutable trade executions, acquisition lots, and disposal allocations (draft branch: feat/aurelius-foundation-0.6-portfolio-lot-persistence).
- [ ] Validate Alembic revision 0005 and PostgreSQL append-only/owner-scope constraints in CI.
- [x] Implement the PostgreSQL application service with per-position locking, execution-ID idempotency, deterministic replay, and atomic audit/lot writes.
- [x] Validate service concurrency, rollback, and replay behavior in PostgreSQL 16 CI (run #410: 42 PostgreSQL integration tests passed).
- [ ] Test oversell races, duplicate execution races, specific-lot isolation, and out-of-order/backdated fill policy.
- [ ] Define atomic cash-ledger settlement/fee/FX integration before any portfolio trade API.
- [ ] Add owner-scoped portfolio read APIs only after persistence and concurrency gates pass.

The first lot implementation is long-only and is not a tax engine. FIFO/LIFO/specific selection is a configurable accounting method, not a universal tax-law determination. Derivatives lifecycle, corporate actions, dividends, short positions, and tax-jurisdiction policies remain separate work.

## Phase 1 — Financial Core
- Expand the current transaction/budget/goal MVP into account-based personal finance.
- Build account balances, opening balances, transfers, liabilities, net worth, income/expense statements, cash flow, budgets, and forecasts.
- Add reconciliation, recurring transactions, CSV import/export, duplicate detection, and source documents.
- [x] Support multi-currency native accounts and a separate owner reporting-currency preference.
- [ ] Add timestamped FX observations and auditable functional/reporting-currency conversion.
- Deliver a financial overview with explainable calculations and clear data-completeness indicators.

## Phase 2 — Market Intelligence
- Add watchlists, instruments, identifiers, exchanges, asset classes, historical prices, and quote timestamps.
- Integrate macroeconomic series, company filings, financial statements, corporate actions, and news.
- Normalize data behind provider adapters; retain raw source references and ingestion metadata.
- Add caching, rate-limit handling, retries, provider health, stale-data warnings, and reconciliation between sources.
- Start with end-of-day data; do not imply real-time access unless the selected license and feed support it.

## Phase 3 — AI Financial Partner
- Build a central assistant that can answer questions using authorized personal financial data and cited market evidence.
- Add specialist roles: Market Analyst, Fundamental Analyst, Trading Analyst, Accountant, Risk Manager, Financial Educator, Research Analyst, Independent Reviewer.
- Use typed inputs/outputs, bounded tools, source citations, explicit uncertainty, and role-specific permissions.
- Add Investment Thesis Tracker and append-only Decision Journal.
- Require an independent second opinion for significant decisions; show disagreements rather than forcing false consensus.

## Phase 4 — Investment and Trading Intelligence
- Add fundamental/valuation analysis, peer comparisons, technical indicators, support/resistance, volatility, and momentum.
- Add risk/reward, position sizing, concentration, liquidity, and drawdown calculations.
- Implement paper portfolios and simulated orders only, with fees, slippage, corporate actions, and clear simulation labels.
- Backtest with point-in-time data, survivorship-bias controls, look-ahead-bias controls, and out-of-sample validation.
- Keep brokerage execution disabled.

## Phase 5 — Predictive Analytics
- Establish a prediction registry with immutable timestamp, probability, horizon, target, model/version, evidence, and outcome rule.
- Track calibration, Brier score, log loss, hit rate, benchmark comparisons, and confidence intervals where appropriate.
- Compare simple baselines against complex models; retain models only when they demonstrate out-of-sample value.
- Show scenario ranges and assumptions, never deterministic promises.
- Monitor drift and retire unreliable models.

## Phase 6 — Autonomous Monitoring
- Add scheduled market/filing/macro monitoring, thesis invalidation checks, portfolio drift alerts, and unusual-movement detection.
- Produce daily, weekly, and monthly reports with source timestamps and change summaries.
- Add user-configurable alert thresholds, quiet periods, deduplication, retries, and delivery audit logs.
- Use a background worker or scheduled job only when justified by real workload; never let scheduled AI tasks execute trades.

## Phase 7 — Professional Reliability
- Complete threat modeling, security/privacy audits, dependency and supply-chain review, and access-control testing.
- Add end-to-end tests, provider contract tests, data-quality monitoring, model evaluation, audit-log integrity, backup/restore drills, and disaster recovery.
- Add role-based permissions, retention/export/delete workflows, observability, cost controls, and incident procedures.
- Review licensing and jurisdiction-specific legal obligations before external distribution or commercial use.

## First practical development milestone: Aurelius Foundation 0.1

**Scope:** documentation + architecture contract + financial-core risk register; no AI framework, provider subscription, or external integration yet.

1. Reconcile the draft PR landscape and create a safe release baseline.
2. Specify the exact money/currency/API representation, including the current Decimal-to-float boundary problem.
3. Draft domain boundaries and initial PostgreSQL entities for accounts, currencies, ledger entries, instruments, source observations, theses, decisions, and predictions—without implementing all tables at once.
4. Define a canonical evidence schema and provider adapter interface.
5. Add a small set of deterministic accounting golden tests before any AI feature.
6. Establish CI coverage and documentation conventions for the Aurelius branch.

**Milestone acceptance:** architecture decision records are reviewed; financial correctness tests pass; no external data or AI calls are required for CI; all proposed agent tools are read-only; the existing FinTrack workflows remain intact.

## Proposed architecture

Start as a **modular monolith**:

- backend/app/domain/: money, ledger, accounts, portfolio, market, risk, research, decisions, predictions.
- backend/app/application/: use cases and orchestration interfaces.
- backend/app/providers/: SEC, FRED, market-data, FX, and news adapters.
- backend/app/intelligence/: central coordinator, specialist prompts/contracts, evidence assembly, independent review.
- backend/app/api/: focused FastAPI routers and versioned schemas.
- backend/app/jobs/: later scheduled ingestion/reporting tasks.
- frontend/src/features/: finance, portfolio, markets, research, decisions, education, settings.
- PostgreSQL: normalized records, provenance, audit events, prediction history; optional full-text search first, vector retrieval only after evaluation.

**Agent boundaries:** specialists do not connect directly to databases or providers. They request bounded tools through the application layer. The application layer validates every request, performs deterministic calculations, enforces user permissions, and logs consequential actions. The independent reviewer receives the evidence and proposed conclusion, not merely the first agent's persuasive narrative.

## Preliminary provider evaluation (no selection or purchase)

| Provider | Best initial role | Cost/limits observed 2026-11-17 | Important caveat |
|---|---|---|---|
| SEC EDGAR | U.S. filings and XBRL company facts | Public API, no key; fair-access ceiling 10 requests/second | Declare User-Agent; server-side access; no CORS on data.sec.gov |
| FRED | U.S. macroeconomic time series | API key required; no subscription price identified in reviewed terms | Third-party series rights may apply; display required notice |
| FMP | Broad fundamentals, ratios, news, multi-asset data | Basic free 250 calls/day; Starter $19/mo billed annually; Premium $49; Ultimate $99 | Tier coverage varies; display/redistribution requires separate licensing agreement |
| Alpha Vantage | Lightweight quote/history prototype | Free 25 requests/day; premium tiers for higher usage and real-time/delayed U.S. quotes | Too constrained for broad autonomous monitoring on free tier |
| Massive (Polygon) | U.S. market data, aggregates, WebSockets | Stocks Basic free 5 calls/min; Starter $29/mo; Developer $79; Advanced $199 | Individual-use tiers differ from business plans; verify display/commercial licensing |

Official references: [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [SEC fair access](https://www.sec.gov/about/developer-resources), [FRED terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html), [FMP pricing](https://site.financialmodelingprep.com/pricing-plans), [Alpha Vantage limits](https://www.alphavantage.co/support/api-key/), [Massive pricing](https://massive.com/pricing). Pricing and entitlements change; re-check before implementation. This is a preliminary screen, not a legal licensing opinion.

**Initial recommendation:** SEC + FRED + one free EOD feed for a provider-neutral prototype. Do not buy a subscription yet. Compare actual symbol coverage, corporate actions, history depth, timestamp quality, reliability, API limits, display rights, commercial rights, and total cost before selecting a paid source.

## Current FinTrack release baseline (preserved, not yet shipped)

- Main branch is the older MVP. The latest inspected main tree does not include frontend/package-lock.json; its CI uses npm install.
- PR #12 integration branch has the lockfile, npm ci, fixed-precision money, CSV escaping, account-isolation coverage, login/register rate limits, populated SQLite/PostgreSQL migration tests, Vitest 4.1.12, and lazy-loaded charts. CI run #114 passed all three jobs.
- PR #11 contains release documentation updates and CI run #115 passed its backend/frontend jobs.
- PR #9 is a separate open draft security fix and is not in PR #12.
- PR #4 contains proposed Render URL/CORS corrections; no Blueprint sync was performed.
- PRs #8 and #11 are overlapping documentation work and require coordination.
- All changes remain unmerged drafts. No deployment, Render infrastructure change, production migration, paid service, or production data write was performed.

## Non-negotiable release gates

- No merge, deployment, Render Blueprint sync, infrastructure/secrets change, paid subscription, brokerage connection, money movement, or production data write without explicit approval.
- Real-money trading stays disabled.
- Do not represent forecasts as guarantees or unsupported market data as verified.
- Back up and test restore before any production database migration or reliance on durable financial records.
- Keep the original FinTrack application functional throughout the transformation.

## Historical FinTrack roadmap

The prior MVP roadmap and release notes are retained below for traceability.

---

# FinTrack Roadmap

Last updated: 2026-11-10

## Current release: 2.2.1

**Status: Deployed on Render; infrastructure and API health verified. Live user-workflow acceptance testing remains.**

### Live infrastructure

- Render Blueprint: `fintrack` (`exs-dbkhp88m7kps7396um8g`)
- API: [https://fintrack-api-l1wa.onrender.com](https://fintrack-api-l1wa.onrender.com)
- Frontend: [https://fintrack-web-int6.onrender.com](https://fintrack-web-int6.onrender.com)
- Database: `fintrack-db` (PostgreSQL 18, free tier)
- Repository: `matteojose3112-bit/aurelius`, branch `main`

### Deployment and verification

- [x] Create Render Blueprint from repository configuration.
- [x] Provision API service, static frontend, and PostgreSQL database.
- [x] Deploy API successfully and confirm Render reports it live.
- [x] Deploy frontend successfully with the production authentication API URL fix (merge commit `1549d9641a036cc72cd479b54624289b11fd6dd5`).
- [x] Confirm API health checks return HTTP 200.
- [x] Confirm PostgreSQL is available and expected schema tables exist: users, transactions, budgets, goals, and Alembic version.
- [x] Confirm frontend production build completes.
- [ ] Manually verify live account registration and login in a browser.
- [ ] Verify live transaction creation, listing, and deletion.
- [ ] Verify live budgets and savings-goal creation/progress/contributions.
- [ ] Verify CSV export and cross-account data isolation.

### Product and engineering

- [x] Responsive dashboard and transaction management.
- [x] Budget management and savings goals.
- [x] Monthly analytics and CSV export.
- [x] Registration, login, JWT authentication, and password hashing.
- [x] User-scoped financial records and API integration tests.
- [x] PostgreSQL support and Alembic initial schema migration.
- [x] GitHub Actions test and production-build workflow.
- [ ] Broader accessibility and keyboard-navigation audit.
- [ ] Password reset and email verification.
- [ ] API rate limiting and additional abuse protection.
- [ ] Automated database backups and restore testing.
- [ ] Legacy SQLite data import/upgrade utility.
- [ ] Review and remediate frontend npm audit findings (3 moderate, 1 high, 2 critical).
- [ ] Reduce or split the frontend production bundle (currently above 500 kB minified).

## Production readiness notes

The current Render PostgreSQL database is on the free tier and is scheduled to expire on December 2, 2026. Upgrade to durable paid resources and configure backups before storing real financial information. The live deployment and API health are verified, but browser-based end-to-end workflows and production security review are still outstanding. FinTrack is a portfolio/educational application, not a bank or financial-advice service.

---

Last reviewed: 2026-11-03

## Current direction — 2026-11-03

**Deployed portfolio application · Live acceptance and production-readiness work outstanding.** Next priorities: complete live registration/login and transaction, budget, goal, export, and account-isolation browser tests; review/remediate frontend dependency audit findings; reduce the production bundle; and plan a durable database upgrade with backups before the free PostgreSQL expiry on 2026-12-02. Do not store durable real financial records on the expiring free-tier database. A broader accessibility/keyboard audit and legacy SQLite import path remain open.


## Release-readiness update — 2026-11-09

**Current state: five focused hardening PRs are open as drafts; none is merged or deployed.** Their individual CI runs have passed, but this does not establish that the combined changes integrate cleanly.

### Draft pull requests

- [ ] **#3 — Account isolation regression tests:** draft PR; CI passed. Include in combined integration validation.
- [ ] **#4 — Production API URL and CORS configuration:** draft PR; CI passed. Review configuration before any authorized Render Blueprint sync.
- [ ] **#5 — CSV formula-injection protection:** draft PR; CI passed. Include in combined integration validation.
- [ ] **#7 — Authentication rate limiting:** draft PR; CI passed. Plan shared Redis/Valkey storage for multi-instance production and verify trusted-proxy/client-IP behavior before deployment.
- [ ] **#10 — Fixed-precision monetary amounts:** draft PR; CI passed. Add/perform populated legacy-data migration coverage and verify PostgreSQL conversion behavior before considering production migration.

### Updated next steps

1. Build and test a combined integration branch for PRs #3, #5, #7, and #10; review #4's deployment configuration separately.
2. Add migration regression coverage using populated pre-migration data and validate the PostgreSQL migration path for PR #10.
3. Run controlled live browser acceptance tests for registration/login, transactions, budgets, goals, CSV export, and account isolation after an approved deployment.
4. Review the frontend dependency audit findings and production bundle-size warning.
5. Arrange a durable PostgreSQL plan, verified backup, and restore procedure before the current free database expires on **2026-12-02**.

### Safety and release gates

- No draft PR has been merged; no production deployment or migration has been initiated.
- Do not sync Render Blueprint changes, alter infrastructure/secrets, or write production data without explicit approval.
- Back up production data and verify a restore path before any schema migration.
- The live app remains a portfolio/educational project, not a bank or financial-advice service.



## Release-readiness update — 2026-11-10

### Completed validation
- [x] Add a populated legacy SQLite migration regression to PR #10; CI run #91 passed.
- [x] Build a combined integration draft PR #12 covering PRs #3, #5, #7, and #10; initial combined CI run #92 passed.
- [x] Review PR #4's Render API URL and CORS diff; no Blueprint sync or live configuration change.
- [x] Review the PostgreSQL migration code path statically; no production or non-production PostgreSQL migration was run.

### Remaining release gates
1. Obtain a fresh CI run for the latest PR #12 head (a small whitespace-handling correction was committed after run #92).
2. Execute the populated-data migration against a disposable PostgreSQL instance and verify data rounding, indexes, foreign keys, and schema revision.
3. Confirm trusted-proxy/client-IP behavior and provision private shared Redis/Valkey storage before deploying rate limits to multiple instances.
4. Re-run the frontend dependency audit, assess remediation, and measure the current production bundle.
5. Complete live browser acceptance only after an explicitly approved deployment.
6. Arrange durable PostgreSQL hosting, a verified backup, and a tested restore before 2026-12-02.

PR #12 is an integration test vehicle, not a merge authorization or a replacement for reviewing the individual draft PRs. No PR has been merged; no Render sync, deployment, production migration, infrastructure/secrets change, or production data write was performed.


### Additional migration validation — 2026-11-10
- [x] Add a PostgreSQL 16 service job to the integration CI workflow.
- [x] Execute the populated legacy-data migration against disposable PostgreSQL; integration CI run #96 passed.
- [x] Confirm all three integration CI jobs passed: backend, frontend, and populated PostgreSQL migration.


### Frontend maintenance follow-up — 2026-11-10
- [x] Re-run npm audit in CI and identify affected packages and severity.
- [ ] Plan and test the major Vitest upgrade to 4.1.12 (audit's reported fix path); affected packages are dev/test dependencies.
- [ ] Re-run npm audit after the upgrade and verify the lockfile is committed and reproducible.
- [ ] Split the 617.25 kB minified JavaScript chunk (172.34 kB gzip) using route-level lazy loading/manual chunks where appropriate.
- [ ] Investigate Recharts zero-width/zero-height warnings emitted by frontend tests.
- [ ] Update GitHub Actions setup-node/checkout usage for the announced Node 20 action deprecation warning.

- [x] Re-run the complete integration pipeline with npm audit reporting enabled; CI run #99 passed all three jobs.


## Frontend maintenance update — 2026-11-10

- [x] Upgrade Vitest to 4.1.12; integration CI run #107 reports zero npm audit vulnerabilities.
- [x] Lazy-load dashboard Recharts panels; initial JS reduced from 617.25 kB to 179.05 kB (54.73 kB gzip), with a separate 438.31 kB charts chunk (118.18 kB gzip).
- [x] Verify backend tests, frontend tests/build, and populated PostgreSQL migration together; all passed in CI run #107.
- [ ] Remove or properly simulate Recharts chart dimensions in jsdom tests to eliminate zero-width/zero-height warnings.
- [ ] Update GitHub Actions checkout/setup-node from v4 to Node 24-compatible action versions to remove Node 20 deprecation warnings.
- [ ] Add and commit a reproducible frontend package lockfile; current workflow still runs npm install without a committed lockfile.


### Reproducible frontend install — 2026-11-12
- [x] Confirm no frontend lockfile exists and keep CI on `npm install` rather than breaking it with `npm ci`.
- [x] Add a temporary CI artifact upload for the lockfile generated by npm install on the next successful run.
- [ ] Retrieve a genuine `frontend/package-lock.json` from CI or a network-enabled Node environment and commit it.
- [ ] Change CI to `npm ci` only after the committed lockfile is present.
- [ ] Verify the lockfile install, Vitest 4.1.12, zero-vulnerability audit, frontend tests/build, backend tests, and PostgreSQL migration in one complete run.
- **Blocker:** the current execution environment cannot reach GitHub/npm and has no cached npm metadata; offline lockfile generation failed. No fabricated lockfile was added.


### Reproducible frontend install — completed 2026-11-12
- [x] Generate and commit the genuine npm lockfile at `frontend/package-lock.json` (lockfileVersion 3).
- [x] Replace `npm install` with `npm ci` in frontend CI.
- [x] Remove temporary lockfile-bootstrap permissions and branch-write logic; CI is read-only again.
- [x] Verify clean install, Vitest 4.1.12, zero-vulnerability npm audit, frontend tests/build, backend tests, and populated PostgreSQL migration; all passed in CI run #114.


## Foundation 0.2 — Accounts & Ledger (domain implementation)

- [x] Add immutable FinancialAccount identities with owner, account type, currency, and open/closed status.
- [x] Define normal balance rules for assets, expenses, liabilities, equity, and income.
- [x] Add immutable positive debit/credit postings and balanced single-currency JournalEntry values.
- [x] Add append-only LedgerBook posting, derived balances, asset-to-asset transfers, and exact one-time reversals.
- [x] Add accounting golden-case and rejection tests; Foundation 0.2 CI run [#136](https://github.com/matteojose3112-bit/aurelius/actions/runs/44185872151) passed backend and frontend jobs.
- [ ] Review idempotency, concurrency, account closure, backdating, reconciliation, and persistence constraints before API/database integration.
- [ ] Keep production migrations, deployments, and external financial actions behind explicit approval.


## Foundation 0.2.1 — Ledger Hardening (design baseline)

- [x] Define owner + operation + idempotency-key semantics, canonical request hashing, safe retries, and conflict behavior.
- [x] Specify atomic posting, deterministic account lock order, unique reversal enforcement, and append-only database protections.
- [x] Define account closure/settlement and audited reopening boundaries.
- [x] Define effective_date vs recorded_at, open-period backdating, and future-dated transaction policy.
- [x] Specify reconciliation matching, duplicate imports, unmatched items, and correction scenarios.
- [x] Review PR #10 / #12 compatibility: legacy Numeric(14,2) remains separate from canonical 0/2/3-exponent multi-currency ledger money.
- [ ] Select canonical database money representation and finalize PostgreSQL schema/API contracts.
- [ ] Implement disposable PostgreSQL atomicity, idempotency, reversal-race, rollback, and owner-isolation tests.

Design contract: [LEDGER_HARDENING_0.2.1.md](docs/finance/LEDGER_HARDENING_0.2.1.md). No persistence, API, migration, production write, or deployment is included in this phase.


## Foundation 0.3 — Persistence Architecture (proposed design)

- [x] Propose canonical money storage: integer minor units in `NUMERIC(38,0)`, with immutable currency exponent/version snapshots and explicit 38-digit bound.
- [x] Design PostgreSQL entities for currency definitions, accounts, journal entries, postings, idempotency records, audit events, and accounting periods.
- [x] Specify database-enforced balance, ownership, currency, reversal, append-only, and period invariants.
- [x] Define atomic posting transaction and retry-safe idempotency behavior.
- [x] Sketch exact-string API contracts for journal creation and account balances.
- [x] Define disposable PostgreSQL concurrency, rollback, isolation, and immutability test gates.
- [x] Record future Ollama provider-adapter architecture and AI safety boundary.
- [ ] Confirm auth principal/FK model and target PostgreSQL version.
- [ ] Implement schema/models/migrations in a disposable development environment.
- [ ] Implement API contracts and pass the PostgreSQL test plan.
- [ ] Review legacy migration/reconciliation strategy before any integration.

Design references: [ADR-003](docs/architecture/ADR-003-canonical-money-storage.md), [schema/API](docs/architecture/FOUNDATION_0.3_POSTGRESQL_SCHEMA_API.md), [test plan](docs/architecture/FOUNDATION_0.3_PERSISTENCE_TEST_PLAN.md), [Ollama note](docs/architecture/AI_PROVIDER_OLLAMA_FUTURE.md). No production persistence or deployment is part of this design milestone.


## Foundation 0.3 — global persistence groundwork

- [x] Inspect existing authentication and migration model: users.id is INTEGER; JWT sub serializes this ID; legacy ownership FKs are INTEGER.
- [x] Decide first-release financial owner FK uses INTEGER users.id, with ON DELETE RESTRICT; no duplicate identity system.
- [x] Inspect database stack: SQLAlchemy 2.0.36, Alembic 1.14.0, psycopg 3.2.3; SQLite local default and PostgreSQL URL support.
- [x] Confirm repository does not pin hosted PostgreSQL major version; set PostgreSQL 16 as disposable CI baseline only, subject to hosted-version verification before future deployment.
- [x] Select initially deferred PostgreSQL constraint triggers for commit-time balanced journal/ownership/currency/reversal validation, plus append-only runtime protections.
- [x] Define global-market separation: ISO 4217 currencies, historical currency snapshots, instrument/venue identifiers, FX observations, timezones, locale, and jurisdiction are distinct.
- [ ] Implement global currency registry ingestion and immutable seed snapshots.
- [ ] Implement SQLAlchemy persistence models and Alembic migration in isolated development/CI.
- [ ] Add PostgreSQL 16 service and real concurrency/rollback tests.
- [ ] Implement atomic posting/idempotency service; keep API integration gated on test results.

References: [Global Markets Architecture](docs/architecture/FOUNDATION_0.3_GLOBAL_MARKETS.md), [Auth/DB inspection](docs/architecture/FOUNDATION_0.3_AUTH_DATABASE_INSPECTION.md), [schema/API](docs/architecture/FOUNDATION_0.3_POSTGRESQL_SCHEMA_API.md).


## Foundation 0.3 — currency registry implementation

- [x] Bundle SIX ISO 4217 List One current release (178 codes; 165 with published minor-unit precision).
- [x] Preserve List Three historical currency facts as 152 code/withdrawal-date records across 137 distinct codes, retaining jurisdiction-specific withdrawal dates.
- [x] Add a maintainer updater that downloads official SIX XML and deterministically refreshes the bundled snapshot; no runtime network lookup.
- [x] Replace the eight-currency hard-coded Money exponent map with registry-backed precision, including 0/2/3/4 decimal units.
- [x] Keep historical exponent unknown when List Three does not publish it; never infer it from a modern replacement currency.
- [x] Add registry, Money, and XML-importer regression tests.
- [ ] Validate the implementation through GitHub Actions before proceeding to ORM/migration work.
- [ ] Add an extensible asset/instrument master for commodities, securities, derivatives, crypto, prediction contracts, real assets, liabilities, and benchmarks.

Coverage design: [Global Asset Coverage](docs/architecture/FOUNDATION_0.3_GLOBAL_ASSET_COVERAGE.md). Registry code: `backend/app/domain/currency.py`; snapshot: `backend/app/domain/data/iso4217_snapshot.json`; updater: `backend/scripts/update_iso4217_snapshot.py`.


## Foundation 0.3 — persistence model and migration implementation

- [x] Define SQLAlchemy models for immutable currency definitions, financial accounts, journals, postings, idempotency, audit, periods, and international owner preferences.
- [x] Keep authenticated owner IDs as INTEGER references to users.id; use UUID IDs for ledger aggregates.
- [x] Add composite foreign keys that enforce journal/account owner and currency-definition consistency.
- [x] Add an idempotent registry seed service that never updates or deletes published reference rows.
- [x] Add Alembic migration for the ledger persistence schema.
- [x] Add PostgreSQL-only deferred journal-balance/reversal triggers, append-only guards, account-identity protection, and period-overlap exclusion.
- [ ] Validate the migration and model/seed tests in CI.
- [ ] Add PostgreSQL 16 service and integration tests for deferred triggers, direct-write bypass resistance, concurrent idempotency/reversal, rollback, and locking.
- [ ] Implement atomic posting transaction service after PostgreSQL behavior is proven.

Implementation branch: feat/aurelius-foundation-0.3-ledger-persistence-models. No hosted database migration or API integration is included.


## Foundation 0.3 — PostgreSQL validation

- [x] Add a disposable PostgreSQL 16 service to GitHub Actions.
- [x] Run the real Alembic migration against PostgreSQL 16 in CI.
- [x] Add PostgreSQL integration tests for balanced/unbalanced journals, reversal symmetry, closed accounts, append-only protection, fractional precision, 38-digit bounds, rollback, and concurrent idempotency uniqueness.
- [x] Latest full CI run passed: PostgreSQL 16 migration + 16 integration tests, SQLite backend suite, frontend tests, and frontend build.
- [ ] Expand concurrency coverage to posting-service replay/conflict semantics, competing reversals, account close/post races, and timeout-after-commit retry.


## Foundation 0.3 — atomic posting engine

- [x] Add server-owned PostJournalCommand and validated integer PostingLine inputs.
- [x] Claim idempotency key and persist journal, postings, audit event, and response atomically.
- [x] Lock account rows in deterministic UUID order and re-check owner/currency/open status.
- [x] Enforce configured open accounting periods; when no periods are configured, period policy remains inactive.
- [x] Implement same-key/same-payload replay and changed-payload conflict.
- [x] Implement exact reversal service with source-journal row locking and one-reversal protection.
- [ ] Validate posting service with PostgreSQL 16 same-key concurrency, competing reversals, rollback/retry, and closed-period tests.
- [ ] Integrate service into API routes only after the service test suite passes.

- [x] PostgreSQL 16 CI passed with 25 integration tests covering posting/reversal concurrency, rollback after partial writes, and account close/post serialization.
- [x] Full CI passed on the latest service branch head: PostgreSQL integration, SQLite backend, frontend tests, and frontend build.

- [x] Add bounded retry for transient PostgreSQL serialization/deadlock/connection errors, reusing the same idempotency key to handle unknown commit outcomes.


## Current Foundation 0.3 delivery status

- [x] SIX ISO 4217 current/historical registry and deterministic maintainer updater.
- [x] SQLAlchemy persistence models and Alembic migration for currency definitions, accounts, journals, postings, idempotency, audit, periods, and owner preferences.
- [x] PostgreSQL 16 deferred constraints, append-only guards, exact minor-unit check, and period exclusion.
- [x] Atomic idempotent journal posting, exact reversals, deterministic account locking, and bounded retry with the same idempotency key.
- [x] Authenticated versioned FastAPI endpoints for currency discovery, account management, native-currency balances, journal posting/reads, and reversals.
- [x] PostgreSQL 16 CI validates migration, database invariants, posting/reversal concurrency, rollback, and API owner isolation.
- [ ] Add global instrument master and unit ontology for securities, futures, options, commodities, crypto, prediction/event contracts, real assets, and liabilities.
- [ ] Add exchange MIC/listing/trading-calendar registry and contract specifications.
- [ ] Add FX observations and reproducible multi-currency portfolio valuation.
- [ ] Add provider adapters with provenance, licensing, freshness, coverage, and jurisdiction checks.
- [ ] Add portfolio holdings, lots, corporate actions, risk analytics, research, and prediction calibration.

The legacy FinTrack transaction/budget/goal API remains in place and continues to use float-backed legacy models. It must be migrated separately; the new Aurelius v1 ledger API does not silently reinterpret legacy rows.


## Foundation 0.4 — global instrument master

- [x] Define open asset-class and instrument-type vocabularies rather than closed enums.
- [x] Add exact rational unit registry with mass, volume, energy, security, derivative, token, event-contract, and area dimensions.
- [x] Add context-required unit semantics for commodity-dependent units such as bushel.
- [x] Add illustrative global commodity asset catalog for precious/industrial metals, energy, agriculture, and electricity.
- [x] Add namespaced/time-bounded instrument identifier domain (ISIN/FIGI/provider IDs).
- [ ] Persist unit definitions, assets, instruments, identifiers, MIC venues, and listings.
- [ ] Add futures/options, bond, and prediction/event contract specifications.
- [ ] Add licensed market-data/FX provider adapters and immutable observations.
- [ ] Add owner holdings, lots, valuation snapshots, and portfolio analytics.

- [x] Add MIC/timezone venue and time-bounded listing domain types.
- [x] Add explicit derivative/futures, bond, and prediction-contract specification types.

- [x] Add provenance-aware market observation and separately calibrated forecast domain records; persistence, scoring, and provider adapters remain pending.


## Foundation 0.4 — global instrument persistence

- [x] Add persistence models for unit/asset/instrument definitions and identifiers.
- [x] Add MIC venue and time-bounded listing tables.
- [x] Add derivative, bond, and prediction contract specification tables.
- [x] Add provider source/licensing metadata, immutable market observations, forecast records, and separate forecast resolutions.
- [x] Add exact rational unit/asset seed service and dry-run-by-default CLI.
- [x] Validate Alembic 0003 on SQLite and PostgreSQL 16 CI; verify temporal exclusion and append-only guards.
- [ ] Add provider adapter contracts and licensed market-data ingestion.
- [ ] Add holdings, position lots, portfolio valuation, and market risk.

- [x] Validate Alembic 0003 on SQLite and PostgreSQL 16 CI; verify temporal exclusion and append-only guards. Latest run: 31 PostgreSQL integration tests and 125 backend tests passed.


## Foundation 0.5 — provider adapters and licensed ingestion

- [x] Define provider capabilities, coverage, data request, observation, and license-policy contracts.
- [x] Require explicit region/venue/global coverage; no implicit assumption of worldwide availability.
- [x] Add license-aware PostgreSQL ingestion service with source/terms validation and exact Decimal values.
- [x] Add observation deduplication by provider source, source record ID, observation type, and instrument.
- [ ] Add first live reference/market data provider after terms, coverage, and licensing review.
- [ ] Add rate limits, retries, circuit breakers, credential handling, and provider health monitoring.
- [ ] Add source freshness/staleness policy and coverage reports.

- [x] Validate provider ingestion and migration 0004 on PostgreSQL 16: 34 integration tests passed; backend suite 134 passed; frontend tests/build passed.

- [x] Review global provider candidates, coverage, pricing, and licensing; recommend ECB reference FX as first live adapter and dataset-level World Bank CC-BY review as second.

## Foundation 0.6 — portfolio lots and transaction-safe settlement

- [x] Persist owner-scoped portfolios, immutable trade executions, acquisition lots, disposal allocations, and position serialization rows.
- [x] Add PostgreSQL execution service with replay protection, deterministic lot replay, oversell rejection, and concurrent-position serialization.
- [x] Refactor ledger posting to expose a caller-session primitive while preserving the transaction-owning journal API.
- [x] Prove the session-bound posting primitive participates in the caller's rollback boundary (journal, postings, audit, and idempotency all roll back together).
- [x] Document proposed BUY/SELL cash-flow accounting, fee treatment, trade-date assumption, partial-fill identity, realized gain/loss, cash sufficiency, and cross-domain transaction/idempotency requirements (see docs/architecture/FOUNDATION_0.6_TRADE_SETTLEMENT_ACCOUNTING.md).
- [x] Add owner-scoped portfolio-to-ledger mapping persistence with composite owner/currency constraints, distinct account roles, and PostgreSQL role/status validation (see docs/architecture/FOUNDATION_0.6_SETTLEMENT_ACCOUNT_MAPPING.md).
- [x] Add a caller-owned PostgreSQL mapping resolver that locks the portfolio, mapping, and four ledger accounts in deterministic order and revalidates use-time status/type/owner/currency.
- [x] Add pure shared currency-scale conversion and deterministic minor-unit residual-allocation primitives with explicit immutable exponent input, ROUND_HALF_UP, and the ledger 38-digit bound.
- [x] Integrate the immutable currency exponent into new lot-engine executions with deterministic multi-lot disposal allocation; preserve historical executions under precision-policy v1.
- [ ] Complete PostgreSQL validation for multi-lot residuals, partial disposals, precision-version replay, and historical v1 rebuild stability.
- [ ] Implement one transaction coordinator for trade execution, lot facts, cash journals, and audit/idempotency records.
- [ ] Add cross-domain PostgreSQL integration tests for successful settlement, duplicate replay, rollback injection, cash sufficiency races, and concurrent fills.
- [ ] Only after those gates pass, design read-only portfolio APIs and valuation/FX reporting.

**Boundary:** the current lot service remains long-only and spot-style. It records fills, not orders, and does not yet post corresponding cash/fee/FX journals. No portfolio trading API should be exposed until cross-domain atomicity and accounting semantics are proven.

- [x] Refactor portfolio execution to expose a caller-owned-session primitive while preserving the existing transaction-owning wrapper.
- [x] Prove portfolio execution, acquisition lot, and audit event all roll back with the caller's outer transaction in PostgreSQL.
- [ ] Build the transaction coordinator that invokes both session-bound primitives and writes the investment and cash sides atomically.


## Foundation 0.6 — atomic trade settlement coordinator

**Integrated:** PR #38 — `feat/aurelius-foundation-0.6-atomic-settlement-coordinator` (CI run #536 passed; merge into main follows dependency integration).

- [x] Define BUY/SELL trade-date journal policy, fee treatment, account roles, and transaction/idempotency contract.
- [x] Add explicit owner-scoped portfolio-to-ledger account mappings (PR #33).
- [x] Add transaction-bound mapping resolution and deterministic account locks (PR #34).
- [x] Add currency-exponent-aware minor-unit conversion and deterministic lot allocation (PR #35).
- [x] Expose caller-owned-session primitives for portfolio execution and ledger posting (PRs #30–#31).
- [x] Add the first coordinator composing both services inside one caller-owned PostgreSQL transaction (PR #38).
- [x] Enforce a locked brokerage cash-balance check before a new BUY settlement.
- [x] Add PostgreSQL integration coverage for BUY/SELL journals, idempotent replay, insufficient-cash rejection, concurrent BUY serialization, and caller-owned rollback.
- [x] Verify the full CI suite on the coordinator head (run #536: backend, frontend, migrations, and PostgreSQL 16 integration all passed).
- [x] Verify mapping/account lock order against session-bound portfolio and ledger services; preserve the historical precision-policy snapshot during settlement.

**Boundary:** the coordinator records already-executed fills only. It does not submit orders, connect to brokers, move money, expose a public trade endpoint, or perform production writes. The caller owns the transaction and its commit/rollback.
