# Aurelius — AI Financial Intelligence & Investment Operating System

> **Formerly FinTrack.** Aurelius is being developed as an evidence-first financial partner for personal finance, accounting, market research, portfolio analysis, risk assessment, and financial education. The existing FinTrack application is the starting foundation—not a completed Aurelius product.

**Transformation status (2026-11-21):** Aurelius has progressed through Foundations 0.1–0.7. The ISO 4217 registry, durable ledger, authenticated posting API, provider-neutral market-data framework, global instrument/observation foundations, and long-only portfolio lot engine are implemented across the reviewed branch stack. Foundation 0.6 now includes owner-scoped portfolio-to-ledger account mappings (PR #33), transaction-bound mapping resolution (PR #34), currency-scale lot allocation (PR #35), and the first atomic trade-settlement coordinator (draft PR #38). The public read-only Aurelius showcase is deployed separately; it uses synthetic data and is disconnected from accounts, APIs, brokers, and live market data. No broker orders, real-money execution, cash transfers, or production financial writes are enabled.

**Operating principle:** deterministic financial calculations and traceable source data come first; AI interprets and challenges evidence, but never invents facts or silently executes financial actions.

## Current Aurelius development status — 2026-11-21

- The ISO 4217 registry replaced the original eight-code hard-coded money map and preserves current and historical definitions from the SIX Maintenance Agency snapshot.
- The first authenticated ledger API uses exact integer-minor-unit strings, owner-derived authorization, idempotent posting, derived balances, and exact reversals.
- The global instrument master distinguishes assets, instruments, identifiers, units, venues, listings, contract specifications, observations, and forecasts.
- The provider-neutral adapter framework is merged in PR #25. Provider ingestion and FX reference adapters remain feature-branch work; no live production feed or paid data plan is configured.
- Long-only portfolio lot accounting supports FIFO/LIFO/specific-lot allocation in the deterministic domain. PR #27 adds this domain slice; the current stacked feature branches add owner-scoped persistence tables and a PostgreSQL-only atomic execution service; the new service/concurrency suite passed PostgreSQL 16 CI run #410 (42 integration tests), along with backend and frontend validation.
- PR #19–#24 and #26–#27 are not all merged; review each branch and its dependencies before integration. PR #25 is merged. The portfolio-lot persistence branch is separate and draft.
- PR #38 is the active coordinator branch, stacked on PR #35 and its mapping/session-composition dependencies. It is draft and unmerged; CI and PostgreSQL cross-domain acceptance remain required before considering the milestone complete.
- The public Aurelius showcase is a separate synthetic-data static site. The existing API/database and legacy authenticated FinTrack service are not being changed by this feature branch.
- No broker order execution, cash transfer, production financial write, or production database migration is enabled.
- See [Money and Currency Contract](docs/finance/MONEY_CONTRACT.md), [Account and Ledger Contract](docs/finance/ACCOUNT_LEDGER_CONTRACT.md), [Global Markets Architecture](docs/architecture/FOUNDATION_0.3_GLOBAL_MARKETS.md), and [Portfolio Lot Persistence](docs/architecture/FOUNDATION_0.6_PORTFOLIO_LOT_PERSISTENCE.md).

## Aurelius transformation — assessment baseline

### What is reusable
- React/Vite/Tailwind dashboard and existing transaction, budget, goal, and chart workflows.
- FastAPI, SQLAlchemy, PostgreSQL/SQLite development setup, Alembic migrations, and authenticated account boundaries.
- Argon2 password hashing, JWT authentication, CSV export, and existing automated test patterns.
- Render API/static-site/database Blueprint as a deployment starting point, subject to lifecycle and security review.

### Current limitations to resolve
- The default `main` branch remains the older FinTrack MVP. The separate integration hardening PR #12 and its component changes remain open draft work; the Aurelius planning merge did not merge or deploy them. Foundation 0.1 is being developed separately.
- The UI is JavaScript (not TypeScript) and concentrated in a large App.jsx; component boundaries and domain-level state need to improve before the product expands.
- The legacy application data model has users, transactions, budgets, and goals. Foundation 0.2 now defines domain-only accounts and ledger entries, but these are not yet persisted or exposed through the API; liabilities workflows, holdings, lots, dividends, trades, benchmarks, and reconciliation remain unimplemented.
- The draft money work uses Numeric(14,2) but currently converts API amounts back to JSON floats. That is not a sufficient multi-currency precision contract. Aurelius must define currency-specific minor-unit precision and an exact API representation before portfolio features.
- No market-data ingestion, source provenance, freshness tracking, AI orchestration, forecasting, paper-trading engine, scheduled research, or prediction ledger exists.
- Existing tests are a useful MVP base, but do not constitute browser E2E, provider contract, accounting golden-case, model-evaluation, or production security coverage.

### Proposed architecture
A modular monolith first: one FastAPI deployment with clear domain modules and provider adapters, backed by PostgreSQL. Keep deterministic calculations independent from AI. Add background scheduling only when ingestion and monitoring require it.

1. **Domain layer:** money/currency, ledger, accounts, portfolio, market data, risk, research, thesis, prediction, and audit models.
2. **Application layer:** explicit use cases for recording transactions, reconciling accounts, valuing holdings, generating research, and reviewing decisions.
3. **Data-provider adapters:** normalized interfaces for prices, fundamentals, macroeconomic series, filings, and news; store source, retrieval time, period, currency, and raw/normalized provenance.
4. **Intelligence layer:** central orchestrator plus specialist roles. Agents receive bounded, read-only tools and structured evidence; they do not directly mutate financial records or access brokerage execution.
5. **Review layer:** independent reviewer challenges assumptions and evidence; outputs distinguish verified facts, estimates, assumptions, and model interpretations.
6. **Presentation/API layer:** typed API contracts and focused React components for each department.
7. **Operations layer:** append-only audit events, scheduled jobs, health checks, retries, observability, backup/restore, and access controls.

Do not introduce a distributed microservice fleet or a heavyweight agent framework at this stage. Start with a Python orchestration service and typed specialist interfaces; choose a framework only after a small benchmark demonstrates a concrete benefit. PostgreSQL full-text search is sufficient initially; add vector search only when a measured retrieval use case warrants it.

### Preliminary data-provider direction
- **SEC EDGAR:** preferred source for U.S. issuer filings and XBRL facts. Public JSON APIs need no API key; requests must identify the client, respect fair-access limits, and run server-side because data.sec.gov does not support browser CORS. See https://www.sec.gov/search-filings/edgar-application-programming-interfaces and https://www.sec.gov/about/developer-resources.
- **FRED:** preferred for U.S. macroeconomic time series. Requires an API key; some underlying series carry third-party rights. Follow the terms and display the required non-endorsement notice: https://fred.stlouisfed.org/docs/api/terms_of_use.html.
- **Financial Modeling Prep (FMP):** promising broad fundamentals/news candidate. Its current published individual tiers include a free Basic tier (250 calls/day), Starter shown at $19/month billed annually, Premium $49/month billed annually, and Ultimate $99/month billed annually. Coverage differs by tier; displaying or redistributing data requires a separate licensing agreement. Pricing and terms must be rechecked before selection: https://site.financialmodelingprep.com/pricing-plans.
- **Alpha Vantage:** useful prototype alternative; free access is 25 requests/day, and real-time/15-minute delayed U.S. data is premium-only. Not sufficient alone for broad autonomous monitoring on the free tier: https://www.alphavantage.co/support/api-key/ and https://www.alphavantage.co/premium/.
- **Massive (formerly Polygon):** strong U.S. market-data candidate. Its current individual Stocks tiers list Basic free (5 calls/minute, 2 years EOD), Starter $29/month (15-minute delayed), Developer $79/month, and Advanced $199/month (real-time). Individual-use plans are explicitly distinguished from business plans; verify commercial/display rights before any product use: https://massive.com/pricing.

**Initial recommendation:** build provider-neutral adapters; prototype with SEC + FRED + one free EOD market-data tier using synthetic/demo fixtures first. Do not purchase a subscription or commit to a provider until coverage, exchange licensing, display/redistribution rights, latency, reliability, and total cost are tested against Aurelius's actual use cases.

### Reliability contract
Every market datum and research claim should carry source/provider, instrument or series identifier, currency/unit, observation period, retrieval timestamp, market timestamp, delay/freshness status, and any transformation applied. Missing or stale data must be visible. AI-generated conclusions must link to the evidence they use. Forecasts must be timestamped and immutable once issued, with outcomes recorded separately.

### Safety boundary
Aurelius is initially read-only with respect to external financial institutions. No brokerage execution, automated orders, money movement, or autonomous portfolio rebalancing. AI output is decision support and education—not a guarantee, regulated advisory service, or substitute for professional tax/legal advice.

---

## Original FinTrack application reference

The sections below document the existing FinTrack MVP and its current setup while the transformation is developed.


**A modern personal finance and budgeting platform.**

FinTrack brings income, expenses, budgets, savings goals, and financial insights into one clear workspace, with a responsive React interface and Python API.

![Status](https://img.shields.io/badge/status-Render%20Blueprint%20provisioned-0d9488)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61dafb)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688)
![License](https://img.shields.io/badge/license-MIT-blue)

## Features

- **Overview dashboard** — income, expenses, balance, and savings at a glance.
- **Transactions** — record, categorize, search, and remove income or expenses.
- **Budgets** — set monthly category limits and monitor spending.
- **Savings goals** — define targets and track contributions.
- **Analytics** — monthly cash flow and category spending visualizations.
- **Data export** — download transaction history as CSV.
- **Account security** — register and sign in with hashed passwords and expiring JWT access tokens.
- **Private workspaces** — transactions, budgets, savings goals, summaries, and exports are scoped to the authenticated account.
- **Responsive UI** — designed for desktop and mobile screens.
- **Automated tests** — frontend interaction tests and backend API integration tests.

## Technology

| Layer | Stack |
| --- | --- |
| Frontend | React, JavaScript, Vite |
| Styling | Tailwind CSS |
| Charts | Recharts |
| Icons | Lucide React |
| Backend | Python, FastAPI |
| Database | PostgreSQL in production, SQLite locally, SQLAlchemy |
| Validation | Pydantic, email-validator |
| Authentication | Argon2 password hashing, JWT (PyJWT) |
| Frontend tests | Vitest, React Testing Library, jsdom |
| Backend tests | pytest, FastAPI TestClient, httpx |
| Migrations | Alembic |
| Hosting | Render Blueprint (API, static frontend, PostgreSQL) |
| CI | GitHub Actions |

## Project structure

```
fintrack/
├── frontend/
│   ├── src/           # React application and component tests
│   └── package.json
├── backend/
│   ├── app/           # FastAPI application and database models
│   ├── tests/         # API integration tests
│   ├── migrations/    # Alembic database migrations
│   ├── alembic.ini
│   └── requirements.txt
├── .github/workflows/ # Continuous integration
├── render.yaml        # Render deployment blueprint
└── README.md
```

## Run locally

### Requirements
- Node.js 18+
- Python 3.10+

### 1. Start the API

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`. Copy `backend/.env.example` as a reference and set a strong, private `FINTRACK_SECRET_KEY` outside local development. Production mode refuses to start without this secret. Database tables are managed with Alembic migrations (`alembic upgrade head`); the Render build runs this command automatically.

### 2. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). The Vite development server proxies `/api` requests to FastAPI. Create an account or sign in from the FinTrack welcome screen. Access tokens remain in memory and are cleared on sign-out or page reload. For a hosted frontend, set `VITE_API_BASE_URL` to the full API base URL, for example `https://fintrack-api.onrender.com/api`.

## Deploy with Render

**Live application:** [Open FinTrack](https://fintrack-web-int6.onrender.com)

The Render Blueprint has been provisioned and the live services have completed their initial deployments.

- Blueprint: `fintrack` (ID: `exs-dbkhp88m7kps7396um8g`)
- API: [https://fintrack-api-l1wa.onrender.com](https://fintrack-api-l1wa.onrender.com)
- Frontend: [https://fintrack-web-int6.onrender.com](https://fintrack-web-int6.onrender.com)
- Database: `fintrack-db` (PostgreSQL 18, Render free tier)
- Source: `matteojose3112-bit/aurelius`, branch `main`

### Verified deployment checks

- [x] Render API service deployed successfully.
- [x] Render frontend build and publish completed successfully after merge commit `1549d9641a036cc72cd479b54624289b11fd6dd5` (authentication API URL fix).
- [x] API health endpoint returned HTTP 200 in Render service health-check logs.
- [x] PostgreSQL database is available and contains the expected `users`, `transactions`, `budgets`, `goals`, and `alembic_version` tables.
- [x] Frontend production build completed successfully.
- [ ] Manually verify account registration and login in the live browser.
- [ ] Complete live end-to-end checks for transactions, budgets, savings goals, CSV export, and account isolation.

The Blueprint generates `FINTRACK_SECRET_KEY`, links the PostgreSQL connection string, configures CORS, and runs Alembic migrations during the API build. The frontend uses `VITE_API_BASE_URL` to call the separately deployed API. The live deployment is operational at the URLs above; user-facing authentication and finance workflows still require a browser acceptance test.

**Production caution:** the current PostgreSQL database is on Render's free tier and is scheduled to expire on December 2, 2026. Do not rely on it for durable financial records. Upgrade to a paid database and configure backups before using real financial data. The frontend build also reported six npm audit vulnerabilities (three moderate, one high, two critical) and a bundle-size warning; these should be reviewed before a production-grade release.

## Run tests

Frontend tests:

```bash
cd frontend
npm install
npm run test -- --run
```

Backend tests (from the repository root):

```bash
pip install -r backend/requirements.txt
pytest -q backend/tests
```

Frontend tests use a mocked API and cover dashboard rendering, transaction search, transaction-form launch, budget progress and creation entry, savings-goal progress and contribution entry, and offline feedback. Key navigation, search, dialogs, and progress indicators expose accessible names and semantics. Backend tests use isolated in-memory SQLite and cover core API workflows without touching local finance data.

GitHub Actions runs frontend tests and a production build, plus backend compile and integration checks, on pushes and pull requests targeting `main`.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register` | Register and receive an access token |
| POST | `/api/auth/login` | Sign in with email and password (OAuth2 form fields) |
| GET | `/api/auth/me` | Current authenticated account |
| GET | `/api/summary` | Dashboard totals and chart data (authenticated) |
| GET / POST | `/api/transactions` | List and create transactions |
| DELETE | `/api/transactions/{id}` | Delete a transaction |
| GET / POST | `/api/budgets` | List and create budgets |
| GET / POST | `/api/goals` | List and create savings goals |
| POST | `/api/goals/{id}/contribute` | Add to a savings goal |
| GET | `/api/export/transactions` | Export transactions as CSV |

## Development roadmap

- [x] Repository and application foundation
- [x] FastAPI service and SQLite data layer
- [x] Responsive dashboard and transaction workflows
- [x] Budget creation and spending progress
- [x] Savings-goal creation and contribution workflows
- [x] Analytics and CSV export foundation
- [x] Automated backend API integration tests
- [x] Frontend interaction test foundation
- [x] GitHub Actions frontend and backend test integration
- [x] Budget and savings-goal workflow coverage
- [x] Accessible search, navigation state, dialog controls, and progress indicators
- [ ] Broader accessibility audit and keyboard-flow review
- [x] Account registration, login, and JWT authentication
- [x] User-scoped transactions, budgets, goals, summaries, and exports
- [x] PostgreSQL production configuration and Alembic initial migration
- [x] Production secret enforcement, configurable CORS, and database health check
- [x] Render Blueprint created and API, static site, and PostgreSQL resources provisioned
- [ ] Confirm API and frontend builds finish successfully in Render
- [ ] Verify live API health check and end-to-end frontend workflows
- [ ] Production security review, persistent paid database, backups, and legacy data import path

## Project principles

FinTrack is designed around clarity, useful financial context, and responsible data handling. It is an educational portfolio project, not financial advice. The local setup uses SQLite; production uses PostgreSQL. Alembic creates the current schema on a fresh database. The initial migration is not a conversion of an older pre-2.0 SQLite database: back up legacy data and plan a dedicated import before attempting to reuse it. FinTrack is a portfolio project, not financial advice or a bank. Do not enter sensitive real-world financial information until the deployment, access controls, backups, and operational security have been independently reviewed. The Render Blueprint currently provisions free-tier resources for demonstration; Render free PostgreSQL databases expire after their trial period and free web services may sleep. Choose paid persistent hosting and verify backups before relying on the service.

## License

Released under the [MIT License](LICENSE).

## Documentation review — 2026-11-03

Documentation review — 2026-11-03: FinTrack is deployed on Render with API health and database schema availability previously verified. Live browser acceptance for registration/login and finance workflows remains outstanding. The PostgreSQL free-tier database is scheduled to expire 2026-12-02; do not rely on it for durable financial records. Upgrade, backups, security review, dependency findings, and bundle-size warning remain release concerns.


## Engineering work in review — 2026-11-09

The following focused hardening changes are available as **open draft pull requests**. They are not part of the deployed `main` branch until reviewed and merged:

| PR | Change | Current status |
| --- | --- | --- |
| [#3](https://github.com/matteojose3112-bit/aurelius/pull/3) | Account-isolation regression tests | Draft; CI passed |
| [#4](https://github.com/matteojose3112-bit/aurelius/pull/4) | Production API URL and CORS configuration | Draft; CI passed; no Render Blueprint sync performed |
| [#5](https://github.com/matteojose3112-bit/aurelius/pull/5) | CSV spreadsheet-formula injection protection | Draft; CI passed |
| [#7](https://github.com/matteojose3112-bit/aurelius/pull/7) | Login and registration rate limiting | Draft; CI passed; shared rate-limit storage and proxy behavior need deployment planning |
| [#10](https://github.com/matteojose3112-bit/aurelius/pull/10) | Fixed-precision monetary storage and Decimal calculations | Draft; populated SQLite migration test passed; PostgreSQL migration test passed in #12 CI |
| [#12](https://github.com/matteojose3112-bit/aurelius/pull/12) | Combined release-hardening integration validation | Draft; CI run #99 passed backend, frontend, PostgreSQL migration, and dependency-audit reporting |

Individual PRs and the combined integration branch have passed their current CI checks. No PR in this list has been merged or deployed. The populated SQLite and disposable PostgreSQL migration tests passed; a verified production backup and restore path are still mandatory before any production migration. Do not treat the live deployment as containing these changes.

## Documentation review — 2026-11-09

Release readiness remains in progress. The immediate engineering focus is integration testing across the draft PRs, followed by live browser acceptance testing, dependency/security review, and a durable database/backup plan before the Render free PostgreSQL expiry on 2026-12-02. No production migration, Render configuration change, or deployment was performed as part of this documentation update.



## Release validation update — 2026-11-10

- PR #10 now includes a populated legacy SQLite migration regression test. GitHub Actions run [#91](https://github.com/matteojose3112-bit/aurelius/actions/runs/42920839088) passed both backend and frontend jobs, including the seeded pre-migration database upgrade, data rounding/preservation, index and foreign-key checks.
- PR #12 is an open draft integration vehicle combining PRs #3, #5, #7, and #10. Its initial combined CI run [#92](https://github.com/matteojose3112-bit/aurelius/actions/runs/42921329034) passed backend tests, Alembic fresh-schema migration, frontend tests, and production build. A small follow-up whitespace-handling correction was committed after that run; the latest head still needs a fresh CI confirmation.
- PR #4's Render URL/CORS diff was reviewed: the configured frontend API URL matches the deployed API, and production CORS is restricted to the deployed frontend origin. No Blueprint sync or live configuration change was performed.
- PostgreSQL migration behavior was reviewed statically: Alembic batch operations use native column alteration on PostgreSQL. No non-production PostgreSQL migration execution has yet been performed, so that validation remains open.
- Rate limiting still defaults to process-local memory. Multi-instance production requires private shared Redis/Valkey storage and verified proxy/client-IP handling.
- Frontend dependency audit findings and the bundle-size warning have not been re-audited in this pass.
- All PRs remain drafts; no changes have been merged or deployed. The free PostgreSQL database expiry remains 2026-12-02, with durable hosting, backup, and restore testing still required.


- The latest integration CI run [#96](https://github.com/matteojose3112-bit/aurelius/actions/runs/42921838065) passed all three jobs: backend suite, frontend tests/build, and a disposable PostgreSQL service migration test. The PostgreSQL test upgraded seeded legacy Float records to Numeric(14,2) and verified rounded values, retained indexes, foreign keys, and migration revision.


### Current frontend audit and bundle review — 2026-11-10
The integration CI audit reconfirmed **6 dependency vulnerabilities**: 3 moderate, 1 high, and 2 critical. The affected packages are Vitest and its transitive test-tool dependencies (Vitest, tinypool, Vite, esbuild, vite-node, and @vitest/mocker); they are in frontend devDependencies, not runtime dependencies. npm reports a fix path through Vitest 4.1.12, which is a major-version upgrade and needs compatibility testing before adoption. The production build also reports a 617.25 kB minified JavaScript chunk (172.34 kB gzip). Frontend tests emit Recharts zero-width/zero-height chart warnings; tests still pass. These remain engineering follow-ups, not reasons to claim a failed build.

Integration CI run [#99](https://github.com/matteojose3112-bit/aurelius/actions/runs/42922254791) subsequently passed all three jobs again and included the current npm audit summary.


## Frontend dependency and bundle improvements — 2026-11-10

- Upgraded Vitest from 2.1.8 to 4.1.12. Latest integration CI [run #107](https://github.com/matteojose3112-bit/aurelius/actions/runs/42924734014) reports **zero npm audit vulnerabilities** (previously 6: 3 moderate, 1 high, 2 critical).
- Extracted the Recharts dashboard panels into a lazy-loaded DashboardCharts component. The initial application JavaScript bundle dropped from 617.25 kB to **179.05 kB** (54.73 kB gzip); charts are loaded separately in a **438.31 kB** chunk (118.18 kB gzip) when the authenticated dashboard renders.
- Backend tests, frontend tests, frontend production build, and populated PostgreSQL migration CI all passed in run #107.
- Frontend tests still emit Recharts zero-width/zero-height warnings in jsdom; this is a test-layout warning and does not fail the suite. GitHub Actions also reports Node 20 deprecation warnings for checkout/setup-node v4, which remains a maintenance follow-up.


### Reproducible frontend install status — 2026-11-12
- The frontend still has no committed `package-lock.json`; CI therefore remains on `npm install`. We did **not** switch to `npm ci`, because that would fail without a valid lockfile.
- Added a temporary artifact-upload step to integration PR #12 so the next successful frontend CI run can preserve the lockfile generated by `npm install`. No CI run or artifact was available for the latest workflow commit at review time.
- Local lockfile generation was attempted with `npm install --package-lock-only --offline`, but the environment has no cached npm registry metadata; network access to GitHub/npm is unavailable here. No synthetic or incomplete lockfile was committed.
- Required next action: retrieve the generated CI artifact (or generate the lockfile in a network-enabled Node environment), commit the genuine lockfile, switch CI to `npm ci`, and rerun all jobs.


### Reproducible frontend install completed — 2026-11-12
- Committed the generated npm lockfile at `frontend/package-lock.json` (lockfileVersion 3; 153,615 bytes) to the integration branch through the CI runner. It is a genuine npm-generated lockfile, not a hand-built approximation.
- Replaced the temporary bootstrap/artifact workflow with standard `npm ci`; removed the workflow's temporary write permission and branch-push logic.
- Clean-install verification passed in [integration CI run #114](https://github.com/matteojose3112-bit/aurelius/actions/runs/43336240992): `npm ci`, npm audit (zero vulnerabilities), all 6 frontend tests, frontend production build, backend tests, and populated PostgreSQL migration all passed.
- The frontend build remains split: initial JS 179.05 kB (54.73 kB gzip); dashboard charts 438.31 kB (118.18 kB gzip). Recharts still logs chart-dimension warnings in jsdom, but tests pass.


## Foundation 0.2.1 — ledger hardening

The domain-only Foundation 0.2 ledger is now accompanied by a hardening contract covering owner-scoped idempotency, retry-safe duplicate handling, atomic posting and concurrency controls, account closure, effective dating/backdated-entry policy, reconciliation, and correction workflows. See [Ledger Hardening Contract](docs/finance/LEDGER_HARDENING_0.2.1.md). This is a design baseline only: the in-memory ledger is not durable or concurrency-safe, and no persistence/API/migration work has begun. The review also establishes that legacy PRs #10 and #12 retain a two-decimal contract and must not be treated as the canonical multi-currency ledger storage design.


## Foundation 0.3 — Persistence Architecture (proposed)

Foundation 0.3 now has a proposed exact-money persistence decision and PostgreSQL schema/API design. Canonical posting magnitudes use integer minor units stored as bounded `NUMERIC(38,0)`, with immutable currency exponent/version snapshots; this avoids binary floats and the narrower `BIGINT` ceiling. The schema design covers accounts, journal entries, postings, idempotency, audit events, and accounting periods, including deferred cross-row balance enforcement, append-only protections, and atomic retry-safe posting. See [ADR-003](docs/architecture/ADR-003-canonical-money-storage.md), [PostgreSQL Schema/API](docs/architecture/FOUNDATION_0.3_POSTGRESQL_SCHEMA_API.md), and the [Persistence Test Plan](docs/architecture/FOUNDATION_0.3_PERSISTENCE_TEST_PLAN.md). This remains design-only: no models, migrations, API routes, database, or deployment have been created.

Future AI integration can use the locally installed Ollama through a provider adapter; see [AI Provider / Ollama Architecture](docs/architecture/AI_PROVIDER_OLLAMA_FUTURE.md). AI remains advisory and cannot bypass deterministic ledger validation or user approval.


## Global markets and internationalization

Aurelius is being designed for international users and markets, not one country or base currency. Foundation 0.3 separates login identity, financial ownership, jurisdiction, ISO 4217 cash currencies, non-fiat asset units, instruments/listings, exchanges, FX observations, and reporting preferences. Account currencies are independent of an owner's reporting currency; historical currency definitions are versioned and immutable. See [Global Markets Architecture](docs/architecture/FOUNDATION_0.3_GLOBAL_MARKETS.md), [Auth/Database Inspection](docs/architecture/FOUNDATION_0.3_AUTH_DATABASE_INSPECTION.md), and the [Global PostgreSQL Schema/API](docs/architecture/FOUNDATION_0.3_POSTGRESQL_SCHEMA_API.md).


## Foundation 0.3 — Currency registry implementation

The first executable Foundation 0.3 slice now replaces the former eight-currency hard-coded exponent map with a versioned registry snapshot derived from the official SIX ISO 4217 List One and List Three XML releases. The bundled release contains **178 current codes (165 with published minor-unit exponents)** and **152 historical code/withdrawal-date records covering 137 distinct historical codes**. Historical withdrawal dates are retained per jurisdiction (for example, the Russian ruble was withdrawn at different dates across former user jurisdictions). The refresh utility downloads SIX's official XML directly; the application itself has no runtime network dependency. See [currency registry domain](backend/app/domain/currency.py), [snapshot updater](backend/scripts/update_iso4217_snapshot.py), and [global asset coverage](docs/architecture/FOUNDATION_0.3_GLOBAL_ASSET_COVERAGE.md).

`Money` now reads precision from the registry and supports current ISO entries with published exponents, including zero-, two-, three-, and four-decimal monetary units. ISO List Three does not publish historical exponents; Aurelius preserves those historical identifiers and withdrawal facts but deliberately does not guess their precision. Fund/reference codes and cash-account eligibility will be separated from the generic monetary-unit arithmetic contract. This implementation slice has tests added; CI validation is pending. SQLAlchemy persistence models, Alembic migrations, PostgreSQL persistence, and API integration remain outstanding.


## Foundation 0.3 — isolated ledger persistence implementation

The next Foundation 0.3 slice now defines SQLAlchemy persistence models for versioned currency definitions, financial accounts, journal entries/postings, idempotency records, audit events, accounting periods, and international owner preferences. The new Alembic migration is stacked after the legacy initial schema and uses the existing INTEGER users.id identity with RESTRICT ownership FKs. Composite foreign keys prevent cross-owner and cross-currency postings. PostgreSQL-only deferred constraint triggers validate balanced journals and exact reversals at commit; append-only triggers protect posted history and currency reference data. The currency registry seed service is idempotent and refuses to mutate an existing published definition. See the [global PostgreSQL schema/API](docs/architecture/FOUNDATION_0.3_POSTGRESQL_SCHEMA_API.md) and [global asset coverage](docs/architecture/FOUNDATION_0.3_GLOBAL_ASSET_COVERAGE.md).

This is still an isolated implementation branch. SQLite migration/schema tests do not prove PostgreSQL trigger, locking, or concurrency behavior. A disposable PostgreSQL 16 CI service and real integration tests remain the next validation gate. No hosted database, Render resource, production record, API route, or deployment has been touched.


## PostgreSQL validation gate — added

A disposable PostgreSQL 16 GitHub Actions service now runs the real Alembic migration and ledger constraint integration tests separately from the SQLite backend suite. The PostgreSQL job exercises deferred balance/reversal triggers, immutable history, fractional-minor-unit rejection, 38-digit bounds, rollback, and concurrent idempotency-key uniqueness. The latest full CI run passed, including the disposable PostgreSQL 16 migration and integration job: **16 PostgreSQL integration tests passed**, alongside the backend suite and frontend tests/build. This validates the current migration and database guards in PostgreSQL 16 CI, not the existing hosted database. No hosted database is involved.


## Foundation 0.3 — atomic posting service

The next implementation slice adds an application-level PostgreSQL posting service. It claims idempotency keys and writes journal headers, posting lines, audit events, and the final replayable response in one transaction. It locks affected accounts in deterministic UUID order, validates ownership/currency/status and configured accounting periods, and supports exact reversals serialized on the source journal. Same-key/same-payload requests replay the stored response; changed payloads conflict. This service is not connected to FastAPI routes yet. See backend/app/persistence/posting_service.py.

The latest full CI run passed with **25 PostgreSQL 16 integration tests**, the SQLite backend suite (including posting-command validation), and frontend tests/build. PostgreSQL coverage includes concurrent same-key replay, competing reversals, account-close/post serialization, failure injection after posting rows are flushed, and atomic rollback. The service remains unexposed to API routes pending review of its transaction contract.



The posting service also performs up to three bounded retries for PostgreSQL serialization failures, deadlocks, and connection failures, always reusing the same idempotency key. This makes retry after an unknown commit outcome safe: a retry either replays the committed result or executes after the original transaction rolled back.


## Foundation 0.3 — versioned ledger API

The tested persistence and posting service is now exposed through authenticated FastAPI routes under /v1. The first API surface includes currency discovery, owner-scoped account creation/listing, native-currency balance derivation, journal posting, journal reads, and exact reversals. JWT context supplies ownership; the client cannot choose owner_id. All money inputs use integer minor-unit strings. Ledger routes require PostgreSQL.

After Alembic upgrade, seed the immutable currency registry explicitly:

- Dry run: from backend/, run python -m scripts.seed_currency_registry
- Apply to the configured development database: python -m scripts.seed_currency_registry --apply
- Production additionally requires --allow-production. No seed command was executed against any hosted database in this work.

PostgreSQL 16 CI has validated the persistence migration, deferred constraints, posting/reversal transactions, and API flow. The existing FinTrack float-based endpoints remain legacy and are not silently rewritten by the new API. Global instrument/commodity/derivative/prediction-market master data and provider adapters remain future milestones.


The latest PostgreSQL 16 API integration run passed **27 tests**, including a fail-closed check that account creation is unavailable until the explicit currency-registry seed has been applied. The full backend and frontend CI suites also pass on the validated API code.


## Foundation 0.4 — global asset and unit ontology

Aurelius is expanding beyond cash accounting into a global multi-asset reference system. The first domain slice adds an open asset-class vocabulary, generic instrument definitions/identifiers, and an exact unit registry. The illustrative commodity catalog covers gold, silver, platinum, palladium, WTI/Brent crude, natural gas, copper, aluminium, wheat, corn, soybeans, coffee, cocoa, and electricity. Unit conversions use exact rational arithmetic; contextual units such as bushels cannot be converted without commodity/contract context.

This is domain groundwork, not yet a persisted instrument master or market-data feed. The next step is PostgreSQL persistence for assets, instruments, identifiers, venues/MICs, listings, and derivative/bond/prediction contract specifications. No market prices, listings, contract expiries, or trading access are fabricated.

The reference catalog also includes representative equity issuers, sovereign debt, ETFs, Bitcoin/Ether, real estate, prediction events, mortgage liabilities, benchmarks, FX pairs, private equity, and derivatives. These are identity/ontology examples only, not market listings or prices.

The domain now also defines MIC/timezone-aware market venues, time-bounded venue listings, and explicit futures/derivative, bond, and prediction-contract specifications. These contracts retain lifecycle dates, units, tick/contract terms, coupon/day-count terms, resolution sources, and settlement rules.

Market observations and Aurelius forecasts are also separate domain records: observations retain source and observed/retrieved timestamps, while forecasts retain model/version, probability, horizon, evidence, and later resolution. Market-implied probabilities are not treated as ground truth or as Aurelius model forecasts.


## Foundation 0.4 — global reference persistence

The next persistence slice adds tables for units, global assets, instruments, identifiers, MIC venues, time-bounded listings, derivative/futures specs, bond terms, prediction contracts, provider licensing/coverage, immutable market observations, and forecast records/resolutions. It uses global reference IDs rather than user ownership; user holdings will reference these instruments later. PostgreSQL prevents overlapping identifier/listing validity windows and protects reference/observation history with append-only triggers.

Seed illustrative unit and asset definitions explicitly after migration:

- Dry run: from backend/, run python -m scripts.seed_global_reference_data
- Apply to the configured development database: python -m scripts.seed_global_reference_data --apply
- Production additionally requires --allow-production.

No market prices, provider subscriptions, broker access, listings, or futures expiries are included in the seed. The instrument master remains separate from owner portfolios and from the cash ledger.


PostgreSQL 16 CI validates the instrument-master migration, temporal exclusion constraints, append-only guards, reference seeding, derivative/bond/prediction specifications, market observations, and forecast resolution. Latest validated run: **31 PostgreSQL integration tests passed; 125 backend tests passed** (31 PostgreSQL-only cases are skipped in the SQLite backend job). Frontend tests/build also pass.


## Foundation 0.5 — provider adapter framework

Aurelius now has provider-neutral contracts for global market/reference data, explicit coverage declarations, license policies, exact Decimal observations, and a PostgreSQL ingestion service. Ingestion checks provider identity/terms, purpose, geographic rights, instrument/type/time coverage, unit/currency references, and deduplicates immutable observations by provider record identity. Fetching occurs outside the database transaction; persistence is atomic.

No live provider, API key, paid subscription, or market feed is configured. Provider-specific adapters will be added only after coverage and licensing are verified. See docs/architecture/FOUNDATION_0.5_PROVIDER_ADAPTER_FRAMEWORK.md.


Latest Foundation 0.5 CI passed: **34 PostgreSQL 16 integration tests**, **134 backend tests** (34 PostgreSQL-only tests skipped in SQLite mode), frontend tests, and frontend build. The fake-provider integration verifies license rejection before fetch, source/terms/coverage checks, and duplicate observation replay without creating duplicate rows.

Provider candidate research is documented in docs/architecture/FOUNDATION_0.5_PROVIDER_CANDIDATE_REVIEW.md. The proposed first live adapter is ECB reference FX, followed by carefully licensed World Bank macro datasets. Broad market subscriptions remain deferred; no provider has been connected or purchased.

## Foundation 0.6 — portfolio lot persistence and transaction composition

Aurelius now has owner-scoped investment portfolios, immutable trade-execution and acquisition-lot records, immutable disposal allocations, and position-lock rows for serialized long-only spot-style position updates. The execution service records already-executed fills only; it does not submit orders. It rebuilds lot state from immutable history and protects execution replay/concurrency in PostgreSQL.

The ledger posting layer now also exposes `post_journal_in_session(session, command, idempotency_key)`. This composition primitive requires an active caller-owned transaction and never commits, rolls back, closes, or retries that session. The existing `post_journal(...)` API remains as a transaction-owning wrapper. This is the required foundation for a future trade-settlement service to persist holdings, cash journals, fees, FX legs, and audit records in one transaction.

This is an enabling refactor, not completed trade settlement: the portfolio execution service is not yet coupled to cash accounting. No trading API, broker connection, order placement, cash movement, or production operation is enabled. See `docs/architecture/FOUNDATION_0.6_PORTFOLIO_LOT_PERSISTENCE.md` and the session-bound posting tests.

## Foundation 0.6 — caller-owned portfolio transactions

The portfolio lot execution layer now exposes `apply_portfolio_execution_in_session(session, owner_id, actor_id, execution, ...)` alongside the original transaction-owning wrapper. The new primitive requires an active PostgreSQL transaction and does not commit, roll back, close, or retry the caller's session. This makes portfolio facts and ledger journals composable under one transaction coordinator. A PostgreSQL regression verifies that rolling back the caller transaction removes the execution, acquisition lot, and audit event together.

The two session-bound primitives are now available as building blocks; the actual coordinator that writes a trade and its corresponding cash/fee/FX journals together is still the next step. See PR #31. No public trading endpoint is enabled.


## Foundation 0.6 — trade settlement accounting specification

The next milestone is documented in `docs/architecture/FOUNDATION_0.6_TRADE_SETTLEMENT_ACCOUNTING.md`. It defines proposed BUY/SELL journal mechanics, fee treatment, owner-scoped account mapping requirements, replay/transaction rules, cash-sufficiency controls, settlement-date assumptions, and the precision/rounding gate between exact lot decimals and integer minor-unit ledger postings.

This is a design contract only. The account mapping and shared rounding policy do not yet exist, so the settlement coordinator is not implemented and no trade API, broker connection, order placement, or cash movement is enabled.

## Foundation 0.6 — explicit settlement account mapping

Added the owner-scoped portfolio_ledger_account_mappings persistence model and Alembic revision 0006. Each portfolio/brokerage-cash-account/currency scope now has explicit, distinct cash, investment-control, realized-gain, and realized-loss account references. Composite foreign keys enforce owner and exact currency-snapshot consistency; a PostgreSQL trigger validates account roles and OPEN status when mappings are created or changed. See docs/architecture/FOUNDATION_0.6_SETTLEMENT_ACCOUNT_MAPPING.md.

This is a schema foundation only: there is no mapping API, automatic account selection, trade coordinator, journal posting, or cash movement. The coordinator must re-check account status at use time. Shared lot/money rounding and reconciliation remains a separate blocker.

Validation on the draft mapping PR head: **154 backend tests passed** (46 PostgreSQL-only cases skipped in SQLite mode), **46 PostgreSQL 16 integration tests passed**, and frontend tests/build passed. The PostgreSQL job applies migration 0006 and runs the new mapping integration tests. No production migration was run.


The mapping resolver now exposes a caller-owned-session operation that locks the active portfolio, the exact mapping, and all four ledger accounts in deterministic UUID order. It revalidates ownership, currency, account roles, and OPEN status at use time; it does not commit or close the caller's transaction.


## Foundation 0.6 — currency-scale allocation primitives

Added a pure domain module, `portfolio_money.py`, for exact Decimal-to-minor-unit conversion using an explicitly supplied currency exponent, `ROUND_HALF_UP`, the ledger's 38-digit minor-unit bound, and deterministic weighted residual allocation. The caller supplies the immutable currency exponent captured for the trade; this helper does not consult a mutable/current registry or infer a currency. Unit tests cover zero-, two-, and three-decimal scales, negative values, invalid inputs, overflow, and order-independent allocation.

The lot engine now uses the immutable currency snapshot for new precision-policy v2 executions. Acquisition basis is quantized to currency scale; SELL gross proceeds, fees, and cost basis are allocated across lots in integer minor units with deterministic residual handling. Historical v1 executions retain legacy exact-Decimal rebuild behavior, so this change does not silently rewrite old lot facts.


The lot engine now supports precision-policy version 2 for new persisted executions. It uses the immutable currency snapshot's minor-unit exponent, quantizes acquisition basis, and allocates rounded gross proceeds, sale fees, and cost basis across lots deterministically with exact residuals. A persisted version flag preserves historical version-1 replay/rebuild semantics; historical financial facts are not rewritten. CI run #495 passed: 170 backend tests passed, 49 skipped in the SQLite suite, 49 PostgreSQL 16 integration tests passed, and frontend tests/build passed. Additional partial-disposal, v1 historical replay, and residual stress cases remain a gate before coordinator implementation.


## Foundation 0.6 — atomic trade settlement coordinator

The PostgreSQL-only settlement coordinator now records an already-executed BUY/SELL fill and its cash-ledger journal in one caller-owned transaction. It uses explicit owner-scoped account mappings, deterministic account locks, immutable currency precision, execution-derived journal idempotency, BUY fee capitalization, SELL net proceeds/cost basis/realized gain or loss, and an owner-timezone trade date. New BUY fills are rejected unless the locked brokerage cash account can fund principal plus fees.

**Validation:** CI run #536 passed on the coordinator head: backend suite, frontend tests/build, SQLite migration, PostgreSQL 16 migration, and the PostgreSQL integration suite. Coordinator integration tests cover BUY journal posting and replay, SELL basis/proceeds/gain, insufficient cash, caller rollback, and concurrent BUYs sharing a brokerage cash account.

**Boundary:** this records fills that have already executed. It does not submit orders, connect to brokers, transfer money, expose a public trading endpoint, or write production financial data. No production migration or deployment was performed.
