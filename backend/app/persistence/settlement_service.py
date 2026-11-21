"""Atomic composition of portfolio fills and cash-ledger journals.

This service records fills that have already executed. It never submits orders,
connects to a broker, transfers cash, or owns the caller's transaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.domain.portfolio_lots import CostBasisMethod, TradeExecution, TradeSide
from app.domain.portfolio_money import to_minor_units
from app.persistence.models import (
    CurrencyDefinitionModel,
    FinancialOwnerPreferenceModel,
    JournalEntryModel,
    JournalPostingModel,
)
from app.persistence.portfolio_models import TradeExecutionModel
from app.persistence.portfolio_lot_service import (
    PersistedTradeResult,
    apply_portfolio_execution_in_session,
)
from app.persistence.posting_service import (
    PostJournalCommand,
    PostingLine,
    PostingResult,
    post_journal_in_session,
)
from app.persistence.settlement_mapping_service import (
    ResolvedPortfolioLedgerAccounts,
    resolve_portfolio_ledger_mapping_in_session,
)


SETTLEMENT_OPERATION_VERSION = "portfolio.trade_settlement.v1"


class TradeSettlementError(RuntimeError):
    """Base class for fail-closed settlement errors."""


class SettlementInsufficientCash(TradeSettlementError):
    """The brokerage cash ledger cannot fund a BUY fill."""


class SettlementCurrencyUnavailable(TradeSettlementError):
    """No eligible immutable currency snapshot exists for the execution."""


class SettlementPrecisionError(TradeSettlementError):
    """The fill cannot be represented safely at the currency's minor-unit scale."""


@dataclass(frozen=True, slots=True)
class TradeSettlementResult:
    portfolio: PersistedTradeResult
    journal: PostingResult
    replayed: bool


def _currency_snapshot(
    session: Session, owner_id: int, execution: TradeExecution
) -> CurrencyDefinitionModel:
    """Resolve the same position snapshot policy used by portfolio persistence."""
    prior = session.scalars(
        select(TradeExecutionModel)
        .join(
            CurrencyDefinitionModel,
            TradeExecutionModel.quote_currency_definition_id == CurrencyDefinitionModel.id,
        )
        .where(
            TradeExecutionModel.owner_id == owner_id,
            TradeExecutionModel.portfolio_id == execution.portfolio_id,
            TradeExecutionModel.account_id == execution.account_id,
            TradeExecutionModel.instrument_id == execution.instrument_id,
            TradeExecutionModel.quote_currency_definition_id
            == CurrencyDefinitionModel.id,
            CurrencyDefinitionModel.code == execution.quote_currency_code,
        )
        .order_by(TradeExecutionModel.executed_at.asc())
        .limit(1)
    ).first()
    if prior is not None:
        currency = session.get(CurrencyDefinitionModel, prior.quote_currency_definition_id)
        if currency is not None:
            return currency

    currency = session.scalars(
        select(CurrencyDefinitionModel)
        .where(
            CurrencyDefinitionModel.code == execution.quote_currency_code,
            CurrencyDefinitionModel.registry_list == "one",
            CurrencyDefinitionModel.withdrawal_key == "",
            CurrencyDefinitionModel.fund.is_(False),
            CurrencyDefinitionModel.minor_unit_exponent.is_not(None),
        )
        .order_by(CurrencyDefinitionModel.published_on.desc())
        .limit(1)
    ).first()
    if currency is None or currency.minor_unit_exponent is None:
        raise SettlementCurrencyUnavailable(
            "quote currency has no eligible ISO minor-unit definition"
        )
    return currency


def _cash_balance_minor(session: Session, owner_id: int, account_id: UUID) -> int:
    """Return the locked ASSET account's posted debit-minus-credit balance."""
    signed_amount = case(
        (JournalPostingModel.side == "DEBIT", JournalPostingModel.amount_minor),
        else_=-JournalPostingModel.amount_minor,
    )
    value = session.scalar(
        select(func.coalesce(func.sum(signed_amount), 0))
        .select_from(JournalPostingModel)
        .join(
            JournalEntryModel,
            JournalEntryModel.id == JournalPostingModel.journal_entry_id,
        )
        .where(
            JournalPostingModel.owner_id == owner_id,
            JournalPostingModel.account_id == account_id,
            JournalEntryModel.owner_id == owner_id,
            JournalEntryModel.status == "POSTED",
        )
    )
    return int(value or 0)


def _trade_date(session: Session, owner_id: int, executed_at) -> date:
    preference = session.get(FinancialOwnerPreferenceModel, owner_id)
    timezone_name = preference.accounting_timezone if preference else "UTC"
    try:
        timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise TradeSettlementError(
            "owner accounting timezone is invalid; trade date cannot be determined"
        ) from exc
    return executed_at.astimezone(timezone).date()


