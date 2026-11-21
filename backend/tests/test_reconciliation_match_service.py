from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base
from app.models import User
from app.domain.reconciliation_matching import (
    MatchDecision, MatchProposal, MatchStatus, MatchStrategy,
)
from app.persistence.currency_registry_seed import seed_currency_registry
from app.persistence.models import (
    AuditEventModel, CurrencyDefinitionModel, FinancialAccountModel,
    JournalEntryModel, JournalPostingModel, ReconciliationImportBatchModel,
    ReconciliationMatchModel, ReconciliationStatementRowModel,
)
from app.persistence.reconciliation_match_service import (
    ReconciliationMatchConflict,
    ReconciliationMatchNotFound,
    confirm_reconciliation_match,
    persist_match_decisions,
    reject_reconciliation_match,
    unmatch_reconciliation_match,
)


def fixture():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    owner = User(email=f"{uuid4()}@matches.test", password_hash="test")
    other = User(email=f"{uuid4()}@matches.test", password_hash="test")
    session.add_all([owner, other])
    session.flush()
    seed_currency_registry(session)
    usd = session.scalar(select(CurrencyDefinitionModel).where(
        CurrencyDefinitionModel.code == "USD",
        CurrencyDefinitionModel.registry_list == "one",
        CurrencyDefinitionModel.withdrawal_key == "",
    ))
    cash = FinancialAccountModel(
        id=uuid4(), owner_id=owner.id, name="Checking",
        account_type="ASSET", currency_definition_id=usd.id, status="OPEN",
    )
    income = FinancialAccountModel(
        id=uuid4(), owner_id=owner.id, name="Income",
        account_type="INCOME", currency_definition_id=usd.id, status="OPEN",
    )
    session.add_all([cash, income])
    session.flush()
    batch = ReconciliationImportBatchModel(
        id=uuid4(), owner_id=owner.id, account_id=cash.id,
        currency_definition_id=usd.id, file_sha256="a" * 64,
        parser_version="csv-v1", status="VALIDATED", row_count=2, error_count=0,
    )
    journal = JournalEntryModel(
        id=uuid4(), owner_id=owner.id, effective_date=date(2026, 11, 21),
        description="Opening deposit", currency_definition_id=usd.id,
        status="POSTED", created_by=owner.id,
    )
    session.add_all([batch, journal])
    session.flush()
    posting = JournalPostingModel(
        id=uuid4(), journal_entry_id=journal.id, owner_id=owner.id,
        account_id=cash.id, currency_definition_id=usd.id,
        side="DEBIT", amount_minor=1000,
    )
    counterpart = JournalPostingModel(
        id=uuid4(), journal_entry_id=journal.id, owner_id=owner.id,
        account_id=income.id, currency_definition_id=usd.id,
        side="CREDIT", amount_minor=1000,
    )
    session.add_all([posting, counterpart])
    rows = [
        ReconciliationStatementRowModel(
            id=uuid4(), batch_id=batch.id, owner_id=owner.id, row_number=n,
            booking_date=date(2026, 11, 21), value_date=None, amount_minor=1000,
            currency_code="USD", description="Deposit", source_transaction_id=None,
            counterparty=None, reference=None, source_payload={"amount": "10.00"},
        )
        for n in (2, 3)
    ]
    session.add_all(rows)
    session.commit()
    return engine, session, owner, other, usd, cash, batch, journal, posting, rows


def proposal(row_number, posting, journal):
    return MatchDecision(
        row_number=row_number,
        status=MatchStatus.PROPOSED,
        proposal=MatchProposal(
            row_number=row_number,
            candidate_id=posting.id,
            journal_id=journal.id,
            strategy=MatchStrategy.EXACT_AMOUNT_DATE_WINDOW,
            date_difference_days=0,
        ),
        candidate_ids=(posting.id,),
    )


def test_proposals_are_persisted_and_never_auto_confirmed():
    engine, session, owner, _, _, _, batch, journal, posting, rows = fixture()
    try:
        decisions = (proposal(2, posting, journal), MatchDecision(3, MatchStatus.UNMATCHED))
        with session.begin():
            result = persist_match_decisions(
                session, owner_id=owner.id, actor_id=owner.id,
                batch_id=batch.id, decisions=decisions,
            )
        assert result.created == 2
        matches = session.scalars(select(ReconciliationMatchModel).order_by(
            ReconciliationMatchModel.statement_row_id
        )).all()
        assert {item.status for item in matches} == {"PROPOSED", "UNMATCHED"}
        assert session.scalar(select(func.count()).select_from(JournalEntryModel)) == 1
        assert session.scalar(select(func.count()).select_from(JournalPostingModel)) == 2
        assert session.scalar(select(func.count()).select_from(AuditEventModel)) == 2
    finally:
        session.close()
        engine.dispose()


