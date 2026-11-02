# FinTrack

**A modern personal finance and budgeting platform.**

FinTrack brings income, expenses, budgets, savings goals, and financial insights into one clear workspace, with a responsive React interface and Python API.

![Status](https://img.shields.io/badge/status-in%20development-8b5cf6)
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
| Database | SQLite, SQLAlchemy |
| Validation | Pydantic |
| Frontend tests | Vitest, React Testing Library, jsdom |
| Backend tests | pytest, FastAPI TestClient, httpx |
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

The API runs at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

### 2. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). The Vite development server proxies `/api` requests to FastAPI.

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
| GET | `/api/summary` | Dashboard totals and chart data |
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
- [ ] Authentication and multi-user accounts
- [ ] Production security, configuration, and database migrations
- [ ] Deployment and portfolio release

## Project principles

FinTrack is designed around clarity, useful financial context, and responsible data handling. It is an educational portfolio project, not financial advice. The initial local setup uses an empty SQLite database; do not enter sensitive real-world financial information into an unreviewed deployment.

## License

Released under the [MIT License](LICENSE).
