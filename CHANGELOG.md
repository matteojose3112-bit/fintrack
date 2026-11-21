## [Unreleased] — Foundation 0.6 Atomic Portfolio Lot Service — 2026-11-17

### Added
- Added PostgreSQL-only atomic trade-fill persistence service with transaction advisory locks for execution IDs and row locks for owner-scoped positions.
- Added deterministic replay from immutable execution history, exact lot/disposal writes, audit events, same-payload replay, changed-payload conflict, and rejection of backdated fills pending a rebuild workflow.
- Preserved one currency-registry snapshot per position to prevent a later ISO release from splitting one holding's identity.
- Added PostgreSQL tests for buy/sell, realized gain/loss, idempotency, oversell rollback, and competing oversell attempts.

### Validation and boundaries
- GitHub Actions run #410 passed: PostgreSQL 16 integration 42 passed, backend suite passed, frontend tests/build passed, and both SQLite and PostgreSQL Alembic upgrades passed.
- The service records already-executed fills only. No broker orders, cash-ledger coupling, tax engine, public portfolio API, hosted database migration, Render change, or deployment.

## [Unreleased] — Foundation 0.6 Portfolio Lot Persistence — 2026-11-17

### Added
- Added owner-scoped investment portfolio, immutable trade execution, acquisition lot, disposal allocation, and position-lock SQLAlchemy models.
- Added Alembic revision 0005 with composite owner/account/portfolio/instrument/currency references, exact unscaled NUMERIC values, PostgreSQL finite-value guards, and append-only triggers.
- Added PostgreSQL integration coverage for exact decimal persistence, cross-owner account rejection, immutable lot/disposal facts, scoped allocations, and mutable operational lock rows.
- Updated CI to execute the new PostgreSQL portfolio-lot integration test module.
- Documented the persistence invariants and next gates in FOUNDATION_0.6_PORTFOLIO_LOT_PERSISTENCE.md.

### Validation and boundaries
- CI validation for this feature branch is pending; do not treat the migration or PostgreSQL tests as passed until the new head run completes.
- Schema/domain only: no portfolio application service, public portfolio API, cash-ledger settlement coupling, tax engine, broker connection, order placement, hosted database migration, Render change, or deployment.
- The in-memory lot domain remains the deterministic calculation reference; remaining balances are derived from immutable acquisition lots and disposal allocations.

## [Unreleased] — Foundation 0.2 Accounts & Ledger — 2026-11-17\n\n### Added\n- Added immutable FinancialAccount domain identities with owner scope, account classification, currency validation, lifecycle status, and accounting normal-side rules.\n- Added immutable balanced single-currency journal entries and strictly positive debit/credit postings.\n- Added append-only in-memory ledger posting, derived account balances, same-owner same-currency asset transfers, and exact one-time reversal entries.\n- Added accounting golden-case tests for opening balances, income, expenses, transfers, reversals, ownership isolation, currency matching, and invalid postings.\n- Added the Account and Ledger Contract, including persistence design gates and explicit FX exclusions.\n\n### Validation and boundaries\n- Foundation 0.2 code and tests are committed on feat/aurelius-foundation-0.2-accounts-ledger; GitHub Actions run [#136](https://github.com/matteojose3112-bit/aurelius/actions/runs/44185872151) passed both backend and frontend jobs for this branch. Backend compile, Alembic SQLite upgrade, full pytest suite, frontend tests, and production build completed successfully.\n- Domain-only implementation: no API, SQLAlchemy model, Alembic migration, frontend, Render configuration, production data, or deployment changed.\n- The in-memory ledger is not a durable audit store or concurrency-safe persistence implementation.\n\n## [Unreleased] — Money primitive hardening — 2026-11-17

### Added
- Added exact `Money.from_minor_units()` construction for currencies with zero-, two-, and three-decimal exponents.
- Canonicalized rounded zero values so negative zero cannot leak into serialized financial output.
- Added regression tests for minor-unit round trips, invalid minor-unit types, and canonical zero.

### Validation
- New changes are committed on `feat/aurelius-foundation-0.1`; CI for the updated head is pending.

## [Unreleased] — Foundation 0.1 CI validation — 2026-11-17

