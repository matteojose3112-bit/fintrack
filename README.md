# FinTrack

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
- Source: `matteojose3112-bit/fintrack`, branch `main`

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
| [#3](https://github.com/matteojose3112-bit/fintrack/pull/3) | Account-isolation regression tests | Draft; CI passed |
| [#4](https://github.com/matteojose3112-bit/fintrack/pull/4) | Production API URL and CORS configuration | Draft; CI passed; no Render Blueprint sync performed |
| [#5](https://github.com/matteojose3112-bit/fintrack/pull/5) | CSV spreadsheet-formula injection protection | Draft; CI passed |
| [#7](https://github.com/matteojose3112-bit/fintrack/pull/7) | Login and registration rate limiting | Draft; CI passed; shared rate-limit storage and proxy behavior need deployment planning |
| [#10](https://github.com/matteojose3112-bit/fintrack/pull/10) | Fixed-precision monetary storage and Decimal calculations | Draft; CI passed; populated-data and PostgreSQL migration validation remain |

These branches have been tested individually; combined integration testing is still required. No PR in this list has been merged or deployed. PR #10's migration must be tested against representative existing data and reviewed for PostgreSQL behavior, with a verified backup before any production migration. Do not treat the live deployment as containing these changes.

## Documentation review — 2026-11-09

Release readiness remains in progress. The immediate engineering focus is integration testing across the draft PRs, followed by live browser acceptance testing, dependency/security review, and a durable database/backup plan before the Render free PostgreSQL expiry on 2026-12-02. No production migration, Render configuration change, or deployment was performed as part of this documentation update.



## Release validation update — 2026-11-10

- PR #10 now includes a populated legacy SQLite migration regression test. GitHub Actions run [#91](https://github.com/matteojose3112-bit/fintrack/actions/runs/42920839088) passed both backend and frontend jobs, including the seeded pre-migration database upgrade, data rounding/preservation, index and foreign-key checks.
- PR #12 is an open draft integration vehicle combining PRs #3, #5, #7, and #10. Its initial combined CI run [#92](https://github.com/matteojose3112-bit/fintrack/actions/runs/42921329034) passed backend tests, Alembic fresh-schema migration, frontend tests, and production build. A small follow-up whitespace-handling correction was committed after that run; the latest head still needs a fresh CI confirmation.
- PR #4's Render URL/CORS diff was reviewed: the configured frontend API URL matches the deployed API, and production CORS is restricted to the deployed frontend origin. No Blueprint sync or live configuration change was performed.
- PostgreSQL migration behavior was reviewed statically: Alembic batch operations use native column alteration on PostgreSQL. No non-production PostgreSQL migration execution has yet been performed, so that validation remains open.
- Rate limiting still defaults to process-local memory. Multi-instance production requires private shared Redis/Valkey storage and verified proxy/client-IP handling.
- Frontend dependency audit findings and the bundle-size warning have not been re-audited in this pass.
- All PRs remain drafts; no changes have been merged or deployed. The free PostgreSQL database expiry remains 2026-12-02, with durable hosting, backup, and restore testing still required.


- The latest integration CI run [#96](https://github.com/matteojose3112-bit/fintrack/actions/runs/42921838065) passed all three jobs: backend suite, frontend tests/build, and a disposable PostgreSQL service migration test. The PostgreSQL test upgraded seeded legacy Float records to Numeric(14,2) and verified rounded values, retained indexes, foreign keys, and migration revision.
