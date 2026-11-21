import pytest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import User
from app.persistence.currency_registry_seed import seed_currency_registry
from app.persistence.models import (
    CurrencyDefinitionModel,
    FinancialAccountModel,
    JournalEntryModel,
    JournalPostingModel,
)


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_registry_seed_is_idempotent_and_preserves_history():
    engine, session = make_session()
    try:
        inserted = seed_currency_registry(session)
        session.commit()
        assert inserted == 330
        assert session.scalar(select(func.count()).select_from(CurrencyDefinitionModel)) == 330

        assert seed_currency_registry(session) == 0
        session.commit()

        bgn = session.scalars(
            select(CurrencyDefinitionModel).where(
                CurrencyDefinitionModel.code == "BGN",
                CurrencyDefinitionModel.registry_list == "three",
            )
        ).one()
        assert bgn.withdrawal_key == "2026-01"
        assert bgn.minor_unit_exponent is None

        rur = session.scalars(
            select(CurrencyDefinitionModel).where(
                CurrencyDefinitionModel.code == "RUR",
                CurrencyDefinitionModel.registry_list == "three",
            )
        ).all()
        assert len(rur) == 10
        assert {row.withdrawal_key for row in rur} >= {"1993-01", "1994-08", "2004-01"}
    finally:
        session.close()
        engine.dispose()


def test_registry_seed_refuses_to_mutate_an_existing_release_record():
    engine, session = make_session()
    try:
        seed_currency_registry(session)
        session.commit()
        usd = session.scalars(
            select(CurrencyDefinitionModel).where(
                CurrencyDefinitionModel.code == "USD",
                CurrencyDefinitionModel.registry_list == "one",
            )
        ).one()
        usd.name = "tampered"
        session.commit()
        with pytest.raises(ValueError, match="immutable currency registry record changed"):
            seed_currency_registry(session)
    finally:
        session.close()
        engine.dispose()


def test_persistence_models_use_existing_integer_auth_and_exact_minor_units():
    assert isinstance(FinancialAccountModel.__table__.c.owner_id.type, type(User.__table__.c.id.type))
    amount_type = JournalPostingModel.__table__.c.amount_minor.type
    # NUMERIC without a declared scale avoids PostgreSQL pre-check rounding.
    assert amount_type.precision is None
    assert amount_type.scale is None

    account_fks = {
        fk.name for fk in JournalPostingModel.__table__.foreign_key_constraints
    }
    assert "fk_journal_postings_account_owner_currency" in account_fks
    assert "fk_journal_postings_journal_owner_currency" in account_fks

    journal_uniques = {
        constraint.name for constraint in JournalEntryModel.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert "uq_journal_entries_reversal_source" in journal_uniques
