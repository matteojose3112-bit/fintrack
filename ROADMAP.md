# FinTrack Roadmap

Last updated: 2026-11-08

## Current release: 2.2.2

**Status: Render MVP previously deployed; current API availability is unconfirmed after an HTTP 503 observation on 2026-11-08. Live user-workflow acceptance testing remains.**

### Live infrastructure

- Render Blueprint: `fintrack` (`exs-dbkhp88m7kps7396um8g`)
- API: [https://fintrack-api-l1wa.onrender.com](https://fintrack-api-l1wa.onrender.com)
- Frontend: [https://fintrack-web-int6.onrender.com](https://fintrack-web-int6.onrender.com)
- Database: `fintrack-db` (PostgreSQL 18, free tier)
- Repository: `matteojose3112-bit/fintrack`, branch `main`

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

The current Render PostgreSQL database is on the free tier and is scheduled to expire on December 2, 2026. Upgrade to durable paid resources and configure backups before storing real financial information. The Render resources were previously deployed and an earlier health check passed, but a later PR review observed HTTP 503 on 2026-11-08. Recheck current API health before relying on the deployment; browser-based end-to-end workflows and production security review are still outstanding. FinTrack is a portfolio/educational application, not a bank or financial-advice service.


---

Last reviewed: 2026-11-08

## Current engineering status — 2026-11-08

**Main branch: 2.2.2 deployed-MVP baseline; live acceptance and production-readiness work remain open.** The latest recorded `main` CI run passed on 2026-11-04 (commit `481cebb`). PR-branch checks for the draft changes below are recorded as passing at their latest heads, but none is merged.

### Open draft PRs — pending merge and review
- [ ] [PR #3](https://github.com/matteojose3112-bit/fintrack/pull/3): additional cross-account isolation regression tests.
- [ ] [PR #4](https://github.com/matteojose3112-bit/fintrack/pull/4): correct Render production API URL and CORS origin; recheck live API health before any Blueprint sync. The PR review recorded HTTP 503 on 2026-11-08; no production configuration change was made.
- [ ] [PR #5](https://github.com/matteojose3112-bit/fintrack/pull/5): protect CSV exports against spreadsheet formula injection.
- [ ] [PR #7](https://github.com/matteojose3112-bit/fintrack/pull/7): rate-limit registration/login; review the process-local default and shared-store requirements before production scaling.

### Open follow-up issue
- [ ] [Issue #6](https://github.com/matteojose3112-bit/fintrack/issues/6): replace floating-point monetary fields/calculations with fixed-precision decimals and define a safe SQLite/PostgreSQL migration plan.

### Additional release gates
- [ ] Recheck live API health and complete browser registration/login plus transaction, budget, savings-goal, contribution, and CSV-export workflows.
- [ ] Verify cross-account isolation in live acceptance tests, not only isolated automated tests.
- [ ] Review current dependency audit results and address the previously reported frontend vulnerabilities.
- [ ] Review/split the previously oversized frontend production bundle.
- [ ] Confirm the free PostgreSQL database's current lifecycle/expiry; arrange durable hosting, automated backups, and a restore test before real financial use.
- [ ] Complete broader keyboard/accessibility and production security reviews.
- [ ] Define a legacy SQLite import/upgrade strategy before reusing pre-2.0 data.

Do not mark draft PRs or issue #6 complete until changes are merged and the corresponding migration, deployment, and acceptance checks are actually performed. FinTrack remains an educational portfolio application, not a bank or financial-advice service.