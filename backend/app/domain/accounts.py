"""Immutable financial account identities and classification rules."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.money import Money


class AccountType(str, Enum):
    """Accounting classification and normal balance for an account."""

    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"

    @property
    def normal_side(self) -> str:
        return "debit" if self in {self.ASSET, self.EXPENSE} else "credit"


class AccountStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class FinancialAccount:
    """A user-owned, single-currency ledger account.

    Account identity and classification are immutable. Balances are derived
    from posted journal entries and are never stored on this object.
    """

    account_id: str
    owner_id: str
    name: str
    account_type: AccountType
    currency: str
    status: AccountStatus = AccountStatus.OPEN

    def __post_init__(self) -> None:
        for field_name in ("account_id", "owner_id", "name"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if not isinstance(self.account_type, AccountType):
            raise TypeError("account_type must be an AccountType")
        if not isinstance(self.status, AccountStatus):
            raise TypeError("status must be an AccountStatus")

        normalized = Money.from_minor_units(0, self.currency).currency
        object.__setattr__(self, "currency", normalized)

    @property
    def normal_side(self) -> str:
        return self.account_type.normal_side
