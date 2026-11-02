from datetime import date
from pydantic import BaseModel, Field

class TransactionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    amount: float = Field(gt=0)
    type: str
    category: str = Field(default="Other", max_length=80)
    date: date

class BudgetCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    limit: float = Field(gt=0)

class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: float = Field(gt=0)

class Contribution(BaseModel):
    amount: float = Field(gt=0)
