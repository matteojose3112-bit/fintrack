from datetime import date
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field


MONEY_FIELD = Field(gt=Decimal("0"), max_digits=14, decimal_places=2)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: EmailStr


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TransactionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    amount: Decimal = MONEY_FIELD
    type: str
    category: str = Field(default="Other", max_length=80)
    date: date


class BudgetCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    limit: Decimal = MONEY_FIELD


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = MONEY_FIELD


class Contribution(BaseModel):
    amount: Decimal = MONEY_FIELD
