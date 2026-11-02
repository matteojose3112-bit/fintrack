# FinTrack

**A modern personal finance and budgeting platform.**

FinTrack brings income, expenses, budgets, savings goals, and financial insights into one clear workspace. It is being built as a practical, full-stack application with a responsive React interface and a Python API.

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

## Project structure

```
fintrack/
├── frontend/          # React application
├── backend/
│   ├── app/           # FastAPI application and database models
│   └── requirements.txt
├── .gitignore
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
# Windows: .venv\Scripts\activate
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

Open the local URL printed by Vite (normally `http://localhost:5173`).

The Vite development server proxies `/api` requests to the FastAPI service.

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

- [x] Repository structure and application foundation
- [x] FastAPI service and SQLite data layer
- [x] Responsive dashboard and core finance screens
- [x] Transaction, budget, and savings-goal workflows
- [x] Analytics and CSV export foundation
- [ ] Automated tests and accessibility review
- [ ] Authentication and multi-user accounts
- [ ] Deployment and production configuration

## Project principles

FinTrack is designed around clarity, useful financial context, and responsible data handling. It is an educational portfolio project, not financial advice. The initial local setup uses SQLite and demo records; do not enter sensitive real-world financial information into an unreviewed deployment.

## License

Released under the [MIT License](LICENSE).
