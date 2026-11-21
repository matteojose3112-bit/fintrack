"""PostgreSQL integration tests for portfolio-to-ledger account mappings."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.persistence.currency_registry_seed import seed_currency_registry
from app.persistence.models import CurrencyDefinitionModel, FinancialAccountModel
from app.persistence.portfolio_models import InvestmentPortfolioModel
from app.persistence.settlement_models import PortfolioLedgerAccountMappingModel
from app.persistence.settlement_mapping_service import (
    SettlementMappingInvalid,
    SettlementMappingNotFound,
    resolve_portfolio_ledger_mapping_in_session,
)


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="requires disposable PostgreSQL 16 database",
)


@pytest.fixture()
def pg_session():
    engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    with Session(engine) as session:
        yield session
        session.rollback()
    engine.dispose()


def make_context(session):
    owner = User(email=f"{uuid4()}@settlement-mapping.test", password_hash="test-only")
    session.add(owner)
    session.flush()
    seed_currency_registry(session)
    usd = session.scalars(
        select(CurrencyDefinitionModel).where(
            CurrencyDefinitionModel.code == "USD",
            CurrencyDefinitionModel.registry_list == "one",
            CurrencyDefinitionModel.withdrawal_key == "",
        )
    ).one()

    portfolio = InvestmentPortfolioModel(
        id=uuid4(), owner_id=owner.id, name="Settlement test", status="ACTIVE"
    )
    accounts = {
        "cash": FinancialAccountModel(
            id=uuid4(), owner_id=owner.id, name="Broker cash",
            account_type="ASSET", currency_definition_id=usd.id, status="OPEN",
        ),
        "investment": FinancialAccountModel(
            id=uuid4(), owner_id=owner.id, name="Investment control",
            account_type="ASSET", currency_definition_id=usd.id, status="OPEN",
        ),
        "gain": FinancialAccountModel(
            id=uuid4(), owner_id=owner.id, name="Realized gain",
            account_type="INCOME", currency_definition_id=usd.id, status="OPEN",
        ),
        "loss": FinancialAccountModel(
            id=uuid4(), owner_id=owner.id, name="Realized loss",
            account_type="EXPENSE", currency_definition_id=usd.id, status="OPEN",
        ),
    }
    session.add_all([portfolio, *accounts.values()])
    session.flush()
    return owner, usd, portfolio, accounts


def mapping_for(owner, usd, portfolio, accounts, **overrides):
    values = {
        "id": uuid4(),
        "owner_id": owner.id,
        "portfolio_id": portfolio.id,
        "cash_account_id": accounts["cash"].id,
        "investment_control_account_id": accounts["investment"].id,
        "realized_gain_account_id": accounts["gain"].id,
        "realized_loss_account_id": accounts["loss"].id,
        "currency_definition_id": usd.id,
    }
    values.update(overrides)
    return PortfolioLedgerAccountMappingModel(**values)


def test_postgres_accepts_valid_mapping_and_enforces_one_mapping_per_scope(pg_session):
    owner, usd, portfolio, accounts = make_context(pg_session)
    mapping = mapping_for(owner, usd, portfolio, accounts)
    pg_session.add(mapping)
    pg_session.commit()

    stored = pg_session.get(PortfolioLedgerAccountMappingModel, mapping.id)
    assert stored.owner_id == owner.id
    assert stored.cash_account_id == accounts["cash"].id
    assert stored.currency_definition_id == usd.id

    pg_session.add(mapping_for(owner, usd, portfolio, accounts))
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()


def test_postgres_rejects_wrong_account_role_and_cross_owner_mapping(pg_session):
    owner, usd, portfolio, accounts = make_context(pg_session)
    wrong_gain = FinancialAccountModel(
        id=uuid4(), owner_id=owner.id, name="Wrong role",
        account_type="ASSET", currency_definition_id=usd.id, status="OPEN",
    )
    pg_session.add(wrong_gain)
    pg_session.flush()
    invalid_role = mapping_for(
        owner, usd, portfolio, accounts,
        realized_gain_account_id=wrong_gain.id,
    )
    pg_session.add(invalid_role)
    with pytest.raises(IntegrityError, match="open INCOME"):
        pg_session.commit()
    pg_session.rollback()

    other_owner, other_usd, _, other_accounts = make_context(pg_session)
    assert other_usd.id == usd.id
    cross_owner = mapping_for(
        owner, usd, portfolio, accounts,
        realized_loss_account_id=other_accounts["loss"].id,
    )
    pg_session.add(cross_owner)
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()



def test_postgres_resolver_returns_locked_roles_and_rejects_closed_accounts(pg_session):
    owner, usd, portfolio, accounts = make_context(pg_session)
    mapping = mapping_for(owner, usd, portfolio, accounts)
    pg_session.add(mapping)
    pg_session.commit()

    with pg_session.begin():
        resolved = resolve_portfolio_ledger_mapping_in_session(
            pg_session, owner.id, portfolio.id, accounts["cash"].id, usd.id
        )
        assert resolved.mapping.id == mapping.id
        assert resolved.cash_account.id == accounts["cash"].id
        assert resolved.investment_control_account.id == accounts["investment"].id
        assert resolved.realized_gain_account.id == accounts["gain"].id
        assert resolved.realized_loss_account.id == accounts["loss"].id

    accounts["gain"].status = "CLOSED"
    pg_session.commit()
    with pg_session.begin():
        with pytest.raises(SettlementMappingInvalid, match="gain account is closed"):
            resolve_portfolio_ledger_mapping_in_session(
                pg_session, owner.id, portfolio.id, accounts["cash"].id, usd.id
            )


def test_postgres_resolver_requires_a_mapping_and_caller_transaction(pg_session):
    owner, usd, portfolio, accounts = make_context(pg_session)
    owner_id = owner.id
    portfolio_id = portfolio.id
    cash_account_id = accounts["cash"].id
    currency_definition_id = usd.id
    pg_session.commit()
    with pytest.raises(RuntimeError, match="active transaction"):
        resolve_portfolio_ledger_mapping_in_session(
            pg_session, owner_id, portfolio_id, cash_account_id, currency_definition_id
        )

    with pg_session.begin():
        with pytest.raises(SettlementMappingNotFound):
            resolve_portfolio_ledger_mapping_in_session(
                pg_session, owner_id, portfolio_id, cash_account_id, currency_definition_id
            )
