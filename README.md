# FinTrack

**A modern personal finance and budgeting platform.**

FinTrack brings income, expenses, budgets, savings goals, and financial insights into one clear workspace, with a responsive React interface and Python API.

![Status](https://img.shields.io/badge/status-deployment%20ready-16a34a)
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
│   └── requirements.txt
├── .github/workflows/ # Continuous integration
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
- [ ] Database migrations and legacy database upgrade path
- [ ] Production security, configuration, and database migrations
- [ ] Deployment and portfolio release

## Project principles

FinTrack is designed around clarity, useful financial context, and responsible data handling. It is an educational portfolio project, not financial advice. The local setup uses SQLite; production uses PostgreSQL. Alembic creates the current schema on a fresh database. The initial migration is not a conversion of an older pre-2.0 SQLite database: back up legacy data and plan a dedicated import before attempting to reuse it. FinTrack is a portfolio project, not financial advice or a bank. Do not enter sensitive real-world financial information until the deployment, access controls, backups, and operational security have been independently reviewed. The Render Blueprint uses free-tier resources for demonstration; Render free PostgreSQL databases expire after their trial period and free web services may sleep. Choose paid persistent hosting and verify backups before relying on the service.

## License

Released under the [MIT License](LICENSE).
