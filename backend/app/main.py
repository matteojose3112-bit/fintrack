import csv
import io
from calendar import month_abbr
from datetime import date
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .models import Budget, Goal, Transaction
from .schemas import BudgetCreate, Contribution, GoalCreate, TransactionCreate

Base.metadata.create_all(bind=engine)
app = FastAPI(title="FinTrack API", version="1.0.0", description="Personal finance and budgeting API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def serialize_transaction(t):
    return {"id": t.id, "title": t.title, "amount": t.amount, "type": t.type, "category": t.category, "date": t.date.isoformat()}

def serialize_budget(b, db):
    spent = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.type == "expense", Transaction.category == b.category, func.strftime("%Y-%m", Transaction.date) == date.today().strftime("%Y-%m")).scalar()
    return {"id": b.id, "category": b.category, "limit": b.limit, "spent": float(spent or 0)}

def serialize_goal(g):
    return {"id": g.id, "name": g.name, "target_amount": g.target_amount, "saved_amount": g.saved_amount}

@app.get("/")
def root():
    return {"name": "FinTrack API", "docs": "/docs", "status": "online"}

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/summary")
def summary(db: Session = Depends(get_db)):
    today = date.today()
    month = today.strftime("%Y-%m")
    income = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.type == "income", func.strftime("%Y-%m", Transaction.date) == month).scalar()
    expenses = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.type == "expense", func.strftime("%Y-%m", Transaction.date) == month).scalar()
    all_income = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.type == "income").scalar()
    all_expenses = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.type == "expense").scalar()
    monthly = []
    for offset in range(5, -1, -1):
        month_num = today.month - offset
        year = today.year
        while month_num <= 0:
            month_num += 12
            year -= 1
        key = f"{year:04d}-{month_num:02d}"
        inc = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.type == "income", func.strftime("%Y-%m", Transaction.date) == key).scalar()
        exp = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.type == "expense", func.strftime("%Y-%m", Transaction.date) == key).scalar()
        monthly.append({"month": month_abbr[month_num], "income": float(inc or 0), "expenses": float(exp or 0)})
    categories = db.query(Transaction.category, func.sum(Transaction.amount).label("amount")).filter(Transaction.type == "expense", func.strftime("%Y-%m", Transaction.date) == month).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc()).all()
    return {"balance": float(all_income or 0) - float(all_expenses or 0), "income": float(income or 0), "expenses": float(expenses or 0), "savings_rate": round(max(0, (float(income or 0) - float(expenses or 0)) / float(income) * 100), 1) if income else 0, "monthly": monthly, "categories": [{"category": c, "amount": float(a)} for c, a in categories]}

@app.get("/api/transactions")
def list_transactions(db: Session = Depends(get_db)):
    return [serialize_transaction(t) for t in db.query(Transaction).order_by(Transaction.date.desc(), Transaction.id.desc()).all()]

@app.post("/api/transactions", status_code=201)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    if payload.type not in ("income", "expense"):
        raise HTTPException(422, "type must be income or expense")
    item = Transaction(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return serialize_transaction(item)

@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    item = db.get(Transaction, transaction_id)
    if not item: raise HTTPException(404, "Transaction not found")
    db.delete(item); db.commit()
    return {"deleted": transaction_id}

@app.get("/api/budgets")
def list_budgets(db: Session = Depends(get_db)):
    return [serialize_budget(b, db) for b in db.query(Budget).order_by(Budget.category).all()]

@app.post("/api/budgets", status_code=201)
def create_budget(payload: BudgetCreate, db: Session = Depends(get_db)):
    existing = db.query(Budget).filter(Budget.category == payload.category).first()
    if existing: raise HTTPException(409, "A budget already exists for this category")
    item = Budget(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item)
    return serialize_budget(item, db)

@app.get("/api/goals")
def list_goals(db: Session = Depends(get_db)):
    return [serialize_goal(g) for g in db.query(Goal).order_by(Goal.id.desc()).all()]

@app.post("/api/goals", status_code=201)
def create_goal(payload: GoalCreate, db: Session = Depends(get_db)):
    item = Goal(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item)
    return serialize_goal(item)

@app.post("/api/goals/{goal_id}/contribute")
def contribute(goal_id: int, payload: Contribution, db: Session = Depends(get_db)):
    item = db.get(Goal, goal_id)
    if not item: raise HTTPException(404, "Goal not found")
    item.saved_amount += payload.amount; db.commit(); db.refresh(item)
    return serialize_goal(item)

@app.get("/api/export/transactions")
def export_transactions(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Type", "Category", "Amount"])
    for t in db.query(Transaction).order_by(Transaction.date.desc()).all():
        writer.writerow([t.date.isoformat(), t.title, t.type, t.category, t.amount])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=fintrack-transactions.csv"})
