"""Explicit, audited reconciliation proposal and confirmation workflow."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.reconciliation_matching import MatchDecision, MatchStatus
from app.persistence.models import (
    AuditEventModel,
    JournalEntryModel,
    JournalPostingModel,
    ReconciliationImportBatchModel,
    ReconciliationMatchModel,
    ReconciliationStatementRowModel,
)


class ReconciliationMatchError(Exception):
    """Base class for reconciliation state transition failures."""


class ReconciliationMatchNotFound(ReconciliationMatchError):
    """The match does not exist for the authenticated owner."""


class ReconciliationMatchConflict(ReconciliationMatchError):
    """The requested match transition is not valid from its current state."""


class ReconciliationCandidateUnavailable(ReconciliationMatchError):
    """The proposed ledger posting is not part of the imported account scope."""


@dataclass(frozen=True, slots=True)
class ProposalPersistenceResult:
    created: int
    updated: int
    unchanged: int
    protected: int


def _require_transaction(session: Session) -> None:
    if not session.in_transaction():
        raise RuntimeError("reconciliation match service requires an active transaction")


def _audit(
    session: Session,
    *,
    owner_id: int,
    actor_id: int,
    event_type: str,
    match_id: UUID,
    payload: dict,
    reason: str | None = None,
) -> None:
    session.add(AuditEventModel(
        id=uuid4(),
        owner_id=owner_id,
        actor_id=actor_id,
        event_type=event_type,
        aggregate_type="RECONCILIATION_MATCH",
        aggregate_id=match_id,
        reason=reason,
        payload=payload,
    ))


def persist_match_decisions(
    session: Session,
    *,
    owner_id: int,
    actor_id: int,
    batch_id: UUID,
    decisions: tuple[MatchDecision, ...],
) -> ProposalPersistenceResult:
    """Persist server-computed proposals; never confirms a proposed match."""
    _require_transaction(session)
    if owner_id <= 0 or actor_id <= 0:
        raise ValueError("owner_id and actor_id must be positive authenticated user IDs")

    batch = session.execute(
        select(ReconciliationImportBatchModel)
        .where(
            ReconciliationImportBatchModel.id == batch_id,
            ReconciliationImportBatchModel.owner_id == owner_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if batch is None:
        raise ReconciliationMatchNotFound("statement import was not found for this owner")

    row_models = session.scalars(
        select(ReconciliationStatementRowModel)
        .where(
            ReconciliationStatementRowModel.batch_id == batch_id,
            ReconciliationStatementRowModel.owner_id == owner_id,
        )
        .with_for_update()
    ).all()
    row_by_number = {row.row_number: row for row in row_models}
    if {decision.row_number for decision in decisions} != set(row_by_number):
        raise ValueError("match decisions must cover every statement row exactly once")

    for decision in decisions:
        if decision.status is MatchStatus.PROPOSED and decision.proposal is None:
            raise ValueError("PROPOSED decisions require a concrete ledger candidate")
        if decision.proposal is not None and decision.proposal.row_number != decision.row_number:
            raise ValueError("proposal row number must match its statement decision")

    proposed_candidate_ids = {
        decision.proposal.candidate_id
        for decision in decisions
        if decision.status is MatchStatus.PROPOSED and decision.proposal is not None
    }
    candidate_by_id = {}
    if proposed_candidate_ids:
        candidate_rows = session.execute(
            select(JournalPostingModel, JournalEntryModel)
            .join(
                JournalEntryModel,
                JournalEntryModel.id == JournalPostingModel.journal_entry_id,
            )
            .where(
                JournalPostingModel.id.in_(proposed_candidate_ids),
                JournalPostingModel.owner_id == owner_id,
                JournalPostingModel.account_id == batch.account_id,
                JournalPostingModel.currency_definition_id == batch.currency_definition_id,
                JournalEntryModel.owner_id == owner_id,
            )
            .with_for_update()
        ).all()
        candidate_by_id = {
            posting.id: (posting, journal)
            for posting, journal in candidate_rows
        }
        if set(candidate_by_id) != proposed_candidate_ids:
            raise ReconciliationCandidateUnavailable(
                "one or more proposed ledger postings are outside the account scope"
            )

        for decision in decisions:
            if decision.status is not MatchStatus.PROPOSED or decision.proposal is None:
                continue
            if decision.proposal.strategy.value != "EXACT_AMOUNT_DATE_WINDOW":
                raise ReconciliationCandidateUnavailable(
                    "this ledger schema supports only exact amount/date proposals"
                )
            row_model = row_by_number[decision.row_number]
            posting, journal = candidate_by_id[decision.proposal.candidate_id]
            signed_amount = (
                int(posting.amount_minor)
                if posting.side == "DEBIT"
                else -int(posting.amount_minor)
            )
            date_difference = abs((row_model.booking_date - journal.effective_date).days)
            if signed_amount != int(row_model.amount_minor):
                raise ReconciliationCandidateUnavailable(
                    "proposed posting amount does not equal the statement row"
                )
            if (
                date_difference != decision.proposal.date_difference_days
                or date_difference > 31
            ):
                raise ReconciliationCandidateUnavailable(
                    "proposed posting date difference is inconsistent or outside the allowed window"
                )

    created = updated = unchanged = protected = 0
    for decision in decisions:
        row_model = row_by_number[decision.row_number]
        existing = session.execute(
            select(ReconciliationMatchModel)
            .where(
                ReconciliationMatchModel.statement_row_id == row_model.id,
                ReconciliationMatchModel.owner_id == owner_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        if existing is not None and existing.status in {"CONFIRMED", "REJECTED"}:
            protected += 1
            continue

        status_value = decision.status.value
        candidate_id = (
            decision.proposal.candidate_id
            if decision.status is MatchStatus.PROPOSED and decision.proposal
            else None
        )
        strategy = (
            decision.proposal.strategy.value
            if decision.status is MatchStatus.PROPOSED and decision.proposal
            else None
        )
        difference = (
            decision.proposal.date_difference_days
            if decision.status is MatchStatus.PROPOSED and decision.proposal
            else None
        )

        if existing is not None and (
            existing.status == status_value
            and existing.journal_posting_id == candidate_id
            and existing.strategy == strategy
            and existing.date_difference_days == difference
        ):
            unchanged += 1
            continue

        if existing is None:
            match = ReconciliationMatchModel(
                id=uuid4(),
                owner_id=owner_id,
                batch_id=batch_id,
                statement_row_id=row_model.id,
                journal_posting_id=candidate_id,
                status=status_value,
                strategy=strategy,
                date_difference_days=difference,
            )
            session.add(match)
            created += 1
        else:
            match = existing
            match.journal_posting_id = candidate_id
            match.status = status_value
            match.strategy = strategy
            match.date_difference_days = difference
            match.confirmed_by = None
            match.confirmed_at = None
            match.last_action_at = func.now()
            updated += 1

        event_type = {
            "PROPOSED": "RECONCILIATION_MATCH_PROPOSED",
            "AMBIGUOUS": "RECONCILIATION_MATCH_AMBIGUOUS",
            "UNMATCHED": "RECONCILIATION_MATCH_UNMATCHED",
        }[status_value]
        _audit(
            session,
            owner_id=owner_id,
            actor_id=actor_id,
            event_type=event_type,
            match_id=match.id,
            payload={
                "batch_id": str(batch_id),
                "statement_row_id": str(row_model.id),
                "journal_posting_id": str(candidate_id) if candidate_id else None,
                "strategy": strategy,
            },
        )

    session.flush()
    return ProposalPersistenceResult(created, updated, unchanged, protected)


def confirm_reconciliation_match(
    session: Session,
    *,
    owner_id: int,
    actor_id: int,
    match_id: UUID,
) -> ReconciliationMatchModel:
    """Explicitly confirm one proposal without changing posted ledger facts."""
    _require_transaction(session)
    match = session.execute(
        select(ReconciliationMatchModel)
        .where(
            ReconciliationMatchModel.id == match_id,
            ReconciliationMatchModel.owner_id == owner_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if match is None:
        raise ReconciliationMatchNotFound("reconciliation match was not found")
    if match.status != "PROPOSED" or match.journal_posting_id is None:
        raise ReconciliationMatchConflict("only a concrete PROPOSED match can be confirmed")

    batch = session.execute(
        select(ReconciliationImportBatchModel)
        .where(
            ReconciliationImportBatchModel.id == match.batch_id,
            ReconciliationImportBatchModel.owner_id == owner_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if batch is None:
        raise ReconciliationMatchNotFound("statement import was not found")

    statement_row = session.execute(
        select(ReconciliationStatementRowModel)
        .where(
            ReconciliationStatementRowModel.id == match.statement_row_id,
            ReconciliationStatementRowModel.owner_id == owner_id,
            ReconciliationStatementRowModel.batch_id == batch.id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if statement_row is None:
        raise ReconciliationMatchNotFound("statement row was not found")

    posting_and_journal = session.execute(
        select(JournalPostingModel, JournalEntryModel)
        .join(
            JournalEntryModel,
            JournalEntryModel.id == JournalPostingModel.journal_entry_id,
        )
        .where(
            JournalPostingModel.id == match.journal_posting_id,
            JournalPostingModel.owner_id == owner_id,
            JournalPostingModel.account_id == batch.account_id,
            JournalPostingModel.currency_definition_id == batch.currency_definition_id,
            JournalEntryModel.owner_id == owner_id,
        )
        .with_for_update()
    ).one_or_none()
    if posting_and_journal is None:
        raise ReconciliationCandidateUnavailable(
            "proposed ledger posting no longer belongs to this account scope"
        )
    posting, journal = posting_and_journal
    if match.strategy != "EXACT_AMOUNT_DATE_WINDOW":
        raise ReconciliationCandidateUnavailable(
            "this ledger schema supports only exact amount/date confirmations"
        )
    signed_amount = (
        int(posting.amount_minor)
        if posting.side == "DEBIT"
        else -int(posting.amount_minor)
    )
    date_difference = abs((statement_row.booking_date - journal.effective_date).days)
    if signed_amount != int(statement_row.amount_minor):
        raise ReconciliationCandidateUnavailable(
            "proposed posting amount no longer equals the statement row"
        )
    if date_difference != match.date_difference_days or date_difference > 31:
        raise ReconciliationCandidateUnavailable(
            "proposed posting date no longer matches the recorded proposal"
        )

    match.status = "CONFIRMED"
    match.confirmed_by = actor_id
    match.confirmed_at = func.now()
    match.last_action_at = func.now()
    _audit(
        session,
        owner_id=owner_id,
        actor_id=actor_id,
        event_type="RECONCILIATION_MATCH_CONFIRMED",
        match_id=match.id,
        payload={
            "batch_id": str(match.batch_id),
            "statement_row_id": str(match.statement_row_id),
            "journal_posting_id": str(match.journal_posting_id),
        },
    )
    session.flush()
    return match


def reject_reconciliation_match(
    session: Session,
    *,
    owner_id: int,
    actor_id: int,
    match_id: UUID,
    reason: str,
) -> ReconciliationMatchModel:
    """Reject a proposal while preserving its candidate and audit history."""
    _require_transaction(session)
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ValueError("rejection reason must be 1..500 characters")
    match = session.execute(
        select(ReconciliationMatchModel)
        .where(
            ReconciliationMatchModel.id == match_id,
            ReconciliationMatchModel.owner_id == owner_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if match is None:
        raise ReconciliationMatchNotFound("reconciliation match was not found")
    if match.status != "PROPOSED":
        raise ReconciliationMatchConflict("only a PROPOSED match can be rejected")
    match.status = "REJECTED"
    match.last_action_at = func.now()
    _audit(
        session,
        owner_id=owner_id,
        actor_id=actor_id,
        event_type="RECONCILIATION_MATCH_REJECTED",
        match_id=match.id,
        payload={"journal_posting_id": str(match.journal_posting_id) if match.journal_posting_id else None},
        reason=reason.strip(),
    )
    session.flush()
    return match


def unmatch_reconciliation_match(
    session: Session,
    *,
    owner_id: int,
    actor_id: int,
    match_id: UUID,
    reason: str,
) -> ReconciliationMatchModel:
    """Revoke a confirmed link; the immutable journal entry remains untouched."""
    _require_transaction(session)
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ValueError("unmatch reason must be 1..500 characters")
    match = session.execute(
        select(ReconciliationMatchModel)
        .where(
            ReconciliationMatchModel.id == match_id,
            ReconciliationMatchModel.owner_id == owner_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if match is None:
        raise ReconciliationMatchNotFound("reconciliation match was not found")
    if match.status != "CONFIRMED":
        raise ReconciliationMatchConflict("only a CONFIRMED match can be unmatched")
    old_posting_id = match.journal_posting_id
    match.status = "UNMATCHED"
    match.confirmed_by = None
    match.confirmed_at = None
    match.last_action_at = func.now()
    _audit(
        session,
        owner_id=owner_id,
        actor_id=actor_id,
        event_type="RECONCILIATION_MATCH_UNMATCHED",
        match_id=match.id,
        payload={"previous_journal_posting_id": str(old_posting_id) if old_posting_id else None},
        reason=reason.strip(),
    )
    session.flush()
    return match