### Validation
- GitHub Actions run [#125](https://github.com/matteojose3112-bit/aurelius/actions/runs/44184005586) passed both jobs on `feat/aurelius-foundation-0.1`.
- Backend job passed dependency installation, Python compile check, Alembic SQLite upgrade, and the complete `backend/tests` pytest suite.
- Frontend job passed dependency installation, frontend tests, and production build.
- This validates the current feature-branch baseline only; it does not merge the branch, change production API/database contracts, or authorize deployment.

### Boundaries
- `Money` remains an isolated domain primitive; legacy API, SQLAlchemy models, migrations, and frontend monetary arithmetic are not yet migrated.
- No production data, Render infrastructure, secrets, deployment, paid provider, brokerage connection, or money movement changed.

## [Unreleased] — Aurelius Foundation 0.1 — 2026-11-17

### Added
- Renamed the GitHub repository to `matteojose3112-bit/aurelius`; legacy FinTrack application and Render identifiers remain unchanged pending a separate compatibility review.
- Added an infrastructure-independent `Money` value object using Python `Decimal`, explicit currency exponents, fixed-scale decimal-string serialization, integer minor units, and same-currency arithmetic.
- Added unit tests for currency scales, `ROUND_HALF_UP` normalization, non-finite values, float rejection, unknown currencies, and cross-currency arithmetic.
- Added the money/currency contract, ADR-0001 architecture decision, and Foundation 0.1 implementation status.

### Validation and boundaries
- Feature branch: `feat/aurelius-foundation-0.1`; CI validation is pending.
- Existing API, database models, migrations, frontend arithmetic, and production data have not been changed.
- No Render configuration, infrastructure, secrets, deployment, paid provider, brokerage connection, or money movement changed.
- Real-money trading and brokerage execution remain disabled.

## [Unreleased] — Aurelius transformation assessment — 2026-11-17

### Product direction
- Announced the transformation of FinTrack into **Aurelius**, an evidence-first AI financial intelligence and investment operating system.
- Defined the nine target departments, specialist-agent responsibilities, prediction accountability, thesis tracking, independent review, and read-only safety boundary.
- Recommended a modular-monolith architecture with deterministic financial/domain services, provider adapters, typed AI specialist interfaces, source provenance, and append-only audit/prediction records.

### Repository assessment
- Reviewed the default-branch tree, backend/frontend implementation, tests, Render Blueprint, open issues, branches, and open draft pull requests.
- Confirmed that main is behind integration PR #12: fixed-precision financial fields, populated migration tests, frontend lockfile, npm ci, and related hardening remain unmerged draft work.
- Identified high-priority financial-model gaps: currency absent from records, Numeric(14,2) does not cover all currency scales, and the integration API converts Decimal values to JSON floats.
- Identified missing account/ledger/portfolio/market-data/AI/prediction/scheduling capabilities; these are planned, not implemented.
- Recorded preliminary provider screen for SEC EDGAR, FRED, FMP, Alpha Vantage, and Massive, including current public pricing/limits and licensing caveats.

### Safety and release status
- Documentation-only transformation plan; no application code, database, Render infrastructure, secrets, or production data changed.
- No PR was merged and no deployment or paid service was initiated.
- Real-money trading and brokerage execution remain disabled.

# Changelog

All notable project changes are documented here.

## [Unreleased] - 2026-11-09

### In review — draft pull requests, not yet released
- **PR #3:** Added account-isolation regression coverage for financial records, summaries, exports, and ownership checks.
- **PR #4:** Proposed production frontend API URL and restricted CORS configuration; no Render Blueprint sync has been performed.
- **PR #5:** Added CSV escaping for user-controlled text that could be interpreted as spreadsheet formulas.
- **PR #7:** Added IP-based rate limits for login and registration, with configurable storage support. Multi-instance shared storage and trusted-proxy behavior still require deployment planning.
- **PR #10:** Replaced floating-point monetary storage/calculations with `Numeric(14, 2)` and Python `Decimal`, added an Alembic conversion migration, and expanded monetary regression tests.

### Validation
- Individual CI checks passed for draft PRs #3, #4, #5, #7, and #10.
- Combined integration testing remains outstanding.
- PR #10 still requires populated legacy-data migration coverage and PostgreSQL conversion review before any production migration.

### Release status
- All five pull requests remain open drafts; none is merged or deployed.
- No production data, Render infrastructure, secrets, or live configuration were changed during this work.
- The Render free PostgreSQL database is still scheduled to expire on 2026-12-02; durable hosting, backup, and restore planning remain release blockers.

# Changelog

All notable project changes are documented here.

## [2.2.1] - 2026-11-02

### Fixed
- Corrected frontend authentication requests to use the configured `VITE_API_BASE_URL`, allowing the hosted static frontend to communicate with the separately deployed API.

### Verified
- Render API deployment completed successfully and is marked live.
- Render frontend build and publish completed successfully from merge commit `1549d9641a036cc72cd479b54624289b11fd6dd5`.
- API health checks returned HTTP 200.
- Render PostgreSQL database is available and contains the expected application tables.
- Frontend production build completed successfully.

### Follow-up
- Live browser registration/login and finance workflow acceptance tests remain outstanding.
- Frontend dependency audit reported 6 vulnerabilities (3 moderate, 1 high, 2 critical); review before production-grade use.
- Frontend bundle-size warning remains to be addressed.
- Current free PostgreSQL database is scheduled to expire on 2026-12-02; upgrade and configure backups before storing real financial data.


## [2.2.0] - 2026-11-02

### Added
- Render Blueprint `fintrack` created from the `main` branch using the root `render.yaml`.
- Provisioned the `fintrack-api` FastAPI web service, `fintrack-web` static site, and `fintrack-db` PostgreSQL database resources.
- Added a dedicated deployment roadmap and documented the Render Blueprint ID and verification checklist.

### Documentation
- Updated deployment status to distinguish successful resource provisioning from verified live service availability.
- Added post-deployment checks for the API health endpoint, database connectivity, and frontend account workflows.
- Clarified that public URLs must be confirmed in Render and that free-tier resources are demonstration-only.

### Status
- Render Blueprint and resource provisioning are confirmed. Live API/frontend deployment and end-to-end checks remain pending confirmation in the Render service dashboard.

## [2.1.0] - 2026-11-02

### Added
- PostgreSQL-compatible database connection configuration with local SQLite fallback.
- Alembic schema migration foundation and initial account/finance schema.
- Render Blueprint for the FastAPI service, static React frontend, and managed PostgreSQL database.
- Environment-based frontend API URL and deployment environment examples.
- Production startup guard requiring `FINTRACK_SECRET_KEY`.

### Improved
- Monthly analytics and budget calculations now use portable date ranges across SQLite and PostgreSQL.
- CORS origins are configurable for local and hosted frontend domains.
- API health endpoint verifies database connectivity for hosting health checks.
- Deployment, migration, and free-tier limitations documented.

### Notes
- The initial migration provisions a fresh schema; it does not import legacy pre-2.0 SQLite data.
- Public hosting resources still need to be provisioned through the connected hosting account.

## [2.0.0] - 2026-11-02

### Added
- Account registration and login endpoints with email validation and Argon2 password hashing.
- Signed JWT access tokens with a 30-minute expiration and an authenticated account endpoint.
- User ownership on transactions, budgets, and savings goals.
- Per-account filtering for summaries, budget calculations, goal contributions, and CSV exports.
- Sign-in and registration screens, authenticated API requests, account display, and sign-out.
- Backend tests for registration, login, validation, protected routes, and cross-account data isolation.

### Security
- Passwords are stored as Argon2 hashes rather than plaintext.
- Financial endpoints require a valid bearer token and return only the authenticated user's records.
- The frontend keeps access tokens in memory and clears them on sign-out or reload.
- Production deployments must set a strong `FINTRACK_SECRET_KEY` and use HTTPS.
- Existing pre-2.0 SQLite databases require a backup and a migration/reset plan before use with this schema.

## [1.4.0] - 2026-11-02

### Added
- Expanded frontend tests for budget and savings-goal screens, progress indicators, and modal entry points.
- Accessible labels for transaction search, mobile navigation, and modal close controls.
- Semantic progressbar roles and values for budget usage and savings-goal completion.

### Improved
- Navigation exposes the current page through `aria-current`.
- Frontend tests now verify the accessible names and progress values used by assistive technology.

## [1.3.0] - 2026-11-02

### Added
- Vitest and React Testing Library setup with a jsdom test environment.
- Frontend interaction tests for dashboard data, transaction search, transaction form launch, and API-offline feedback.
- GitHub Actions frontend test execution before the production build.

## [1.2.0] - 2026-11-02

### Added
- Automated FastAPI integration tests for health checks and transaction workflows.
- Coverage for transaction validation, dashboard summaries, budget creation and duplicate protection.
- Coverage for savings-goal creation, contributions, missing-goal handling, and CSV export.
- Isolated in-memory SQLite test fixtures to keep tests separate from local finance data.
- pytest and a compatible httpx test dependency.
- GitHub Actions execution of backend tests on pushes and pull requests to `main`.

## [1.1.0] - 2026-11-02

### Added
- Dedicated budget management screen with category spending progress and remaining limits.
- Budget creation form connected to the FastAPI endpoint.
- Dedicated savings goals screen with target progress.
- Savings goal creation and contribution forms connected to the API.
- Context-aware primary action for transactions, budgets, and savings goals.

## [1.0.0] - 2026-11-02

### Added
- Initial FinTrack repository and project documentation.
- React + Vite frontend with a responsive dark dashboard.
- FastAPI backend with SQLite persistence through SQLAlchemy.
- Transaction creation, listing, and deletion.
- Monthly income and expense summaries with chart-ready analytics.
- Budget and savings-goal API foundations.
- CSV transaction export.
- Local development setup and API documentation through FastAPI Swagger UI.

## [2.2.2] - 2026-11-03

### Documentation
- Refreshed README and roadmap with the current Render deployment, outstanding live acceptance tests, and production-readiness concerns.
- Reaffirmed the 2026-12-02 expiry date for the free PostgreSQL database and the need for a durable upgrade and backups before storing real financial records.
- Kept dependency audit findings, bundle-size work, security review, and live workflow verification visible as open items.



## [Unreleased] - 2026-11-10

### Validation
- Added populated legacy SQLite migration coverage to PR #10; CI run #91 passed backend and frontend jobs.
- Opened draft integration PR #12 combining account isolation, CSV formula protection, authentication rate limiting, and fixed-precision money changes. Initial combined CI run #92 passed; a subsequent small whitespace-handling correction awaits fresh CI confirmation.
- Reviewed PR #4's production API URL and CORS configuration without syncing the Render Blueprint.
- Reviewed the PostgreSQL migration implementation statically; live PostgreSQL migration validation remains outstanding.

### Remaining release requirements
- PostgreSQL populated-data migration execution, rate-limit shared storage/proxy validation, dependency audit and bundle review, live browser acceptance after approved deployment, and durable database backup/restore remain outstanding.
- No PR was merged or deployed, and no production data or infrastructure was changed.


### Migration validation
- Added a disposable PostgreSQL 16 CI service and a populated legacy-data migration regression test to integration PR #12.
- CI run #96 passed backend tests, frontend tests/build, and populated PostgreSQL migration validation, including data rounding, indexes, foreign keys, and Alembic revision.


### Dependency and build review
- Re-ran npm audit in integration CI: 6 findings (3 moderate, 1 high, 2 critical), all within Vitest/dev-tool dependency paths. npm reports a fix through Vitest 4.1.12, requiring a major-version compatibility review.
- Confirmed the frontend production build succeeds but emits a 617.25 kB minified JavaScript chunk (172.34 kB gzip).
- Recorded Recharts chart-dimension warnings from frontend tests and GitHub Actions Node 20 deprecation warnings for follow-up.

- Follow-up integration CI run #99 passed backend, frontend, and disposable PostgreSQL migration jobs while reporting the current dependency audit findings.


## [Unreleased] — 2026-11-10

### Frontend
- Upgraded Vitest from 2.1.8 to 4.1.12; npm audit now reports zero vulnerabilities in integration CI run #107.
- Split the Recharts dashboard panels into a lazy-loaded component. Initial JavaScript bundle reduced from 617.25 kB to 179.05 kB (54.73 kB gzip), with charts in a separate 438.31 kB chunk (118.18 kB gzip).
- Verified the full backend, frontend, and populated PostgreSQL migration CI suite; all three jobs passed in run #107.

### Follow-up
- Recharts still emits jsdom chart-dimension warnings; CI action Node 20 deprecation warnings and a committed frontend lockfile remain maintenance items.


### Reproducible frontend install — 2026-11-12
- Added a temporary CI artifact upload step on integration PR #12 to preserve the genuine lockfile generated by npm install.
- Confirmed a committed lockfile is still absent; CI remains on npm install. The switch to npm ci is intentionally deferred until the lockfile is committed.
- Local offline lockfile generation could not resolve npm packages because registry metadata is not cached and network access is unavailable. No incomplete lockfile was committed; retrieval and validation remain pending.


### Reproducible frontend install — 2026-11-12
- Added the genuine npm-generated `frontend/package-lock.json` (lockfileVersion 3) to the integration branch.
- Switched frontend CI from `npm install` to clean, deterministic `npm ci` and removed temporary workflow write permissions/bootstrap logic.
- CI run #114 passed clean installation, zero-vulnerability npm audit, all frontend tests, frontend production build, backend tests, and populated PostgreSQL migration.


## Post-merge status — 2026-11-17

- Merged Aurelius transformation documentation PR [#13](https://github.com/matteojose3112-bit/aurelius/pull/13) into `main` at merge commit [560348f](https://github.com/matteojose3112-bit/aurelius/commit/560348f18f96827c1bce0fd4d3079cbb5c0730be).
- The merge contains README, ROADMAP, and CHANGELOG updates (461 additions, 2 deletions); GitHub reported two checks passed and no deployment was created.
- Earlier entries in this changelog describe the pre-merge state and are historical. The merged Aurelius planning documents are now on `main`.
- This was documentation-only: no application code, production data, Render infrastructure, secrets, deployment, paid service, or brokerage action changed.
- Follow-up required: reconcile the historical release-hardening statements with the current status of PRs #3–#12 before treating the release baseline as current. Do not infer that merging PR #13 merged or deployed those separate changes.


## Unreleased — Foundation 0.2.1 — 2026-11-17

### Added
- Defined the ledger hardening contract for owner-scoped idempotency, canonical request fingerprints, retry-safe replay, and changed-payload conflicts.
- Specified atomic posting, deterministic account lock order, unique reversal constraints, append-only database protections, account closure, effective dating, and backdated-entry policy.
- Added reconciliation/import-deduplication and correction golden scenarios.
- Reviewed legacy PR #10 and integration PR #12: Numeric(14,2) remains a legacy MVP convention and is not the canonical multi-currency ledger persistence design.

### Status
- Foundation 0.2.1 is a design baseline only. The in-memory ledger remains non-durable and non-concurrency-safe; API, schema, migrations, and PostgreSQL concurrency tests remain future work.
- No merge, deployment, Render change, production data write, brokerage connection, or external financial action was performed.


## Unreleased — Foundation 0.3 — 2026-11-17

### Added
- Proposed canonical integer minor-unit persistence in PostgreSQL `NUMERIC(38,0)` with a hard 38-digit bound and immutable currency exponent/version snapshots.
- Designed logical PostgreSQL schema for currency definitions, accounts, journal entries, postings, idempotency, audit events, and accounting periods.
- Specified atomic posting, deferred balance validation, append-only protection, exact-string API money contracts, and disposable PostgreSQL concurrency tests.
- Documented future Ollama provider-adapter architecture with AI restricted to advisory/draft workflows behind deterministic financial controls.

### Status
- Foundation 0.3 is design-only. No SQLAlchemy models, Alembic migrations, API routes, databases, production data, deployments, or Ollama runtime integration were created.


## Unreleased — Foundation 0.3 global groundwork — 2026-11-17

### Added
- Inspected legacy authentication and migration model; documented INTEGER users.id ownership compatibility.
- Selected PostgreSQL 16 as a disposable CI baseline (hosted database version remains unverified) and deferred constraint triggers for commit-time ledger invariants.
- Expanded the persistence design for international users, ISO 4217 registry versioning, historical currency definitions, FX provenance, global instruments/listings, MIC venues, timezone, locale, and jurisdiction separation.

### Status
- This commit records architecture decisions and inspection only. No ORM models, migrations, API endpoints, local/hosted database changes, Render operations, or deployments were performed.


## Unreleased — Foundation 0.3 currency registry — 2026-11-17

### Added
- Added a bundled, versioned ISO 4217 snapshot based on SIX List One (178 current codes) and List Three (152 jurisdiction/withdrawal-date records across 137 historical codes).
- Added a maintainer-only XML updater that fetches the official SIX List One and List Three sources; the application performs no runtime network calls for currency definitions.
- Replaced the hard-coded eight-currency exponent map with registry-backed Money precision for current ISO monetary units with published exponents.
- Preserved numeric codes as three-character strings, fund flags, country associations, historical withdrawal dates, and unknown historical exponents without guessing.
- Added tests for global currency coverage, 0/2/3/4-decimal units, reference-code rejection, fund/unit metadata, jurisdiction-specific history, and XML parsing.
- Added global asset/instrument coverage architecture for commodities, securities, derivatives, digital assets, real/alternative assets, prediction markets, macro benchmarks, and liabilities.

### Status
- Implementation is committed to an isolated draft feature branch. CI validation is pending. No ORM models, Alembic migrations, PostgreSQL database, API integration, Render changes, or deployment are included in this slice.


## Unreleased — Foundation 0.3 persistence models — 2026-11-17

### Added
- Added SQLAlchemy models for the global currency registry, financial accounts, journal entries, journal postings, idempotency, audit events, accounting periods, and owner reporting preferences.
- Added owner/currency composite foreign keys so postings cannot link a journal and account from different owners or currency definitions.
- Added Alembic migration 0002 for the new ledger persistence schema, with PostgreSQL deferred journal-balance and reversal validation, append-only guards, account identity protection, and accounting-period overlap enforcement.
- Added idempotent currency-registry seeding that preserves immutable published definitions and historical withdrawal-date records.
- Added persistence-model and registry-seed tests.

### Status
- Implementation is isolated on a draft feature branch. CI validation is pending. PostgreSQL concurrency behavior remains unverified until the disposable PostgreSQL 16 test job is added. No hosted database, API, Render configuration, production data, or deployment changed.


## Unreleased — Foundation 0.3 PostgreSQL integration validation — 2026-11-17

### Added
- Added a disposable PostgreSQL 16 service and a dedicated CI job that applies Alembic migrations and runs real database constraint/concurrency tests.
- Added PostgreSQL checks for exact integral minor units, 38-digit posting bounds, deferred journal balancing, reversal symmetry, closed-account rules, append-only records, transaction rollback, and concurrent idempotency-key uniqueness.

### Status
- Latest full CI run passed: PostgreSQL 16 migration and 16 database integration tests, SQLite backend tests, frontend tests, and frontend build. SQLite migration/test success is not treated as PostgreSQL validation. No hosted database or production environment was used.


## Unreleased — Foundation 0.3 atomic posting service — 2026-11-17

### Added
- Added a transaction-owning PostgreSQL posting service that atomically claims idempotency, locks accounts in sorted UUID order, writes journal/postings/audit, completes the replayable result, and commits once.
- Added canonical request hashing, same-key/same-payload replay, and changed-payload conflict behavior.
- Added configured accounting-period checks and exact reversal creation serialized on the source journal.
- Added service-level exceptions for account ownership/status, currency, idempotency, period, and reversal conflicts.

### Status
- Service is implemented but not yet connected to API routes. PostgreSQL concurrency/rollback tests are being added before API integration.

- PostgreSQL 16 CI passed with 25 integration tests, including service-level replay/conflict, competing reversals, account close/post serialization, and failure-injection rollback. Full backend/frontend CI passed on the validated branch head.

- Added bounded three-attempt retry for transient PostgreSQL serialization/deadlock/connection failures. Retries reuse the same idempotency key, so unknown commit outcomes safely replay or execute once.


## Unreleased — Foundation 0.3 versioned ledger API — 2026-11-17

### Added
- Exposed authenticated v1 endpoints for current cash currency discovery, owner-scoped financial account creation/listing, native-currency balance derivation, journal posting/reads, and exact reversals.
- Added strict request schemas using integer minor-unit strings and UUID account identifiers; owner identity comes exclusively from JWT context.
- Added a dry-run-by-default currency registry seed CLI; explicit --apply is required, and production additionally requires --allow-production.
- Added PostgreSQL API integration tests for account creation, idempotent journal posting/replay, balance derivation, journal reads, reversal, authentication, and cross-owner isolation.

### Status
- PostgreSQL 16 migration, persistence, posting service, and initial API integration are validated in CI. No hosted database, registry seed, Render resource, production record, broker, or deployment was touched.

- PostgreSQL 16 API integration now passes 27 tests, including authenticated owner isolation and fail-closed behavior before registry seeding.


## Unreleased — Foundation 0.4 global asset ontology — 2026-11-17

### Added
- Added an extensible asset/instrument domain that distinguishes underlying assets from financial instruments and their identifiers.
- Added exact rational unit definitions for mass, volume, energy, securities, derivatives, tokens, event contracts, and area.
- Added context-required quantity units for commodity-specific measures such as bushels.
- Added an illustrative commodity catalog spanning precious metals, industrial metals, crude oil, natural gas, agriculture, and electricity.
- Added tests for exact unit conversion, dimension mismatch, contextual-unit safety, open asset classes, and time-bounded identifiers.

### Status
- Domain groundwork only. Instrument master persistence, venue/listing registry, contract specs, market observations, data providers, portfolio holdings, and trading are not yet implemented.

- Expanded representative asset examples to include equities, sovereign debt, ETFs, cryptoassets, real estate, prediction events, liabilities, benchmarks, FX pairs, private equity, and derivatives.

- Added market venue/listing, derivative/futures, bond, and prediction/event contract specification domain types with validation for MICs, IANA timezones, contract lifecycle, coupon terms, resolution sources, and timezone-aware deadlines.


## Unreleased — Foundation 0.4 global instrument persistence — 2026-11-17

### Added
- Added SQLAlchemy persistence models and Alembic revision 0003 for unit/asset/instrument masters, namespaced identifiers, MIC venues, time-bounded listings, derivative/bond/prediction contract specs, provider source terms, market observations, and forecasts/resolutions.
- Added PostgreSQL temporal exclusion constraints for overlapping identifier and venue-symbol validity windows.
- Added append-only protection for global reference data, observations, forecasts, and resolutions.
- Added exact immutable unit/asset seed service and a dry-run-by-default CLI with explicit production-write guard.



### Validation
- PostgreSQL 16 integration: 31 passed. Backend suite: 125 passed, 31 PostgreSQL-only tests skipped in SQLite mode. Full frontend tests/build passed on the validated PR head.

### Status
- Foundation 0.4 global reference persistence is implemented and validated in CI. No market-data provider connection, hosted database migration, production seed, Render change, deployment, or trading action was performed.


## Unreleased — Foundation 0.5 provider adapter framework — 2026-11-17

### Added
- Added provider-neutral capability, request, observation, and licensing-policy contracts.
- Added explicit global/regional/venue coverage checks and fail-closed purpose/region licensing.
- Added PostgreSQL-only ingestion service that fetches outside transactions, validates instruments/units/currencies, and inserts immutable observations atomically.
- Added a unique provider-observation deduplication index and Alembic revision 0004.
- Added fake-provider tests for capability matching, licensing, out-of-request rows, and idempotent replay.



### Validation
- PostgreSQL 16 integration: 34 passed. Backend suite: 134 passed, with PostgreSQL-only cases skipped in SQLite mode. Frontend tests and build passed on the validated provider-framework head.

### Status
- Provider-neutral contracts and licensed ingestion are implemented and CI-validated. No live provider adapter, external network fetch, API key, subscription, production source, or production data write was configured.

- Added current provider candidate review covering ECB, World Bank, Twelve Data, CoinGecko, Alpha Vantage, FRED, and Nasdaq Data Link, including current plan limits and data-rights cautions. Recommended ECB reference FX first; no subscriptions or integrations.

## Unreleased — Foundation 0.6 session-bound ledger posting — 2026-11-17

### Added
- Added `post_journal_in_session`, a caller-owned-session primitive that writes the journal, postings, audit event, and idempotency response without committing or closing the transaction.
- Preserved `post_journal` as the transaction-owning, bounded-retry wrapper around the session-bound primitive.
- Added a PostgreSQL integration regression proving an outer transaction rollback removes the journal, postings, audit event, and idempotency claim together.

### Design boundary
- This is the transaction-composition foundation for trade settlement, not yet the trade-to-ledger integration itself. The portfolio lot service still records investment-side facts separately and must be refactored to accept a caller-owned session before a coordinator can commit both domains atomically.
- No trading API, brokerage connection, order placement, production data write, deployment, or infrastructure change was performed.

## Unreleased — Foundation 0.6 session-bound portfolio execution — 2026-11-17

### Added
- Added `apply_portfolio_execution_in_session`, which records the immutable execution, acquisition lot or disposal allocations, position lock update, and audit event within a caller-owned PostgreSQL transaction.
- Preserved `apply_portfolio_execution` as the transaction-owning wrapper for standalone use.
- Added PostgreSQL integration coverage proving an outer rollback removes the execution, acquisition lot, and portfolio audit event together.

### Boundary
- The portfolio and ledger services can now participate in the same caller-owned transaction. A coordinator that invokes both and defines the trade/cash/fee/FX accounting entries is still outstanding; no user-facing trade API is enabled.


## Unreleased — Foundation 0.6 trade settlement accounting specification — 2026-11-18

### Added
- Documented proposed single-currency BUY/SELL journal mechanics, purchase-fee capitalization, sale-fee net-proceeds treatment, realized gain/loss, and worked examples.
- Defined the required owner-scoped mapping between brokerage cash accounts, portfolio investment control accounts, and realized gain/loss accounts.
- Specified trade-date handling, independent partial-fill identity, idempotency, caller-owned transaction composition, cash-sufficiency controls, and required PostgreSQL failure/concurrency tests.
- Identified the blocking precision gate between unscaled Decimal lot accounting and integer minor-unit ledger postings.

### Status and boundaries
- Documentation/design only. The account mapping, shared rounding/reconciliation policy, and settlement coordinator are not implemented.
- No trading API, brokerage connection, order placement, cash movement, production write, deployment, or infrastructure change was performed.

## Unreleased — Foundation 0.6 settlement account mapping — 2026-11-18

### Added
- Added the owner-scoped portfolio_ledger_account_mappings model and Alembic revision 0006.
- Enforced portfolio ownership, same-owner/same-currency account references, unique portfolio/cash/currency scope, and distinct ledger roles with database constraints.
- Added a PostgreSQL trigger requiring an active portfolio and open cash/investment ASSET, realized-gain INCOME, and realized-loss EXPENSE accounts when a mapping is created or changed.
- Added model-level and PostgreSQL integration tests for valid mappings, duplicate scopes, incorrect account roles, and cross-owner references.

### Boundary
- Persistence only. No mapping API, default account inference, coordinator, journal posting, cash sufficiency enforcement, broker integration, production migration, or cash movement is included. The coordinator must re-check account status at use time.

### Validation
- Draft PR CI on the final mapping branch head: 154 backend tests passed (46 PostgreSQL-only cases skipped in SQLite mode); 46 PostgreSQL 16 integration tests passed; frontend tests and build passed. PostgreSQL CI applied migration 0006 and exercised the mapping constraints and role trigger.


## Unreleased — Foundation 0.6 settlement mapping resolver — 2026-11-18

### Added
- Added resolve_portfolio_ledger_mapping_in_session, which requires an active caller-owned PostgreSQL transaction and resolves only the exact owner/portfolio/cash-account/currency mapping.
- Added deterministic row locking (portfolio, mapping, then all financial accounts ordered by UUID) and use-time validation of portfolio status, account ownership, currency, role type, and OPEN status.
- Added PostgreSQL integration coverage for successful role resolution, missing mappings, transaction ownership, and account closure after mapping creation.

### Boundary
- The resolver performs no writes and never commits, rolls back, closes, or retries the caller's Session. Trade settlement and journal posting remain unimplemented.


## Unreleased — Foundation 0.6 currency-scale allocation primitives — 2026-11-18

### Added
- Added pure Decimal-to-minor-unit conversion using an explicitly supplied currency exponent and ROUND_HALF_UP.
- Added exact conversion back from integer minor units and a 38-digit ledger bound.
- Added deterministic weighted minor-unit allocation: stable key ordering, floor allocation, and exact final residual assignment.
- Added unit coverage for zero-, two-, and three-decimal currencies, negative amounts, float/non-finite rejection, overflow, and input-order-independent residual allocation.

### Boundary
- The primitive deliberately does not look up a current currency registry definition; the caller must supply the immutable exponent snapshot captured for the trade.
- Existing portfolio lot/disposal facts are not yet quantized through this helper. Snapshot propagation and lot-engine integration remain required before settlement coordination.
- No trade coordinator, journal posting, API, broker integration, or cash movement is included.


## Unreleased — Foundation 0.6 lot precision integration — 2026-11-18

### Added
- Added accounting precision policy versioning to immutable trade executions. Existing rows default to v1; new fills use v2.
- Integrated the immutable currency-definition minor-unit exponent into new lot-engine executions.
- Quantized acquisition lot basis to currency scale using ROUND_HALF_UP.
- Allocated SELL gross proceeds, fees, and aggregate cost basis across disposal lots using stable lot identifiers and exact residual assignment.
- Rejected sale fees exceeding rounded gross proceeds before lot mutation.
- Added domain and PostgreSQL service tests for currency-scale acquisition basis and allocation behavior.

### Boundary
- Historical v1 executions retain their prior exact-Decimal rebuild semantics; no historical lot facts are rewritten.
- CI run #495 passed: 170 backend tests passed, 49 skipped in the SQLite suite, 49 PostgreSQL 16 integration tests passed, and frontend tests/build passed. Additional multi-lot partial-disposal and historical v1 replay stress cases remain follow-up coverage.
- No cash journal, settlement coordinator, production migration, broker integration, or cash movement is included.


## [Unreleased] — Foundation 0.6 Atomic Trade Settlement Coordinator — 2026-11-21

### Added
- Added a PostgreSQL-only coordinator that composes already-executed portfolio fills and cash-ledger journals inside one caller-owned transaction.
- Reused the owner-scoped settlement mapping resolver, session-bound portfolio execution, and session-bound ledger posting primitives.
- Added deterministic execution-derived journal idempotency, immutable currency-exponent conversion, BUY fee capitalization, SELL net-proceeds/cost-basis/gain/loss postings, and owner-timezone trade dates.
- Added a locked brokerage cash-balance check before new BUY fills.
- Added pure accounting tests for BUY, SELL gain/loss, fee bounds, and zero-value BUY rejection.

### Validation and boundaries
- CI and PostgreSQL cross-domain acceptance are pending on draft PR #38; do not treat the coordinator as release-ready until those checks pass.
- The coordinator records fills that have already executed. No broker connection, order submission, cash transfer, public trade API, production data write, or deployment is included.
