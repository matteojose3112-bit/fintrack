"""PostgreSQL integration tests for append-only portfolio lot persistence."""

from datetime import datetime, timezone
from decimal import Decimal
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.persistence.currency_registry_seed import seed_currency_registry
from app.persistence.models import CurrencyDefinitionModel, FinancialAccountModel
from app.persistence.instrument_models import InstrumentDefinitionModel
from app.persistence.portfolio_models import (
    InvestmentPortfolioModel,
    LotDisposalAllocationModel,
    PortfolioLotModel,
    PortfolioPositionLockModel,
    TradeExecutionModel,
)


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="requires disposable PostgreSQL 16 database",
)


@pytest.fixture()
def pg_session():
    engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    with engine.connect() as connection:
        version = int(connection.scalar(text("SHOW server_version_num")))
        assert version >= 160000
    with Session(engine) as session:
        yield session
        session.rollback()
    engine.dispose()


def context(session, email=None):
    owner = User(email=email or f"{uuid4()}@portfolio.test", password_hash="test-only")
    session.add(owner)
    session.flush()
    seed_currency_registry(session)
    usd = session.scalars(
        select(CurrencyDefinitionModel).where(
            CurrencyDefinitionModel.code == "USD",
            CurrencyDefinitionModel.registry_list == "one",
            CurrencyDefinitionModel.withdrawal_key == "",
        )
    ).first()
    account = FinancialAccountModel(
        id=uuid4(), owner_id=owner.id, name="Brokerage",
        account_type="ASSET", currency_definition_id=usd.id, status="OPEN",
    )
    instrument = InstrumentDefinitionModel(
        id=uuid4(), instrument_type="equity", name="Test listed equity",
        status="ACTIVE", source_id="portfolio-test",
    )
    portfolio = InvestmentPortfolioModel(
        id=uuid4(), owner_id=owner.id, name="Long-term portfolio", status="ACTIVE",
    )
    session.add_all([account, instrument, portfolio])
    session.flush()
    return owner, usd, account, instrument, portfolio


def execution(owner, usd, account, instrument, portfolio, *, side="BUY", quantity="2.5",
              price="123.456789", fee="0.0001", execution_id=None):
    return TradeExecutionModel(
        id=execution_id or uuid4(),
        owner_id=owner.id,
        portfolio_id=portfolio.id,
        account_id=account.id,
        instrument_id=instrument.id,
        quote_currency_definition_id=usd.id,
        side=side,
        quantity=Decimal(quantity),
        unit_price=Decimal(price),
        fee=Decimal(fee),
        executed_at=datetime(2026, 11, 17, 15, 30, tzinfo=timezone.utc),
        source="broker-import",
        cost_basis_method="fifo",
        specific_lot_id=None,
        request_hash="a" * 64,
        created_by=owner.id,
    )


def test_postgres_persists_unscaled_decimal_trade_values_exactly(pg_session):
    owner, usd, account, instrument, portfolio = context(pg_session)
    fill = execution(owner, usd, account, instrument, portfolio)
    pg_session.add(fill)
    pg_session.commit()

    stored = pg_session.get(TradeExecutionModel, fill.id)
    assert stored.quantity == Decimal("2.5")
    assert stored.unit_price == Decimal("123.456789")
    assert stored.fee == Decimal("0.0001")


def test_postgres_rejects_cross_owner_brokerage_account_reference(pg_session):
    owner_a, usd_a, _, instrument, portfolio = context(pg_session)
    owner_b, usd_b, account_b, _, _ = context(pg_session)
    assert usd_a.id == usd_b.id

    invalid = execution(owner_a, usd_a, account_b, instrument, portfolio)
    pg_session.add(invalid)
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_lot_and_disposal_rows_are_append_only(pg_session):
    owner, usd, account, instrument, portfolio = context(pg_session)
    buy = execution(owner, usd, account, instrument, portfolio)
    pg_session.add(buy)
    pg_session.flush()

    lot = PortfolioLotModel(
        id=uuid4(), owner_id=owner.id, portfolio_id=portfolio.id,
        account_id=account.id, instrument_id=instrument.id,
        quote_currency_definition_id=usd.id, opened_by_execution_id=buy.id,
        opened_at=buy.executed_at, original_quantity=buy.quantity,
        original_cost=buy.quantity * buy.unit_price + buy.fee,
    )
    pg_session.add(lot)
    pg_session.commit()

    lot.original_cost = Decimal("1")
    with pytest.raises(DBAPIError, match="append-only"):
        pg_session.commit()
    pg_session.rollback()

    sell = execution(owner, usd, account, instrument, portfolio, side="SELL")
    pg_session.add(sell)
    pg_session.flush()
    allocation = LotDisposalAllocationModel(
        id=uuid4(), owner_id=owner.id, portfolio_id=portfolio.id,
        account_id=account.id, instrument_id=instrument.id,
        quote_currency_definition_id=usd.id, disposal_execution_id=sell.id,
        lot_id=lot.id, quantity=Decimal("1"), cost_basis=Decimal("10"),
        gross_proceeds=Decimal("20"), allocated_sale_fee=Decimal("0"),
        net_proceeds=Decimal("20"), realized_gain_loss=Decimal("10"),
    )
    pg_session.add(allocation)
    pg_session.commit()
    allocation.realized_gain_loss = Decimal("999")
    with pytest.raises(DBAPIError, match="append-only"):
        pg_session.commit()
    pg_session.rollback()

    # The operational lock row is intentionally mutable; it is not financial history.
    lock = PortfolioPositionLockModel(
        owner_id=owner.id, portfolio_id=portfolio.id, account_id=account.id,
        instrument_id=instrument.id, quote_currency_definition_id=usd.id,
        lock_version=0,
    )
    pg_session.add(lock)
    pg_session.commit()
    lock.lock_version = 1
    pg_session.commit()
    assert lock.lock_version == 1


def test_postgres_disposal_allocation_must_match_execution_and_lot_scope(pg_session):
    owner, usd, account, instrument, portfolio = context(pg_session)
    buy = execution(owner, usd, account, instrument, portfolio)
    pg_session.add(buy)
    pg_session.flush()
    lot = PortfolioLotModel(
        id=uuid4(), owner_id=owner.id, portfolio_id=portfolio.id,
        account_id=account.id, instrument_id=instrument.id,
        quote_currency_definition_id=usd.id, opened_by_execution_id=buy.id,
        opened_at=buy.executed_at, original_quantity=buy.quantity,
        original_cost=buy.quantity * buy.unit_price + buy.fee,
    )
    sell = execution(owner, usd, account, instrument, portfolio, side="SELL")
    pg_session.add_all([lot, sell])
    pg_session.flush()

    allocation = LotDisposalAllocationModel(
        id=uuid4(), owner_id=owner.id, portfolio_id=portfolio.id,
        account_id=account.id, instrument_id=instrument.id,
        quote_currency_definition_id=usd.id, disposal_execution_id=sell.id,
        lot_id=uuid4(), quantity=Decimal("1"), cost_basis=Decimal("10"),
        gross_proceeds=Decimal("20"), allocated_sale_fee=Decimal("0"),
        net_proceeds=Decimal("20"), realized_gain_loss=Decimal("10"),
    )
    pg_session.add(allocation)
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()
