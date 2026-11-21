"""PostgreSQL integration tests for append-only reconciliation imports."""

from concurrent.futures import ThreadPoolExecutor
import os
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from app.models import User
from app.domain.reconciliation_csv import parse_statement_csv
from app.domain.reconciliation_matching import (
    MatchDecision, MatchProposal, MatchStatus, MatchStrategy,
)
from app.persistence.currency_registry_seed import seed_currency_registry
from app.persistence.models import (
    AuditEventModel,
    CurrencyDefinitionModel,
    FinancialAccountModel,
    JournalEntryModel,
    JournalPostingModel,
    ReconciliationImportBatchModel,
    ReconciliationMatchModel,
    ReconciliationStatementRowModel,
)
from app.persistence.reconciliation_import_service import persist_statement_import
from app.persistence.reconciliation_match_service import (
    confirm_reconciliation_match,
    persist_match_decisions,
    unmatch_reconciliation_match,
)


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
            ReconciliationImportBatchModel.owner_id == owner_id,
            ReconciliationImportBatchModel.account_id == account_id,
            ReconciliationImportBatchModel.file_sha256 == parsed.file_sha256,
        )) == 1
        assert session.scalar(select(func.count()).select_from(ReconciliationStatementRowModel).where(
            ReconciliationStatementRowModel.batch_id == results[0].batch_id
        )) == 2


def test_postgres_explicit_match_confirmation_is_audited_and_read_only(pg_factory):
    owner_id, account_id = setup_account(pg_factory)
    parsed = parse_statement_csv(STATEMENT, currency_exponent=2, expected_currency="USD")
    batch_result = persist(pg_factory, owner_id, account_id, parsed)

    with pg_factory() as session:
        cash = session.get(FinancialAccountModel, account_id)
        expense = FinancialAccountModel(
            id=uuid4(), owner_id=owner_id, name="Card purchases",
            account_type="EXPENSE",
            currency_definition_id=cash.currency_definition_id,
            status="OPEN",
        )
        session.add(expense)
        journal = JournalEntryModel(
            id=uuid4(), owner_id=owner_id, effective_date=date(2026, 11, 21),
            description="Card purchase", currency_definition_id=cash.currency_definition_id,
            status="POSTED", created_by=owner_id,
        )
        session.add(journal)
        session.flush()
        cash_posting = JournalPostingModel(
            id=uuid4(), journal_entry_id=journal.id, owner_id=owner_id,
            account_id=account_id, currency_definition_id=cash.currency_definition_id,
            side="CREDIT", amount_minor=2550,
        )
        expense_posting = JournalPostingModel(
            id=uuid4(), journal_entry_id=journal.id, owner_id=owner_id,
            account_id=expense.id, currency_definition_id=cash.currency_definition_id,
            side="DEBIT", amount_minor=2550,
        )
        session.add_all([cash_posting, expense_posting])
        session.commit()
        row = session.scalar(select(ReconciliationStatementRowModel).where(
            ReconciliationStatementRowModel.batch_id == batch_result.batch_id,
            ReconciliationStatementRowModel.row_number == 2,
        ))
        journal_id = journal.id
        posting_id = cash_posting.id
        session.commit()

    decisions = (
        MatchDecision(
            row_number=2,
            status=MatchStatus.PROPOSED,
            proposal=MatchProposal(
                row_number=2,
                candidate_id=posting_id,
                journal_id=journal_id,
                strategy=MatchStrategy.EXACT_AMOUNT_DATE_WINDOW,
                date_difference_days=0,
            ),
            candidate_ids=(posting_id,),
        ),
        MatchDecision(row_number=3, status=MatchStatus.UNMATCHED),
    )
    with pg_factory() as session, session.begin():
        persist_match_decisions(
            session, owner_id=owner_id, actor_id=owner_id,
            batch_id=batch_result.batch_id, decisions=decisions,
        )

    with pg_factory() as session:
        match = session.scalar(select(ReconciliationMatchModel).where(
            ReconciliationMatchModel.statement_row_id == row.id
        ))
        match_id = match.id

    with pg_factory() as session, session.begin():
        confirmed = confirm_reconciliation_match(
            session, owner_id=owner_id, actor_id=owner_id, match_id=match_id,
        )
        assert confirmed.status == "CONFIRMED"

    with pg_factory() as session:
        assert session.scalar(select(func.count()).select_from(JournalEntryModel).where(
            JournalEntryModel.id == journal_id
        )) == 1
        assert session.scalar(select(func.count()).select_from(JournalPostingModel).where(
            JournalPostingModel.id == posting_id
        )) == 1
        assert session.scalar(select(func.count()).select_from(AuditEventModel).where(
            AuditEventModel.aggregate_id == match_id,
            AuditEventModel.event_type == "RECONCILIATION_MATCH_CONFIRMED",
        )) == 1
