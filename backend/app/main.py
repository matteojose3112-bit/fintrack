import csv
import io
import os
from calendar import month_abbr
from datetime import date
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .auth import create_access_token, get_current_user, hash_password, verify_password
from .database import get_db
from .models import Budget, Goal, Transaction, User
from .schemas import AuthResponse, BudgetCreate, Contribution, GoalCreate, RegisterRequest, TransactionCreate, UserResponse

app = FastAPI(title="FinTrack API", version="2.1.0", description="Personal finance and budgeting API")
allowed_origins = [origin.strip() for origin in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173"
).split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def month_range(year: int, month: int):
    start = date(year, month, 1)
    end = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
    return start, end


def api_amount(value):
    """Convert exact database decimals to JSON-compatible numbers at the API boundary."""
    return float(value or Decimal("0"))


def auth_response(user: User):
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": {"id": user.id, "email": user.email}}


def serialize_transaction(t):
    return {"id": t.id, "title": t.title, "amount": api_amount(t.amount), "type": t.type, "category": t.category, "date": t.date.isoformat()}


def serialize_budget(b, db, user_id):
    today = date.today()
    start, end = month_range(today.year, today.month)
    spent = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.type == "expense",
        Transaction.category == b.category,
        Transaction.date >= start,
        Transaction.date < end,
    ).scalar()
    return {"id": b.id, "category": b.category, "limit": api_amount(b.limit), "spent": api_amount(spent)}


def serialize_goal(g):
    return {"id": g.id, "name": g.name, "target_amount": api_amount(g.target_amount), "saved_amount": api_amount(g.saved_amount)}


@app.get("/")
def root():
    return {"name": "FinTrack API", "docs": "/docs", "status": "online"}


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return auth_response(user)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == form.username.lower()).first()
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    return auth_response(user)


@app.get("/api/auth/me", response_model=UserResponse)
def current_account(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}


@app.get("/api/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    start, end = month_range(today.year, today.month)

    def totals(kind, lower=None, upper=None):
        query = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == user.id, Transaction.type == kind
        )
        if lower is not None:
            query = query.filter(Transaction.date >= lower)
        if upper is not None:
            query = query.filter(Transaction.date < upper)
        return query.scalar() or Decimal("0")

    income = totals("income", start, end)
    expenses = totals("expense", start, end)
    all_income = totals("income")
    all_expenses = totals("expense")
    monthly = []
    for offset in range(5, -1, -1):
        month_num = today.month - offset
        year = today.year
        while month_num <= 0:
            month_num += 12
            year -= 1
        month_start, month_end = month_range(year, month_num)
        monthly.append({
            "month": month_abbr[month_num],
            "income": api_amount(totals("income", month_start, month_end)),
            "expenses": api_amount(totals("expense", month_start, month_end)),
        })
    categories = db.query(Transaction.category, func.sum(Transaction.amount).label("amount")).filter(
        Transaction.user_id == user.id, Transaction.type == "expense",
        Transaction.date >= start, Transaction.date < end,
    ).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc()).all()
    savings_rate = ((income - expenses) / income * Decimal("100")) if income else Decimal("0")
    return {
        "balance": api_amount(all_income - all_expenses),
        "income": api_amount(income),
        "expenses": api_amount(expenses),
        "savings_rate": round(float(max(Decimal("0"), savings_rate)), 1),
        "monthly": monthly,
        "categories": [{"category": category, "amount": api_amount(amount)} for category, amount in categories],
    }


@app.get("/api/transactions")
def list_transactions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.date.desc(), Transaction.id.desc()).all()
    return [serialize_transaction(t) for t in items]


@app.post("/api/transactions", status_code=201)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.type not in ("income", "expense"):
        raise HTTPException(422, "type must be income or expense")
    item = Transaction(**payload.model_dump(), user_id=user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return serialize_transaction(item)


@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user.id).first()
    if not item:
        raise HTTPException(404, "Transaction not found")
    db.delete(item)
    db.commit()
    return {"deleted": transaction_id}


@app.get("/api/budgets")
def list_budgets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(Budget).filter(Budget.user_id == user.id).order_by(Budget.category).all()
    return [serialize_budget(b, db, user.id) for b in items]


@app.post("/api/budgets", status_code=201)
def create_budget(payload: BudgetCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    existing = db.query(Budget).filter(Budget.user_id == user.id, Budget.category == payload.category).first()
    if existing:
        raise HTTPException(409, "A budget already exists for this category")
    item = Budget(**payload.model_dump(), user_id=user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return serialize_budget(item, db, user.id)


@app.get("/api/goals")
def list_goals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.id.desc()).all()
    return [serialize_goal(g) for g in items]


@app.post("/api/goals", status_code=201)
def create_goal(payload: GoalCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = Goal(**payload.model_dump(), user_id=user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return serialize_goal(item)


@app.post("/api/goals/{goal_id}/contribute")
def contribute(goal_id: int, payload: Contribution, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if not item:
        raise HTTPException(404, "Goal not found")
    item.saved_amount += payload.amount
    db.commit()
    db.refresh(item)
    return serialize_goal(item)


@app.get("/api/export/transactions")
def export_transactions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Type", "Category", "Amount"])
    items = db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.date.desc()).all()
    for transaction in items:
        writer.writerow([transaction.date.isoformat(), transaction.title, transaction.type, transaction.category, transaction.amount])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=fintrack-transactions.csv"})
