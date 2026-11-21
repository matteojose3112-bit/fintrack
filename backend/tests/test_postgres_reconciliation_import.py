"""PostgreSQL integration tests for append-only reconciliation imports."""

from concurrent.futures import ThreadPoolExecutor
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from app.models import User
from app.domain.reconciliation_csv import parse_statement_csv
from app.persistence.currency_registry_seed import seed_currency_registry
from app.persistence.models import (
    AuditEventModel,
    CurrencyDefinitionModel,
    FinancialAccountModel,
    ReconciliationImportBatchModel,
    ReconciliationStatementRowModel,
)
from app.persistence.reconciliation_import_service import persist_statement_import


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL, reason="requires disposable PostgreSQL 16 database"
)

STATEMENT = (
    b"booking_date,amount,currency,description,source_transaction_id\n"
    b"2026-11-21,-25.50,USD,Card purchase,bank-ref-1\n"
    b"2026-11-22,100.00,USD,Deposit,bank-ref-2\n"
)


@pytest.fixture()
def pg_factory():
    engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    with engine.connect() as connection:
        assert int(connection.scalar(text("SHOW server_version_num"))) >= 160000
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


def setup_account(factory):
    with factory() as session:
        owner = User(email=f"{uuid4()}@reconciliation.test", password_hash="test-only")
        session.add(owner)
        session.flush()
        seed_currency_registry(session)
        usd = session.scalar(select(CurrencyDefinitionModel).where(
            CurrencyDefinitionModel.code == "USD",
            CurrencyDefinitionModel.registry_list == "one",
            CurrencyDefinitionModel.withdrawal_key == "",
            CurrencyDefinitionModel.fund.is_(False),
        ))
        account = FinancialAccountModel(
            id=uuid4(), owner_id=owner.id, name="Checking",
            account_type="ASSET", currency_definition_id=usd.id, status="OPEN",
        )
        session.add(account)
        session.commit()
        return owner.id, account.id


def persist(factory, owner_id, account_id, parsed):
    with factory() as session, session.begin():
        return persist_statement_import(
            session, owner_id=owner_id, account_id=account_id, parsed=parsed,
            original_filename="bank.csv",
        )


def test_postgres_import_is_idempotent_and_audited(pg_factory):
    owner_id, account_id = setup_account(pg_factory)
    parsed = parse_statement_csv(STATEMENT, currency_exponent=2, expected_currency="USD")
    first = persist(pg_factory, owner_id, account_id, parsed)
    replay = persist(pg_factory, owner_id, account_id, parsed)
    assert first.inserted is True
    assert replay.inserted is False
    assert replay.batch_id == first.batch_id

    with pg_factory() as session:
        assert session.scalar(select(func.count()).select_from(ReconciliationImportBatchModel)) >= 1
        rows = session.scalars(select(ReconciliationStatementRowModel).where(
            ReconciliationStatementRowModel.batch_id == first.batch_id
        )).all()
        assert len(rows) == 2
        assert session.scalar(select(func.count()).select_from(AuditEventModel).where(
            AuditEventModel.aggregate_id == first.batch_id
        )) == 1


def test_postgres_evidence_rows_and_batches_are_database_append_only(pg_factory):
    owner_id, account_id = setup_account(pg_factory)
    parsed = parse_statement_csv(STATEMENT, currency_exponent=2, expected_currency="USD")
    result = persist(pg_factory, owner_id, account_id, parsed)

    with pg_factory() as session:
        with pytest.raises(Exception, match="append-only"):
            with session.begin():
                batch = session.get(ReconciliationImportBatchModel, result.batch_id)
                batch.status = "HAS_ERRORS"
                session.flush()

    with pg_factory() as session:
        with pytest.raises(Exception, match="append-only"):
            with session.begin():
                row = session.scalar(select(ReconciliationStatementRowModel).where(
                    ReconciliationStatementRowModel.batch_id == result.batch_id
                ))
                session.delete(row)
                session.flush()

    with pg_factory() as session:
        assert session.get(ReconciliationImportBatchModel, result.batch_id).status == "VALIDATED"
        assert session.scalar(select(func.count()).select_from(ReconciliationStatementRowModel).where(
            ReconciliationStatementRowModel.batch_id == result.batch_id
        )) == 2


def test_concurrent_replay_creates_only_one_batch_and_row_set(pg_factory):
    owner_id, account_id = setup_account(pg_factory)
    parsed = parse_statement_csv(STATEMENT, currency_exponent=2, expected_currency="USD")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda _: persist(pg_factory, owner_id, account_id, parsed),
            range(2),
        ))
    assert sum(result.inserted for result in results) == 1
    assert results[0].batch_id == results[1].batch_id
    with pg_factory() as session:
        assert session.scalar(select(func.count()).select_from(ReconciliationImportBatchModel).where(
            ReconciliationImportBatchModel.file_sha256 == parsed.file_sha256
        )) == 1
        assert session.scalar(select(func.count()).select_from(ReconciliationStatementRowModel).where(
            ReconciliationStatementRowModel.batch_id == results[0].batch_id
        )) == 2
