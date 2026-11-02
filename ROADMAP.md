# FinTrack Roadmap

Last updated: 2026-11-02

## Current release: 2.2.0

**Status: Render resources provisioned; live deployment verification pending.**

The Render Blueprint `fintrack` has been created from `matteojose3112-bit/fintrack` on `main` using the root `render.yaml`.

- Blueprint ID: `exs-dbkhp88m7kps7396um8g`
- `fintrack-api` — FastAPI web service
- `fintrack-web` — static React frontend
- `fintrack-db` — PostgreSQL database

Resource provisioning is confirmed. A public release is only complete after Render reports successful service deployments and the live checks below pass.

## Deployment verification

- [x] Create Render Blueprint from repository configuration
- [x] Provision API service, static frontend, and PostgreSQL database
- [ ] Confirm API build and Alembic migration complete successfully
- [ ] Confirm frontend build and publish complete successfully
- [ ] Verify API health endpoint at `/api/health` on the actual Render API URL
- [ ] Verify frontend can register and authenticate a user
- [ ] Verify transactions, budgets, savings goals, and CSV export
- [ ] Verify user data isolation across accounts

## Product and engineering

- [x] Responsive dashboard and transaction management
- [x] Budget management and savings goals
- [x] Monthly analytics and CSV export
- [x] Registration, login, JWT authentication, and password hashing
- [x] User-scoped financial records and API integration tests
- [x] PostgreSQL support and Alembic initial schema migration
- [x] GitHub Actions test and production-build workflow
- [ ] Broader accessibility and keyboard-navigation audit
- [ ] Password reset and email verification
- [ ] API rate limiting and additional abuse protection
- [ ] Automated database backups and restore testing
- [ ] Legacy SQLite data import/upgrade utility

## Production readiness notes

The current Render Blueprint uses free-tier resources for demonstration. Render free PostgreSQL has a limited lifetime and free web services may sleep. Upgrade to durable paid resources, configure backups, and review security before storing real financial information. FinTrack is a portfolio/educational application, not a bank or financial-advice service.
