# FinTrack Roadmap

Last updated: 2026-11-02

## Current release: 2.2.1

**Status: Deployed on Render; infrastructure and API health verified. Live user-workflow acceptance testing remains.**

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

The current Render PostgreSQL database is on the free tier and is scheduled to expire on December 2, 2026. Upgrade to durable paid resources and configure backups before storing real financial information. The live deployment and API health are verified, but browser-based end-to-end workflows and production security review are still outstanding. FinTrack is a portfolio/educational application, not a bank or financial-advice service.
