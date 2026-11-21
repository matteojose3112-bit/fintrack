"""PostgreSQL integration tests for the atomic portfolio lot service."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import User
from app.domain.portfolio_lots import (
    PortfolioAccountingError,
    TradeExecution,
    TradeSide,
)
from app.persistence.currency_registry_seed import seed_currency_registry
from app.persistence.models import AuditEventModel, CurrencyDefinitionModel, FinancialAccountModel
from app.persistence.instrument_models import InstrumentDefinitionModel
from app.persistence.portfolio_models import InvestmentPortfolioModel, PortfolioLotModel, TradeExecutionModel
from app.persistence.portfolio_lot_service import (
    ExecutionIdConflict,
    OutOfOrderExecution,
    apply_portfolio_execution,
    apply_portfolio_execution_in_session,
)


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="requires disposable PostgreSQL 16 database",
)


@pytest.fixture()
def pg_factory():
    engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    with engine.connect() as connection:
        assert int(connection.scalar(text("SHOW server_version_num"))) >= 160000
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


def make_context(factory):
    with factory() as session:
        owner = User(email=f"{uuid4()}@portfolio-service.test", password_hash="test-only")
        session.add(owner)
        session.flush()
        seed_currency_registry(session)
        usd = session.scalars(
            select(CurrencyDefinitionModel).where(
                CurrencyDefinitionModel.code == "USD",
                CurrencyDefinitionModel.registry_list == "one",
                CurrencyDefinitionModel.withdrawal_key == "",
                CurrencyDefinitionModel.fund.is_(False),
            )
        ).first()
        account = FinancialAccountModel(
            id=uuid4(), owner_id=owner.id, name="Brokerage",
            account_type="ASSET", currency_definition_id=usd.id, status="OPEN",
        )
        instrument = InstrumentDefinitionModel(
            id=uuid4(), instrument_type="equity", name="Service test equity",
            status="ACTIVE", source_id="portfolio-service-test",
        )
        portfolio = InvestmentPortfolioModel(
            id=uuid4(), owner_id=owner.id, name="Service test portfolio", status="ACTIVE",
        )
        session.add_all([account, instrument, portfolio])
        session.commit()
        return owner.id, account, instrument, portfolio


def make_trade(portfolio, account, instrument, *, side, quantity, price, fee="0",
               minute=0, execution_id=None):
    return TradeExecution(
        execution_id=execution_id or uuid4(),
        portfolio_id=portfolio.id,
        account_id=account.id,
        instrument_id=instrument.id,
        side=TradeSide(side),
        quantity=Decimal(quantity),
        unit_price=Decimal(price),
        quote_currency_code="USD",
        fee=Decimal(fee),
        executed_at=datetime(2026, 11, 17, 15, 30, tzinfo=timezone.utc)
        + timedelta(minutes=minute),
        source="broker-import-test",
    )


def test_service_buy_sell_and_same_payload_replay(pg_factory):
    owner_id, account, instrument, portfolio = make_context(pg_factory)
    buy = make_trade(portfolio, account, instrument, side="buy",
                     quantity="10", price="10", minute=0)
    first = apply_portfolio_execution(pg_factory, owner_id, owner_id, buy)
    replay = apply_portfolio_execution(pg_factory, owner_id, owner_id, buy)
    assert first.application.opened_lot_id is not None
    assert replay.application.replayed is True
    assert replay.position.quantity == Decimal("10")

    sell = make_trade(portfolio, account, instrument, side="sell",
                      quantity="3", price="15", fee="3", minute=1)
    sold = apply_portfolio_execution(pg_factory, owner_id, owner_id, sell)
    assert sold.application.realized_gain_loss == Decimal("12")
    assert sold.position.quantity == Decimal("7")
    assert sold.position.remaining_cost_basis == Decimal("70")



def test_session_bound_portfolio_execution_rolls_back_with_outer_transaction(pg_factory):
    owner_id, account, instrument, portfolio = make_context(pg_factory)
    trade = make_trade(
        portfolio, account, instrument, side="buy",
        quantity="4", price="12.50", fee="1.25",
    )

    with pg_factory() as session:
        with pytest.raises(RuntimeError, match="force outer transaction rollback"):
            with session.begin():
                result = apply_portfolio_execution_in_session(
                    session, owner_id, owner_id, trade
                )
                assert result.position.quantity == Decimal("4")
                assert session.in_transaction()
                raise RuntimeError("force outer transaction rollback")

    with pg_factory() as verify:
        assert verify.get(TradeExecutionModel, trade.execution_id) is None
        assert verify.scalar(
            select(PortfolioLotModel.id).where(
                PortfolioLotModel.opened_by_execution_id == trade.execution_id
            )
        ) is None
        assert verify.scalar(
            select(AuditEventModel.id).where(
                AuditEventModel.owner_id == owner_id,
                AuditEventModel.aggregate_id == trade.execution_id,
                AuditEventModel.event_type == "portfolio.trade_execution.recorded",
            )
        ) is None


def test_service_rejects_execution_id_payload_reuse(pg_factory):
    owner_id, account, instrument, portfolio = make_context(pg_factory)
    execution_id = uuid4()
    first = make_trade(portfolio, account, instrument, side="buy",
                       quantity="1", price="10", execution_id=execution_id)
    apply_portfolio_execution(pg_factory, owner_id, owner_id, first)
    changed = make_trade(portfolio, account, instrument, side="buy",
                         quantity="2", price="10", execution_id=execution_id)
    with pytest.raises(ExecutionIdConflict):
        apply_portfolio_execution(pg_factory, owner_id, owner_id, changed)


def test_service_oversell_rolls_back_execution(pg_factory):
    owner_id, account, instrument, portfolio = make_context(pg_factory)
    buy = make_trade(portfolio, account, instrument, side="buy",
                     quantity="2", price="10", minute=0)
    apply_portfolio_execution(pg_factory, owner_id, owner_id, buy)
    sell = make_trade(portfolio, account, instrument, side="sell",
                      quantity="3", price="12", minute=1)
    with pytest.raises(PortfolioAccountingError):
        apply_portfolio_execution(pg_factory, owner_id, owner_id, sell)
    with pg_factory() as verify:
        assert verify.get(TradeExecutionModel, sell.execution_id) is None
        assert verify.get(TradeExecutionModel, buy.execution_id) is not None


def test_service_serializes_competing_oversells(pg_factory):
    owner_id, account, instrument, portfolio = make_context(pg_factory)
    buy = make_trade(portfolio, account, instrument, side="buy",
                     quantity="10", price="10", minute=0)
    apply_portfolio_execution(pg_factory, owner_id, owner_id, buy)
    sells = [
        make_trade(portfolio, account, instrument, side="sell",
                   quantity="7", price="12", minute=1),
        make_trade(portfolio, account, instrument, side="sell",
                   quantity="7", price="12", minute=2),
    ]

    def attempt(item):
        try:
            return apply_portfolio_execution(pg_factory, owner_id, owner_id, item)
        except (PortfolioAccountingError, OutOfOrderExecution):
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, sells))
    assert sum(result is not None for result in results) == 1

    with pg_factory() as verify:
        rows = verify.scalars(
            select(TradeExecutionModel).where(
                TradeExecutionModel.portfolio_id == portfolio.id,
                TradeExecutionModel.side == "SELL",
            )
        ).all()
        assert len(rows) == 1


def test_service_persists_currency_scale_and_precision_policy_version(pg_factory):
    owner_id, account, instrument, portfolio = make_context(pg_factory)
    trade = make_trade(
        portfolio, account, instrument, side="buy",
        quantity="1", price="1.005", fee="0.004",
    )
    result = apply_portfolio_execution(pg_factory, owner_id, owner_id, trade)
    assert result.position.remaining_cost_basis == Decimal("1.01")
    with pg_factory() as session:
        execution_row = session.get(TradeExecutionModel, trade.execution_id)
        assert execution_row.accounting_precision_version == 2
        lot = session.scalar(
            select(PortfolioLotModel).where(
                PortfolioLotModel.opened_by_execution_id == trade.execution_id
            )
        )
        assert Decimal(lot.original_cost) == Decimal("1.01")