def test_confirm_unmatch_and_reconfirm_are_audited_without_ledger_mutation():
    engine, session, owner, _, _, _, batch, journal, posting, rows = fixture()
    try:
        with session.begin():
            persist_match_decisions(
                session, owner_id=owner.id, actor_id=owner.id, batch_id=batch.id,
                decisions=(proposal(2, posting, journal), MatchDecision(3, MatchStatus.UNMATCHED)),
            )
        match = session.scalar(select(ReconciliationMatchModel).where(
            ReconciliationMatchModel.statement_row_id == rows[0].id
        ))
        session.commit()
        with session.begin():
            confirmed = confirm_reconciliation_match(
                session, owner_id=owner.id, actor_id=owner.id, match_id=match.id,
            )
            assert confirmed.status == "CONFIRMED"
        with session.begin():
            unmatched = unmatch_reconciliation_match(
                session, owner_id=owner.id, actor_id=owner.id,
                match_id=match.id, reason="Statement row was linked to the wrong entry",
            )
            assert unmatched.status == "UNMATCHED"
        with session.begin():
            confirm_reconciliation_match(
                session, owner_id=owner.id, actor_id=owner.id, match_id=match.id,
            )
        assert session.scalar(select(func.count()).select_from(JournalEntryModel)) == 1
        assert session.scalar(select(func.count()).select_from(JournalPostingModel)) == 2
        event_types = set(session.scalars(select(AuditEventModel.event_type)).all())
        assert {
            "RECONCILIATION_MATCH_PROPOSED",
            "RECONCILIATION_MATCH_CONFIRMED",
            "RECONCILIATION_MATCH_UNMATCHED",
        }.issubset(event_types)
    finally:
        session.close()
        engine.dispose()


def test_confirmed_posting_cannot_be_assigned_to_two_statement_rows():
    engine, session, owner, _, _, _, batch, journal, posting, rows = fixture()
    try:
        with session.begin():
            persist_match_decisions(
                session, owner_id=owner.id, actor_id=owner.id, batch_id=batch.id,
                decisions=(proposal(2, posting, journal), MatchDecision(3, MatchStatus.UNMATCHED)),
            )
        first = session.scalar(select(ReconciliationMatchModel).where(
            ReconciliationMatchModel.statement_row_id == rows[0].id
        ))
        with session.begin():
            confirm_reconciliation_match(
                session, owner_id=owner.id, actor_id=owner.id, match_id=first.id,
            )
        with session.begin():
            persist_match_decisions(
                session, owner_id=owner.id, actor_id=owner.id, batch_id=batch.id,
                decisions=(MatchDecision(2, MatchStatus.PROPOSED, proposal(2, posting, journal).proposal),
                           proposal(3, posting, journal)),
            )
        second = session.scalar(select(ReconciliationMatchModel).where(
            ReconciliationMatchModel.statement_row_id == rows[1].id
        ))
        session.commit()
        with session.begin(), pytest.raises(IntegrityError):
            confirm_reconciliation_match(
                session, owner_id=owner.id, actor_id=owner.id, match_id=second.id,
            )
    finally:
        session.close()
        engine.dispose()


def test_rejection_is_preserved_when_proposals_are_regenerated():
    engine, session, owner, _, _, _, batch, journal, posting, rows = fixture()
    try:
        with session.begin():
            persist_match_decisions(
                session, owner_id=owner.id, actor_id=owner.id, batch_id=batch.id,
                decisions=(proposal(2, posting, journal), MatchDecision(3, MatchStatus.UNMATCHED)),
            )
        match = session.scalar(select(ReconciliationMatchModel).where(
            ReconciliationMatchModel.statement_row_id == rows[0].id
        ))
        with session.begin():
            reject_reconciliation_match(
                session, owner_id=owner.id, actor_id=owner.id, match_id=match.id,
                reason="Not the same transaction",
            )
        with session.begin():
            result = persist_match_decisions(
                session, owner_id=owner.id, actor_id=owner.id, batch_id=batch.id,
                decisions=(proposal(2, posting, journal), MatchDecision(3, MatchStatus.UNMATCHED)),
            )
        assert result.protected == 1
        assert session.get(ReconciliationMatchModel, match.id).status == "REJECTED"
    finally:
        session.close()
        engine.dispose()


def test_match_lookup_is_owner_scoped():
    engine, session, owner, other, _, _, batch, journal, posting, _ = fixture()
    try:
        with session.begin(), pytest.raises(ReconciliationMatchNotFound):
            confirm_reconciliation_match(
                session, owner_id=other.id, actor_id=other.id, match_id=uuid4(),
            )
    finally:
        session.close()
        engine.dispose()
