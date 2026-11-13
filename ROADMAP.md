# FinTrack Roadmap

Last updated: 2026-11-10

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
