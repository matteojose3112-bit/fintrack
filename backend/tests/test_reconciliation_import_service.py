from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.domain.reconciliation_csv import parse_statement_csv
from app.models import User
from app.persistence.currency_registry_seed import seed_currency_registry
from app.persistence.models import (
    CurrencyDefinitionModel,
    FinancialAccountModel,
    JournalEntryModel,
    ReconciliationImportBatchModel,
    ReconciliationStatementRowModel,
)
from app.persistence.reconciliation_import_service import (
    InvalidStatementEvidence,
    ReconciliationAccountUnavailable,
    persist_statement_import,
)


CSV = (
    b"booking_date,amount,currency,description,source_transaction_id\n"
    b"2026-11-21,-25.50,USD,=SUM(1+1),bank-tx-1\n"
    b"2026-11-22,100.00,USD,Salary,bank-tx-2\n"
)


def make_fixture():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    owner = User(email="owner@example.com", password_hash="test-hash")
    stranger = User(email="stranger@example.com", password_hash="test-hash")
    session.add_all([owner, stranger])
    session.flush()
    seed_currency_registry(session)
    usd = session.scalar(
        select(CurrencyDefinitionModel).where(
            CurrencyDefinitionModel.code == "USD",
            CurrencyDefinitionModel.registry_list == "one",
        )
    )
    account = FinancialAccountModel(
        id=uuid4(), owner_id=owner.id, name="Checking",
        account_type="ASSET", currency_definition_id=usd.id, status="OPEN",
    )
    session.add(account)
    session.commit()
    return engine, session, owner, stranger, usd, account


def test_valid_statement_import_persists_immutable_evidence_and_is_idempotent():
    engine, session, owner, _, usd, account = make_fixture()
    try:
        parsed = parse_statement_csv(CSV, currency_exponent=2, expected_currency="USD")
        with session.begin():
            first = persist_statement_import(
                session, owner_id=owner.id, account_id=account.id,
                parsed=parsed, original_filename="../../bank.csv",
            )
        assert first.inserted is True
        assert first.row_count == 2

        with session.begin():
            replay = persist_statement_import(
                session, owner_id=owner.id, account_id=account.id, parsed=parsed,
            )
        assert replay.inserted is False
        assert replay.batch_id == first.batch_id
        assert session.scalar(select(func.count()).select_from(ReconciliationImportBatchModel)) == 1
        assert session.scalar(select(func.count()).select_from(ReconciliationStatementRowModel)) == 2
        assert session.scalar(select(func.count()).select_from(JournalEntryModel)) == 0

        batch = session.get(ReconciliationImportBatchModel, first.batch_id)
        assert batch.original_filename == "bank.csv"
        row = session.scalars(
            select(ReconciliationStatementRowModel)
            .where(ReconciliationStatementRowModel.batch_id == first.batch_id)
            .order_by(ReconciliationStatementRowModel.row_number)
        ).first()
        assert row.amount_minor == -2550
        assert row.source_payload["description"] == "=SUM(1+1)"
        assert row.currency_code == "USD"
    finally:
        session.close()
        engine.dispose()


def test_same_file_is_distinct_for_a_different_parser_version():
    engine, session, owner, _, _, account = make_fixture()
    try:
        parsed = parse_statement_csv(CSV, currency_exponent=2, expected_currency="USD")
        with session.begin():
            first = persist_statement_import(
                session, owner_id=owner.id, account_id=account.id,
                parsed=parsed, parser_version="csv-v1",
            )
        with session.begin():
            second = persist_statement_import(
                session, owner_id=owner.id, account_id=account.id,
                parsed=parsed, parser_version="csv-v2",
            )
        assert first.batch_id != second.batch_id
        assert session.scalar(select(func.count()).select_from(ReconciliationImportBatchModel)) == 2
    finally:
        session.close()
        engine.dispose()


def test_import_rejects_partial_invalid_parse_without_creating_batch():
    engine, session, owner, _, _, account = make_fixture()
    try:
        parsed = parse_statement_csv(
            b"booking_date,amount,currency,description\n2026-11-21,1.001,USD,bad\n",
            currency_exponent=2,
        )
        with session.begin(), pytest.raises(InvalidStatementEvidence):
            persist_statement_import(
                session, owner_id=owner.id, account_id=account.id, parsed=parsed,
            )
        assert session.scalar(select(func.count()).select_from(ReconciliationImportBatchModel)) == 0
    finally:
        session.close()
        engine.dispose()


def test_import_rejects_cross_owner_account_access():
    engine, session, _, stranger, _, account = make_fixture()
    try:
        parsed = parse_statement_csv(CSV, currency_exponent=2, expected_currency="USD")
        with session.begin(), pytest.raises(ReconciliationAccountUnavailable):
            persist_statement_import(
                session, owner_id=stranger.id, account_id=account.id, parsed=parsed,
            )
        assert session.scalar(select(func.count()).select_from(ReconciliationImportBatchModel)) == 0
    finally:
        session.close()
        engine.dispose()


def test_import_rejects_non_asset_or_closed_accounts():
    engine, session, owner, _, _, account = make_fixture()
    try:
        account.status = "CLOSED"
        session.commit()
        parsed = parse_statement_csv(CSV, currency_exponent=2, expected_currency="USD")
        with session.begin(), pytest.raises(ReconciliationAccountUnavailable):
            persist_statement_import(
                session, owner_id=owner.id, account_id=account.id, parsed=parsed,
            )
        assert session.scalar(select(func.count()).select_from(ReconciliationImportBatchModel)) == 0
    finally:
        session.close()
        engine.dispose()
