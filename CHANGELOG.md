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
