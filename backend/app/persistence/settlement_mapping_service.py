"""Caller-transaction resolver for explicit portfolio settlement account mappings."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models import FinancialAccountModel
from app.persistence.portfolio_models import InvestmentPortfolioModel
from app.persistence.settlement_models import PortfolioLedgerAccountMappingModel


class SettlementMappingError(RuntimeError):
    """Base error for settlement mapping resolution failures."""


class SettlementMappingNotFound(SettlementMappingError):
    """No mapping exists for the requested owner/portfolio/cash/currency scope."""


class SettlementMappingInvalid(SettlementMappingError):
    """A mapped portfolio or ledger account is no longer eligible for settlement."""


@dataclass(frozen=True, slots=True)
class ResolvedPortfolioLedgerAccounts:
    """Locked mapping and role-specific account rows for one settlement transaction."""

    mapping: PortfolioLedgerAccountMappingModel
    cash_account: FinancialAccountModel
    investment_control_account: FinancialAccountModel
    realized_gain_account: FinancialAccountModel
    realized_loss_account: FinancialAccountModel


def resolve_portfolio_ledger_mapping_in_session(
    session: Session,
    owner_id: int,
    portfolio_id: UUID,
    cash_account_id: UUID,
    currency_definition_id: UUID,
) -> ResolvedPortfolioLedgerAccounts:
    """Resolve and lock a mapping inside the caller-owned PostgreSQL transaction.

    Lock order is portfolio, mapping, then all four financial accounts in
    ascending UUID order. Account locks use the same deterministic ordering as
    ledger posting and prevent a concurrent account closure from racing the
    settlement transaction. This function never commits, rolls back, closes,
    or retries the caller's Session.
    """
    if not session.in_transaction():
        raise RuntimeError(
            "resolve_portfolio_ledger_mapping_in_session requires an active transaction"
        )
    if session.get_bind().dialect.name != "postgresql":
        raise RuntimeError("settlement mapping resolution requires PostgreSQL")
    if isinstance(owner_id, bool) or not isinstance(owner_id, int) or owner_id <= 0:
        raise ValueError("owner_id must be a positive authenticated user ID")
    for name, value in (
        ("portfolio_id", portfolio_id),
        ("cash_account_id", cash_account_id),
        ("currency_definition_id", currency_definition_id),
    ):
        if not isinstance(value, UUID):
            raise TypeError(f"{name} must be UUID")

    portfolio = session.execute(
        select(InvestmentPortfolioModel)
        .where(
            InvestmentPortfolioModel.id == portfolio_id,
            InvestmentPortfolioModel.owner_id == owner_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if portfolio is None:
        raise SettlementMappingNotFound("portfolio not found for owner")
    if portfolio.status != "ACTIVE":
        raise SettlementMappingInvalid("portfolio is archived")

    mapping = session.execute(
        select(PortfolioLedgerAccountMappingModel)
        .where(
            PortfolioLedgerAccountMappingModel.owner_id == owner_id,
            PortfolioLedgerAccountMappingModel.portfolio_id == portfolio_id,
            PortfolioLedgerAccountMappingModel.cash_account_id == cash_account_id,
            PortfolioLedgerAccountMappingModel.currency_definition_id
            == currency_definition_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if mapping is None:
        raise SettlementMappingNotFound(
            "no ledger account mapping exists for this portfolio, cash account, and currency"
        )

    role_ids = {
        "cash": mapping.cash_account_id,
        "investment": mapping.investment_control_account_id,
        "gain": mapping.realized_gain_account_id,
        "loss": mapping.realized_loss_account_id,
    }
    ordered_ids = sorted(set(role_ids.values()), key=str)
    if len(ordered_ids) != 4:
        raise SettlementMappingInvalid("mapped ledger account roles must be distinct")

    rows = session.scalars(
        select(FinancialAccountModel)
        .where(FinancialAccountModel.id.in_(ordered_ids))
        .order_by(FinancialAccountModel.id)
        .with_for_update()
    ).all()
    accounts = {row.id: row for row in rows}
    if len(accounts) != 4:
        raise SettlementMappingInvalid("one or more mapped financial accounts are missing")

    expected_types = {
        "cash": "ASSET",
        "investment": "ASSET",
        "gain": "INCOME",
        "loss": "EXPENSE",
    }
    for role, account_id in role_ids.items():
        account = accounts[account_id]
        if account.owner_id != owner_id:
            raise SettlementMappingInvalid(f"mapped {role} account is not owned by caller")
        if account.currency_definition_id != currency_definition_id:
            raise SettlementMappingInvalid(f"mapped {role} account currency does not match fill")
        if account.account_type != expected_types[role]:
            raise SettlementMappingInvalid(
                f"mapped {role} account must have type {expected_types[role]}"
            )
        if account.status != "OPEN":
            raise SettlementMappingInvalid(f"mapped {role} account is closed")

    return ResolvedPortfolioLedgerAccounts(
        mapping=mapping,
        cash_account=accounts[role_ids["cash"]],
        investment_control_account=accounts[role_ids["investment"]],
        realized_gain_account=accounts[role_ids["gain"]],
        realized_loss_account=accounts[role_ids["loss"]],
    )
