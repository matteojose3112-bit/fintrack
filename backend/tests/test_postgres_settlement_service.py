"""PostgreSQL integration tests for atomic portfolio/cash settlement."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import User
from app.domain.portfolio_lots import TradeExecution, TradeSide
from app.persistence.currency_registry_seed import seed_currency_registry
from app.persistence.models import (
    CurrencyDefinitionModel, FinancialAccountModel, JournalEntryModel,
    JournalPostingModel,
)
from app.persistence.instrument_models import InstrumentDefinitionModel
from app.persistence.portfolio_models import (
    InvestmentPortfolioModel, TradeExecutionModel,
)
from app.persistence.settlement_models import PortfolioLedgerAccountMappingModel
from app.persistence.posting_service import (
    PostJournalCommand, PostingLine, post_journal_in_session,
)
from app.persistence.settlement_service import (
    SettlementInsufficientCash, settle_portfolio_execution_in_session,
)

POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL, reason="requires disposable PostgreSQL 16 database"
)


@pytest.fixture()
def pg_factory():
    engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    with engine.connect() as connection:
        assert int(connection.scalar(text("SHOW server_version_num"))) >= 160000
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


def context(factory):
    with factory() as session:
        owner = User(email=f"{uuid4()}@settlement-coordinator.test", password_hash="test-only")
        session.add(owner)
        session.flush()
        seed_currency_registry(session)
        usd = session.scalars(select(CurrencyDefinitionModel).where(
            CurrencyDefinitionModel.code == "USD",
            CurrencyDefinitionModel.registry_list == "one",
            CurrencyDefinitionModel.withdrawal_key == "",
            CurrencyDefinitionModel.fund.is_(False),
        )).first()
        portfolio = InvestmentPortfolioModel(
            id=uuid4(), owner_id=owner.id, name="Coordinator test", status="ACTIVE"
        )
        accounts = {
            "cash": FinancialAccountModel(
                id=uuid4(), owner_id=owner.id, name="Broker cash",
                account_type="ASSET", currency_definition_id=usd.id, status="OPEN"
            ),
            "investment": FinancialAccountModel(
                id=uuid4(), owner_id=owner.id, name="Investment control",
                account_type="ASSET", currency_definition_id=usd.id, status="OPEN"
            ),
            "gain": FinancialAccountModel(
                id=uuid4(), owner_id=owner.id, name="Realized gain",
                account_type="INCOME", currency_definition_id=usd.id, status="OPEN"
            ),
            "loss": FinancialAccountModel(
                id=uuid4(), owner_id=owner.id, name="Realized loss",
                account_type="EXPENSE", currency_definition_id=usd.id, status="OPEN"
            ),
        }
        instrument = InstrumentDefinitionModel(
            id=uuid4(), instrument_type="equity", name="Settlement test equity",
            status="ACTIVE", source_id="settlement-coordinator-test"
        )
        session.add_all([portfolio, *accounts.values(), instrument])
        session.flush()
        session.add(PortfolioLedgerAccountMappingModel(
            id=uuid4(), owner_id=owner.id, portfolio_id=portfolio.id,
            cash_account_id=accounts["cash"].id,
            investment_control_account_id=accounts["investment"].id,
            realized_gain_account_id=accounts["gain"].id,
            realized_loss_account_id=accounts["loss"].id,
            currency_definition_id=usd.id,
        ))
        session.commit()
        return owner.id, usd.id, portfolio, accounts, instrument


def trade(portfolio, accounts, instrument, side, qty, price, fee="0", minute=0):
    return TradeExecution(
        execution_id=uuid4(), portfolio_id=portfolio.id,
        account_id=accounts["cash"].id, instrument_id=instrument.id,
        side=TradeSide(side), quantity=Decimal(qty), unit_price=Decimal(price),
        quote_currency_code="USD", fee=Decimal(fee),
        executed_at=datetime(2026, 11, 20, 15, tzinfo=timezone.utc)
        + timedelta(minutes=minute), source="manual-test",
    )


def fund_cash(factory, owner_id, usd_id, accounts, amount_minor):
    with factory() as session, session.begin():
        post_journal_in_session(
            session,
            PostJournalCommand(
                owner_id=owner_id, actor_id=owner_id,
                effective_date=datetime(2026, 11, 20, tzinfo=timezone.utc).date(),
                description="Test opening brokerage cash",
                currency_definition_id=usd_id,
                postings=(
                    PostingLine(accounts["cash"].id, "DEBIT", amount_minor),
                    PostingLine(accounts["gain"].id, "CREDIT", amount_minor),
                ),
            ),
            f"test-opening-cash:{uuid4()}",
        )


def settle(factory, owner_id, execution):
    with factory() as session, session.begin():
        return settle_portfolio_execution_in_session(
            session, owner_id, owner_id, execution
        )


def postings_for(factory, execution_id):
    with factory() as session:
        return session.scalars(
            select(JournalPostingModel)
            .join(JournalEntryModel, JournalEntryModel.id == JournalPostingModel.journal_entry_id)
            .where(
                JournalEntryModel.owner_id.is_not(None),
                JournalEntryModel.description.like(f"%{execution_id}%"),
            )
        ).all()


def test_buy_posts_cash_and_capitalized_basis_and_replays(pg_factory):
    owner_id, usd_id, portfolio, accounts, instrument = context(pg_factory)
    fund_cash(pg_factory, owner_id, usd_id, accounts, 100000)
    execution = trade(portfolio, accounts, instrument, "buy", "10", "10", "1")
    first = settle(pg_factory, owner_id, execution)
    replay = settle(pg_factory, owner_id, execution)
    assert first.journal.replayed is False
    assert replay.replayed is True
    assert replay.journal.replayed is True
    with pg_factory() as session:
        assert session.get(TradeExecutionModel, execution.execution_id) is not None
        journals = session.scalars(select(JournalEntryModel).where(
            JournalEntryModel.description.like(f"%{execution.execution_id}%")
        )).all()
        assert len(journals) == 1
        rows = session.scalars(select(JournalPostingModel).where(
            JournalPostingModel.journal_entry_id == journals[0].id
        )).all()
        assert sorted((row.side, int(row.amount_minor)) for row in rows) == [
            ("CREDIT", 10100), ("DEBIT", 10100)
        ]


def test_insufficient_cash_rejects_without_portfolio_or_journal_writes(pg_factory):
    owner_id, _, portfolio, accounts, instrument = context(pg_factory)
    execution = trade(portfolio, accounts, instrument, "buy", "10", "10", "1")
    with pytest.raises(SettlementInsufficientCash):
        settle(pg_factory, owner_id, execution)
    with pg_factory() as session:
        assert session.get(TradeExecutionModel, execution.execution_id) is None
        assert session.scalar(select(JournalEntryModel.id).where(
            JournalEntryModel.description.like(f"%{execution.execution_id}%")
        )) is None


def test_sell_posts_net_proceeds_basis_and_realized_gain(pg_factory):
    owner_id, usd_id, portfolio, accounts, instrument = context(pg_factory)
    fund_cash(pg_factory, owner_id, usd_id, accounts, 100000)
    buy = trade(portfolio, accounts, instrument, "buy", "10", "10", "1", minute=0)
    settle(pg_factory, owner_id, buy)
    sell = trade(portfolio, accounts, instrument, "sell", "4", "15", "0.60", minute=1)
    result = settle(pg_factory, owner_id, sell)
    assert result.journal.replayed is False
    with pg_factory() as session:
        journal = session.scalar(select(JournalEntryModel).where(
            JournalEntryModel.description.like(f"%{sell.execution_id}%")
        ))
        rows = session.scalars(select(JournalPostingModel).where(
            JournalPostingModel.journal_entry_id == journal.id
        )).all()
        assert sorted((row.side, int(row.amount_minor)) for row in rows) == [
            ("CREDIT", 1900), ("CREDIT", 4040), ("DEBIT", 5940)
        ]


def test_outer_rollback_removes_portfolio_fill_and_cash_journal(pg_factory):
    owner_id, usd_id, portfolio, accounts, instrument = context(pg_factory)
    fund_cash(pg_factory, owner_id, usd_id, accounts, 100000)
    execution = trade(portfolio, accounts, instrument, "buy", "2", "10", "0.50")
    with pg_factory() as session:
        with pytest.raises(RuntimeError, match="force settlement rollback"):
            with session.begin():
                settle_portfolio_execution_in_session(session, owner_id, owner_id, execution)
                raise RuntimeError("force settlement rollback")
    with pg_factory() as verify:
        assert verify.get(TradeExecutionModel, execution.execution_id) is None
        assert verify.scalar(select(JournalEntryModel.id).where(
            JournalEntryModel.description.like(f"%{execution.execution_id}%")
        )) is None



def test_concurrent_buys_cannot_overdraw_shared_brokerage_cash(pg_factory):
    owner_id, usd_id, portfolio, accounts, instrument = context(pg_factory)
    fund_cash(pg_factory, owner_id, usd_id, accounts, 10000)

    # A second portfolio shares the same brokerage cash account but has its
    # own investment-control account and position lock.
    with pg_factory() as session:
        second_portfolio = InvestmentPortfolioModel(
            id=uuid4(), owner_id=owner_id, name="Second coordinator portfolio",
            status="ACTIVE",
        )
        second_investment = FinancialAccountModel(
            id=uuid4(), owner_id=owner_id, name="Second investment control",
            account_type="ASSET",
            currency_definition_id=usd_id, status="OPEN",
        )
        session.add_all([second_portfolio, second_investment])
        session.flush()
        session.add(PortfolioLedgerAccountMappingModel(
            id=uuid4(), owner_id=owner_id, portfolio_id=second_portfolio.id,
            cash_account_id=accounts["cash"].id,
            investment_control_account_id=second_investment.id,
            realized_gain_account_id=accounts["gain"].id,
            realized_loss_account_id=accounts["loss"].id,
            currency_definition_id=usd_id,
        ))
        session.commit()

    first_trade = trade(portfolio, accounts, instrument, "buy", "6", "10", minute=0)
    second_trade = trade(
        second_portfolio, accounts, instrument, "buy", "6", "10", minute=0
    )

    def attempt(item):
        try:
            settle(pg_factory, owner_id, item)
            return True
        except SettlementInsufficientCash:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        accepted = list(pool.map(attempt, [first_trade, second_trade]))

    assert sum(accepted) == 1
    with pg_factory() as session:
        cash_rows = session.scalars(select(JournalPostingModel).where(
            JournalPostingModel.owner_id == owner_id,
            JournalPostingModel.account_id == accounts["cash"].id,
        )).all()
        debit = sum(int(row.amount_minor) for row in cash_rows if row.side == "DEBIT")
        credit = sum(int(row.amount_minor) for row in cash_rows if row.side == "CREDIT")
        assert debit - credit == 4000