def _settlement_postings(
    execution: TradeExecution,
    portfolio_result: PersistedTradeResult,
    accounts: ResolvedPortfolioLedgerAccounts,
    exponent: int,
) -> tuple[PostingLine, ...]:
    """Build balanced integer-minor-unit journal lines from v2 lot facts."""
    if execution.side is TradeSide.BUY:
        total_cost = to_minor_units(
            execution.quantity * execution.unit_price + execution.fee, exponent
        )
        if total_cost <= 0:
            raise SettlementPrecisionError("zero-value BUY fills cannot be settled")
        return (
            PostingLine(accounts.investment_control_account.id, "DEBIT", total_cost),
            PostingLine(accounts.cash_account.id, "CREDIT", total_cost),
        )

    gross = to_minor_units(execution.quantity * execution.unit_price, exponent)
    fee = to_minor_units(execution.fee, exponent)
    net_proceeds = gross - fee
    if gross <= 0:
        raise SettlementPrecisionError("zero-value SELL fills cannot be settled")
    if fee > gross or net_proceeds < 0:
        raise SettlementPrecisionError("sale fee cannot exceed gross proceeds")

    basis = to_minor_units(
        sum((allocation.cost_basis for allocation in portfolio_result.application.allocations),
            Decimal("0")),
        exponent,
    )
    lines: list[PostingLine] = []
    if net_proceeds:
        lines.append(PostingLine(accounts.cash_account.id, "DEBIT", net_proceeds))
    if basis:
        lines.append(PostingLine(accounts.investment_control_account.id, "CREDIT", basis))
    if net_proceeds > basis:
        lines.append(
            PostingLine(
                accounts.realized_gain_account.id, "CREDIT", net_proceeds - basis
            )
        )
    elif basis > net_proceeds:
        lines.append(
            PostingLine(
                accounts.realized_loss_account.id, "DEBIT", basis - net_proceeds
            )
        )
    if len(lines) < 2:
        raise SettlementPrecisionError("settlement produced no balanced positive-value journal")
    return tuple(lines)


def settle_portfolio_execution_in_session(
    session: Session,
    owner_id: int,
    actor_id: int,
    execution: TradeExecution,
    *,
    cost_basis_method: CostBasisMethod = CostBasisMethod.FIFO,
    specific_lot_id: UUID | None = None,
) -> TradeSettlementResult:
    """Atomically record an already-executed fill and its cash journal.

    The caller must supply an active PostgreSQL transaction. This function
    never creates, commits, rolls back, closes, or retries the Session.
    """
    if not session.in_transaction():
        raise RuntimeError(
            "settle_portfolio_execution_in_session requires an active transaction"
        )
    if session.get_bind().dialect.name != "postgresql":
        raise RuntimeError("trade settlement requires PostgreSQL")
    if actor_id != owner_id:
        raise TradeSettlementError("actor must match the authenticated owner in v1")

    currency = _currency_snapshot(session, owner_id, execution)
    if currency.minor_unit_exponent is None:
        raise SettlementCurrencyUnavailable("currency snapshot has no minor-unit exponent")

    accounts = resolve_portfolio_ledger_mapping_in_session(
        session,
        owner_id,
        execution.portfolio_id,
        execution.account_id,
        currency.id,
    )

    existing = session.get(TradeExecutionModel, execution.execution_id)
    if existing is None and execution.side is TradeSide.BUY:
        required_cash = to_minor_units(
            execution.quantity * execution.unit_price + execution.fee,
            currency.minor_unit_exponent,
        )
        if required_cash <= 0:
            raise SettlementPrecisionError("zero-value BUY fills cannot be settled")
        available_cash = _cash_balance_minor(
            session, owner_id, accounts.cash_account.id
        )
        if available_cash < required_cash:
            raise SettlementInsufficientCash(
                "brokerage cash balance is insufficient for the BUY including fees"
            )

    portfolio_result = apply_portfolio_execution_in_session(
        session,
        owner_id,
        actor_id,
        execution,
        cost_basis_method=cost_basis_method,
        specific_lot_id=specific_lot_id,
    )

    lines = _settlement_postings(
        execution, portfolio_result, accounts, currency.minor_unit_exponent
    )
    command = PostJournalCommand(
        owner_id=owner_id,
        actor_id=actor_id,
        effective_date=_trade_date(session, owner_id, execution.executed_at),
        description=(
            f"Portfolio {execution.side.value.upper()} settlement "
            f"{execution.execution_id}"
        ),
        currency_definition_id=currency.id,
        postings=lines,
    )
    journal = post_journal_in_session(
        session,
        command,
        f"{SETTLEMENT_OPERATION_VERSION}:{execution.execution_id}",
    )
    return TradeSettlementResult(
        portfolio=portfolio_result,
        journal=journal,
        replayed=portfolio_result.application.replayed or journal.replayed,
    )
