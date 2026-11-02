# FinTrack API

FastAPI service for the FinTrack personal finance application.

## Setup

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The service is available at `http://localhost:8000`; interactive docs are at `/docs`.

## Configuration

The initial version stores data in `backend/fintrack.db` using SQLite. The database is created automatically when the application starts.

## Routes

- `GET /api/health`
- `GET /api/summary`
- `GET, POST /api/transactions`
- `DELETE /api/transactions/{id}`
- `GET, POST /api/budgets`
- `GET, POST /api/goals`
- `POST /api/goals/{id}/contribute`
- `GET /api/export/transactions`

Amounts are represented as positive numbers; the transaction `type` determines whether an amount is income or expense.
