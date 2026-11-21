from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LedgerInputModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class AccountCreateRequest(LedgerInputModel):
    name: str = Field(min_length=1, max_length=160)
    account_type: Literal["ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE"]
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")


class JournalPostingRequest(LedgerInputModel):
    account_id: str = Field(pattern=r"^[0-9a-fA-F-]{36}$")
    side: Literal["DEBIT", "CREDIT"]
    amount_minor: str = Field(pattern=r"^[1-9][0-9]{0,37}$")


class JournalCreateRequest(LedgerInputModel):
    effective_date: date
    description: str = Field(min_length=1, max_length=500)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    postings: list[JournalPostingRequest] = Field(min_length=2, max_length=1000)


class JournalReversalRequest(LedgerInputModel):
    effective_date: date
    description: str = Field(default="Journal reversal", min_length=1, max_length=500)
