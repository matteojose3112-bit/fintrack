"""PostgreSQL-only atomic persistence service for long-only portfolio fills.

This records already-executed fills. It never submits orders to a broker.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
import hashlib
import json
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.domain.portfolio_lots import (
    CostBasisMethod,
    PortfolioAccountingError,
    PortfolioLotBook,
    PositionSnapshot,
    TradeApplication,
    TradeExecution,
    TradeSide,
)
from app.persistence.instrument_models import InstrumentDefinitionModel
from app.persistence.models import (
    AuditEventModel,
    CurrencyDefinitionModel,
    FinancialAccountModel,
)
from app.persistence.portfolio_models import (
    InvestmentPortfolioModel,
    LotDisposalAllocationModel,
    PortfolioLotModel,
    PortfolioPositionLockModel,
    TradeExecutionModel,
)


class PortfolioPersistenceError(RuntimeError):
    """Base error for persistence-boundary failures."""


class PortfolioScopeError(PortfolioPersistenceError):
    """The requested owner/portfolio/account/instrument scope is invalid."""


class ExecutionIdConflict(PortfolioPersistenceError):
    """An execution identifier was reused with a different payload."""


class OutOfOrderExecution(PortfolioPersistenceError):
    """A late fill requires the explicit rebuild workflow, not ordinary posting."""


@dataclass(frozen=True, slots=True)
class PersistedTradeResult:
    application: TradeApplication
    position: PositionSnapshot


def _decimal_key(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f") if normalized else "0"


def _request_hash(
    execution: TradeExecution,
    method: CostBasisMethod,
    specific_lot_id: UUID | None,
) -> str:
    payload = {
        "execution_id": str(execution.execution_id),
        "portfolio_id": str(execution.portfolio_id),
        "account_id": str(execution.account_id),
        "instrument_id": str(execution.instrument_id),
        "side": execution.side.value,
        "quantity": _decimal_key(execution.quantity),
        "unit_price": _decimal_key(execution.unit_price),
        "quote_currency_code": execution.quote_currency_code,
        "fee": _decimal_key(execution.fee),
        "executed_at": execution.executed_at.isoformat(),
        "source": execution.source,
        "cost_basis_method": method.value,
        "specific_lot_id": str(specific_lot_id) if specific_lot_id else None,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _to_domain(row: TradeExecutionModel, currency_code: str, currency_exponent: int) -> TradeExecution:
    return TradeExecution(
        execution_id=row.id,
        portfolio_id=row.portfolio_id,
        account_id=row.account_id,
        instrument_id=row.instrument_id,
        side=TradeSide(row.side.lower()),
        quantity=Decimal(row.quantity),
        unit_price=Decimal(row.unit_price),
        quote_currency_code=currency_code,
        fee=Decimal(row.fee),
        executed_at=row.executed_at,
        source=row.source,
        currency_minor_unit_exponent=(currency_exponent if row.accounting_precision_version >= 2 else None),
    )


def _rebuild_book(
    session: Session,
    owner_id: int,
    portfolio_id: UUID,
    account_id: UUID,
    instrument_id: UUID,
    currency_definition_id: UUID,
    currency_code: str,
    currency_exponent: int,
) -> tuple[PortfolioLotBook, dict[UUID, TradeApplication], list[TradeExecutionModel]]:
    rows = session.scalars(
        select(TradeExecutionModel)
        .where(
            TradeExecutionModel.owner_id == owner_id,
            TradeExecutionModel.portfolio_id == portfolio_id,
            TradeExecutionModel.account_id == account_id,
            TradeExecutionModel.instrument_id == instrument_id,
            TradeExecutionModel.quote_currency_definition_id == currency_definition_id,
        )
        .order_by(TradeExecutionModel.executed_at, TradeExecutionModel.id)
    ).all()

    book = PortfolioLotBook()
    applications: dict[UUID, TradeApplication] = {}
    for row in rows:
        domain_execution = _to_domain(row, currency_code, currency_exponent)
        method = CostBasisMethod(row.cost_basis_method)
        application = book.apply(
            domain_execution,
            cost_basis_method=method,
            specific_lot_id=row.specific_lot_id,
        )
        applications[row.id] = application
    return book, applications, list(rows)


def apply_portfolio_execution_in_session(
    session: Session,
    owner_id: int,
    actor_id: int,
    execution: TradeExecution,
    *,
    cost_basis_method: CostBasisMethod = CostBasisMethod.FIFO,
    specific_lot_id: UUID | None = None,
) -> PersistedTradeResult:
    """Record an execution inside a caller-owned PostgreSQL transaction.

    The caller owns commit/rollback. This function never creates or closes a
    Session and never commits, rolls back, or retries. Use it when the trade,
    cash journal, fees, FX legs, and audit facts must share one atomic boundary.
    """
    if actor_id != owner_id:
        raise PortfolioScopeError("actor must match the authenticated owner in v1")
    if not isinstance(cost_basis_method, CostBasisMethod):
        raise TypeError("cost_basis_method must be CostBasisMethod")
    if cost_basis_method is CostBasisMethod.SPECIFIC and specific_lot_id is None:
        raise PortfolioAccountingError("specific-lot disposal requires a lot ID")
    if cost_basis_method is not CostBasisMethod.SPECIFIC and specific_lot_id is not None:
        raise PortfolioAccountingError("specific_lot_id is only valid with SPECIFIC method")

    request_hash = _request_hash(execution, cost_basis_method, specific_lot_id)
    if not session.in_transaction():
        raise RuntimeError("apply_portfolio_execution_in_session requires an active transaction")
    if session.bind is None or session.bind.dialect.name != "postgresql":
        raise RuntimeError("portfolio execution persistence requires PostgreSQL")

    # A global execution lock handles the same execution UUID racing
    # across different position keys; the row lock below serializes
    # competing fills for one long-only position.
    session.execute(
        select(
            func.pg_advisory_xact_lock(
                func.hashtextextended(str(execution.execution_id), 0)
            )
        )
    )

    portfolio = session.get(InvestmentPortfolioModel, execution.portfolio_id)
    account = session.get(FinancialAccountModel, execution.account_id)
    instrument = session.get(InstrumentDefinitionModel, execution.instrument_id)
    if portfolio is None or portfolio.owner_id != owner_id:
        raise PortfolioScopeError("portfolio is not owned by the authenticated user")
    if account is None or account.owner_id != owner_id:
        raise PortfolioScopeError("brokerage account is not owned by the authenticated user")
    if instrument is None:
        raise PortfolioScopeError("instrument is unknown")

    existing = session.get(TradeExecutionModel, execution.execution_id)
    if existing is not None:
        if existing.owner_id != owner_id or existing.request_hash != request_hash:
            raise ExecutionIdConflict(
                "execution ID was reused by another owner or with a different payload"
            )
        # Replays use the exact historical currency definition already
        # attached to the execution, even if that currency was later withdrawn.
        currency = session.get(
            CurrencyDefinitionModel, existing.quote_currency_definition_id
        )
        if currency is None or currency.code != execution.quote_currency_code:
            raise PortfolioPersistenceError(
                "stored execution currency snapshot is unavailable or inconsistent"
            )
    else:
        if portfolio.status != "ACTIVE":
            raise PortfolioScopeError("portfolio is archived")
        if account.status != "OPEN" or account.account_type != "ASSET":
            raise PortfolioScopeError("brokerage account must be an open asset account")
        if instrument.status != "ACTIVE":
            raise PortfolioScopeError("instrument is inactive")
        # Keep one immutable currency-definition snapshot per position.
        # A later ISO release must not split one holding into two position keys.
        currency = session.scalars(
            select(CurrencyDefinitionModel)
            .join(
                TradeExecutionModel,
                TradeExecutionModel.quote_currency_definition_id
                == CurrencyDefinitionModel.id,
            )
            .where(
                TradeExecutionModel.owner_id == owner_id,
                TradeExecutionModel.portfolio_id == execution.portfolio_id,
                TradeExecutionModel.account_id == execution.account_id,
                TradeExecutionModel.instrument_id == execution.instrument_id,
                CurrencyDefinitionModel.code == execution.quote_currency_code,
            )
            .order_by(TradeExecutionModel.executed_at.asc())
            .limit(1)
        ).first()
        if currency is None:
            currency = session.scalars(
                select(CurrencyDefinitionModel).where(
                    CurrencyDefinitionModel.code == execution.quote_currency_code,
                    CurrencyDefinitionModel.registry_list == "one",
                    CurrencyDefinitionModel.withdrawal_key == "",
                    CurrencyDefinitionModel.fund.is_(False),
                    CurrencyDefinitionModel.minor_unit_exponent.is_not(None),
                )
                .order_by(CurrencyDefinitionModel.published_on.desc())
            ).first()
        if currency is None:
            raise PortfolioScopeError(
                "quote currency is not an eligible current cash currency"
            )

    if currency.minor_unit_exponent is None:
        raise PortfolioScopeError("quote currency snapshot has no minor-unit exponent")

    lock_values = {
        "owner_id": owner_id,
        "portfolio_id": execution.portfolio_id,
        "account_id": execution.account_id,
        "instrument_id": execution.instrument_id,
        "quote_currency_definition_id": currency.id,
        "lock_version": 0,
    }
    session.execute(
        pg_insert(PortfolioPositionLockModel)
        .values(**lock_values)
        .on_conflict_do_nothing(
            index_elements=[
                PortfolioPositionLockModel.owner_id,
                PortfolioPositionLockModel.portfolio_id,
                PortfolioPositionLockModel.account_id,
                PortfolioPositionLockModel.instrument_id,
                PortfolioPositionLockModel.quote_currency_definition_id,
            ]
        )
    )
    position_lock = session.scalar(
        select(PortfolioPositionLockModel)
        .where(
            PortfolioPositionLockModel.owner_id == owner_id,
            PortfolioPositionLockModel.portfolio_id == execution.portfolio_id,
            PortfolioPositionLockModel.account_id == execution.account_id,
            PortfolioPositionLockModel.instrument_id == execution.instrument_id,
            PortfolioPositionLockModel.quote_currency_definition_id == currency.id,
        )
        .with_for_update()
    )
    if position_lock is None:
        raise PortfolioPersistenceError("failed to acquire position serialization lock")

    book, applications, history = _rebuild_book(
        session,
        owner_id,
        execution.portfolio_id,
        execution.account_id,
        execution.instrument_id,
        currency.id,
        execution.quote_currency_code,
        currency.minor_unit_exponent,
    )

    if existing is not None:
        prior_application = applications.get(execution.execution_id)
        if prior_application is None:
            raise PortfolioPersistenceError("idempotent execution was not found in its position history")
        application = replace(prior_application, replayed=True)
    else:
        if history and execution.executed_at <= history[-1].executed_at:
            raise OutOfOrderExecution(
                "execution timestamp is not later than the latest recorded fill; use the explicit rebuild workflow"
            )

        precision_execution = replace(
            execution,
            currency_minor_unit_exponent=currency.minor_unit_exponent,
        )
        application = book.apply(
            precision_execution,
            cost_basis_method=cost_basis_method,
            specific_lot_id=specific_lot_id,
        )
        row = TradeExecutionModel(
            id=execution.execution_id,
            owner_id=owner_id,
            portfolio_id=execution.portfolio_id,
            account_id=execution.account_id,
            instrument_id=execution.instrument_id,
            quote_currency_definition_id=currency.id,
            side=execution.side.value.upper(),
            quantity=execution.quantity,
            unit_price=execution.unit_price,
            fee=execution.fee,
            executed_at=execution.executed_at,
            source=execution.source,
            cost_basis_method=cost_basis_method.value,
            specific_lot_id=specific_lot_id,
            request_hash=request_hash,
            accounting_precision_version=2,
            created_by=actor_id,
        )
        session.add(row)
        session.flush()

        if execution.side is TradeSide.BUY:
            opened_lot = next(
                lot for lot in book.lots if lot.lot_id == application.opened_lot_id
            )
            session.add(
                PortfolioLotModel(
                    id=opened_lot.lot_id,
                    owner_id=owner_id,
                    portfolio_id=execution.portfolio_id,
                    account_id=execution.account_id,
                    instrument_id=execution.instrument_id,
                    quote_currency_definition_id=currency.id,
                    opened_by_execution_id=execution.execution_id,
                    opened_at=execution.executed_at,
                    original_quantity=opened_lot.original_quantity,
                    original_cost=opened_lot.original_cost,
                )
            )
        else:
            session.add_all(
                [
                    LotDisposalAllocationModel(
                        id=uuid4(),
                        owner_id=owner_id,
                        portfolio_id=execution.portfolio_id,
                        account_id=execution.account_id,
                        instrument_id=execution.instrument_id,
                        quote_currency_definition_id=currency.id,
                        disposal_execution_id=execution.execution_id,
                        lot_id=item.lot_id,
                        quantity=item.quantity,
                        cost_basis=item.cost_basis,
                        gross_proceeds=item.gross_proceeds,
                        allocated_sale_fee=item.allocated_sale_fee,
                        net_proceeds=item.net_proceeds,
                        realized_gain_loss=item.realized_gain_loss,
                    )
                    for item in application.allocations
                ]
            )

        session.add(
            AuditEventModel(
                id=uuid4(),
                owner_id=owner_id,
                actor_id=actor_id,
                event_type="portfolio.trade_execution.recorded",
                aggregate_type="portfolio_trade_execution",
                aggregate_id=execution.execution_id,
                payload={
                    "portfolio_id": str(execution.portfolio_id),
                    "account_id": str(execution.account_id),
                    "instrument_id": str(execution.instrument_id),
                    "side": execution.side.value,
                    "quantity": str(execution.quantity),
                    "unit_price": str(execution.unit_price),
                    "quote_currency_code": execution.quote_currency_code,
                    "fee": str(execution.fee),
                    "cost_basis_method": cost_basis_method.value,
                    "accounting_precision_version": 2,
                    "currency_minor_unit_exponent": currency.minor_unit_exponent,
                },
            )
        )
        position_lock.lock_version += 1

    position = book.position(
        execution.portfolio_id,
        execution.account_id,
        execution.instrument_id,
        execution.quote_currency_code,
    )
    return PersistedTradeResult(application=application, position=position)


def apply_portfolio_execution(
    session_factory: Callable[[], Session],
    owner_id: int,
    actor_id: int,
    execution: TradeExecution,
    *,
    cost_basis_method: CostBasisMethod = CostBasisMethod.FIFO,
    specific_lot_id: UUID | None = None,
) -> PersistedTradeResult:
    """Transaction-owning wrapper for standalone execution recording."""
    with session_factory() as session:
        with session.begin():
            return apply_portfolio_execution_in_session(
                session,
                owner_id,
                actor_id,
                execution,
                cost_basis_method=cost_basis_method,
                specific_lot_id=specific_lot_id,
            )
