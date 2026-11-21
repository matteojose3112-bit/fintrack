"""Atomic PostgreSQL posting and reversal application services.

The service owns its Session and transaction. A single transaction claims the
idempotency key, locks accounts, inserts immutable journal rows and audit data,
completes the idempotency response, and commits. Database deferred triggers
remain the final authority for balanced posting and reversal invariants.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from time import sleep
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.persistence.models import (
    AccountingPeriodModel,
    AuditEventModel,
    CurrencyDefinitionModel,
    FinancialAccountModel,
    IdempotencyRecordModel,
    JournalEntryModel,
    JournalPostingModel,
)


MAX_MINOR_UNITS = 10**38 - 1
CREATE_OPERATION = "ledger.create_journal"
REVERSE_OPERATION = "ledger.reverse_journal"


class PostingServiceError(Exception):
    """Base class for deterministic posting application errors."""


class IdempotencyConflict(PostingServiceError):
    """An idempotency key was reused with a different canonical request."""


class IdempotencyInProgress(PostingServiceError):
    """A persisted idempotency claim has no completed result."""


class InvalidJournal(PostingServiceError):
    """The proposed journal violates a domain/application invariant."""


class AccountNotFound(PostingServiceError):
    """One or more requested accounts do not exist or are not owned by caller."""


class AccountClosed(PostingServiceError):
    """An ordinary journal cannot post to a closed account."""


class CurrencyMismatch(PostingServiceError):
    """The account currency definition does not match the journal."""


class AccountingPeriodUnavailable(PostingServiceError):
    """Configured accounting periods do not allow the effective date."""


class JournalNotFound(PostingServiceError):
    """The requested source journal does not exist for the owner."""


class JournalAlreadyReversed(PostingServiceError):
    """The source journal already has a reversal."""


@dataclass(frozen=True, slots=True)
class PostingLine:
    account_id: UUID
    side: str
    amount_minor: int

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, UUID):
            raise TypeError("posting account_id must be UUID")
        side = self.side.upper() if isinstance(self.side, str) else ""
        if side not in {"DEBIT", "CREDIT"}:
            raise ValueError("posting side must be DEBIT or CREDIT")
        if isinstance(self.amount_minor, bool) or not isinstance(self.amount_minor, int):
            raise TypeError("amount_minor must be an integer")
        if self.amount_minor <= 0 or self.amount_minor > MAX_MINOR_UNITS:
            raise ValueError("amount_minor must be within 1..10^38-1")
        object.__setattr__(self, "side", side)


@dataclass(frozen=True, slots=True)
class PostJournalCommand:
    owner_id: int
    actor_id: int
    effective_date: date
    description: str
    currency_definition_id: UUID
    postings: tuple[PostingLine, ...]

    def __post_init__(self) -> None:
        for name, value in (("owner_id", self.owner_id), ("actor_id", self.actor_id)):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive authenticated user ID")
        if not isinstance(self.effective_date, date) or isinstance(self.effective_date, datetime):
            raise TypeError("effective_date must be a calendar date")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("description must be non-empty")
        if not isinstance(self.currency_definition_id, UUID):
            raise TypeError("currency_definition_id must be UUID")
        lines = tuple(self.postings)
        if len(lines) < 2 or any(not isinstance(line, PostingLine) for line in lines):
            raise InvalidJournal("a journal requires at least two valid posting lines")
        account_ids = [line.account_id for line in lines]
        if len(set(account_ids)) != len(account_ids):
            raise InvalidJournal("an account may appear only once in a journal")
        debit = sum(line.amount_minor for line in lines if line.side == "DEBIT")
        credit = sum(line.amount_minor for line in lines if line.side == "CREDIT")
        if debit != credit:
            raise InvalidJournal("journal debits must equal credits")
        object.__setattr__(self, "postings", lines)


@dataclass(frozen=True, slots=True)
class ReverseJournalCommand:
    owner_id: int
    actor_id: int
    source_journal_id: UUID
    effective_date: date
    description: str = "Journal reversal"

    def __post_init__(self) -> None:
        for name, value in (("owner_id", self.owner_id), ("actor_id", self.actor_id)):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive authenticated user ID")
        if not isinstance(self.source_journal_id, UUID):
            raise TypeError("source_journal_id must be UUID")
        if not isinstance(self.effective_date, date) or isinstance(self.effective_date, datetime):
            raise TypeError("effective_date must be a calendar date")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("description must be non-empty")


@dataclass(frozen=True, slots=True)
class PostingResult:
    status_code: int
    body: dict
    replayed: bool = False


def _validate_idempotency_key(key: str) -> str:
    if not isinstance(key, str) or not key.strip() or len(key) > 255:
        raise ValueError("Idempotency-Key must be a non-empty string up to 255 characters")
    return key


def _hash_payload(payload: dict) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _claim_idempotency(
    session: Session,
    owner_id: int,
    operation: str,
    key: str,
    request_hash: str,
) -> tuple[IdempotencyRecordModel | None, PostingResult | None]:
    record_id = uuid4()
    statement = (
        pg_insert(IdempotencyRecordModel)
        .values(
            id=record_id,
            owner_id=owner_id,
            operation=operation,
            idempotency_key=key,
            request_hash=request_hash,
        )
        .on_conflict_do_nothing(
            index_elements=[
                IdempotencyRecordModel.owner_id,
                IdempotencyRecordModel.operation,
                IdempotencyRecordModel.idempotency_key,
            ]
        )
        .returning(IdempotencyRecordModel.id)
    )
    claimed_id = session.execute(statement).scalar_one_or_none()
    if claimed_id is not None:
        return session.get(IdempotencyRecordModel, claimed_id), None

    existing = session.execute(
        select(IdempotencyRecordModel)
        .where(
            IdempotencyRecordModel.owner_id == owner_id,
            IdempotencyRecordModel.operation == operation,
            IdempotencyRecordModel.idempotency_key == key,
        )
        .with_for_update()
    ).scalar_one()
    if existing.request_hash != request_hash:
        raise IdempotencyConflict("Idempotency-Key was already used with a different request")
    if (
        existing.completed_at is None
        or existing.response_status is None
        or existing.response_body is None
    ):
        raise IdempotencyInProgress("Idempotency-Key has no committed result")
    return None, PostingResult(
        status_code=existing.response_status,
        body=existing.response_body,
        replayed=True,
    )


def _complete_idempotency(
    record: IdempotencyRecordModel,
    journal: JournalEntryModel,
    status_code: int,
    body: dict,
) -> None:
    record.journal_entry_id = journal.id
    record.response_status = status_code
    record.response_body = body
    record.completed_at = func.now()


def _check_period(session: Session, owner_id: int, effective_date: date) -> None:
    configured_period_count = session.scalar(
        select(func.count())
        .select_from(AccountingPeriodModel)
        .where(AccountingPeriodModel.owner_id == owner_id)
    )
    if not configured_period_count:
        return

    period = session.execute(
        select(AccountingPeriodModel)
        .where(
            AccountingPeriodModel.owner_id == owner_id,
            AccountingPeriodModel.starts_on <= effective_date,
            AccountingPeriodModel.ends_on >= effective_date,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if period is None or period.status != "OPEN":
        raise AccountingPeriodUnavailable(
            "effective_date must fall inside an OPEN accounting period"
        )


def _lock_and_validate_accounts(
    session: Session,
    owner_id: int,
    currency_definition_id: UUID,
    account_ids: list[UUID],
    *,
    allow_closed: bool = False,
) -> dict[UUID, FinancialAccountModel]:
    ordered_ids = sorted(set(account_ids), key=str)
    accounts = session.scalars(
        select(FinancialAccountModel)
        .where(FinancialAccountModel.id.in_(ordered_ids))
        .order_by(FinancialAccountModel.id)
        .with_for_update()
    ).all()
    by_id = {account.id: account for account in accounts}
    if len(by_id) != len(ordered_ids):
        raise AccountNotFound("one or more financial accounts do not exist")
    for account in accounts:
        if account.owner_id != owner_id:
            raise AccountNotFound("one or more financial accounts are not owned by caller")
        if account.currency_definition_id != currency_definition_id:
            raise CurrencyMismatch("all accounts must use the journal currency definition")
        if account.status != "OPEN" and not allow_closed:
            raise AccountClosed("ordinary journals cannot post to closed accounts")
    return by_id


def _currency_definition(session: Session, definition_id: UUID) -> CurrencyDefinitionModel:
    definition = session.get(CurrencyDefinitionModel, definition_id)
    if (
        definition is None
        or definition.registry_list != "one"
        or definition.minor_unit_exponent is None
    ):
        raise InvalidJournal("journal currency must be a current ISO monetary unit")
    return definition


def _journal_response(
    journal: JournalEntryModel,
    currency: CurrencyDefinitionModel,
    postings: list[tuple[UUID, str, int]],
) -> dict:
    return {
        "journal_id": str(journal.id),
        "effective_date": journal.effective_date.isoformat(),
        "recorded_at": journal.recorded_at.isoformat(),
        "currency": {
            "code": currency.code,
            "registry_release": currency.registry_release,
            "minor_unit_exponent": currency.minor_unit_exponent,
        },
        "postings": [
            {
                "account_id": str(account_id),
                "side": side,
                "amount_minor": str(amount_minor),
            }
            for account_id, side, amount_minor in postings
        ],
    }


def post_journal_in_session(
    session: Session,
    command: PostJournalCommand,
    idempotency_key: str,
) -> PostingResult:
    """Post a journal inside a caller-owned transaction.

    The caller must have an active transaction and remains responsible for
    commit/rollback. This function never opens, commits, rolls back, closes,
    or retries the Session. It is the composition boundary for workflows
    (such as trade settlement) that must persist ledger and domain facts
    atomically in one database transaction.
    """
    if not session.in_transaction():
        raise RuntimeError("post_journal_in_session requires an active transaction")

    key = _validate_idempotency_key(idempotency_key)
    canonical_lines = sorted(
        command.postings,
        key=lambda line: (str(line.account_id), line.side, line.amount_minor),
    )
    request_hash = _hash_payload(
        {
            "owner_id": command.owner_id,
            "effective_date": command.effective_date.isoformat(),
            "description": command.description,
            "currency_definition_id": str(command.currency_definition_id),
            "postings": [
                {
                    "account_id": str(line.account_id),
                    "side": line.side,
                    "amount_minor": str(line.amount_minor),
                }
                for line in canonical_lines
            ],
        }
    )

    record, replay = _claim_idempotency(
        session, command.owner_id, CREATE_OPERATION, key, request_hash
    )
    if replay is not None:
        return replay

    assert record is not None
    currency = _currency_definition(session, command.currency_definition_id)
    _lock_and_validate_accounts(
        session,
        command.owner_id,
        command.currency_definition_id,
        [line.account_id for line in command.postings],
    )
    _check_period(session, command.owner_id, command.effective_date)

    journal = JournalEntryModel(
        id=uuid4(),
        owner_id=command.owner_id,
        effective_date=command.effective_date,
        description=command.description,
        currency_definition_id=command.currency_definition_id,
        status="POSTED",
        created_by=command.actor_id,
    )
    session.add(journal)
    session.flush()

    normalized_lines = [
        (line.account_id, line.side, line.amount_minor)
        for line in canonical_lines
    ]
    session.add_all(
        [
            JournalPostingModel(
                id=uuid4(),
                journal_entry_id=journal.id,
                owner_id=command.owner_id,
                account_id=account_id,
                currency_definition_id=command.currency_definition_id,
                side=side,
                amount_minor=Decimal(amount_minor),
            )
            for account_id, side, amount_minor in normalized_lines
        ]
    )
    session.flush()
    session.refresh(journal)
    body = _journal_response(journal, currency, normalized_lines)
    session.add(
        AuditEventModel(
            id=uuid4(),
            owner_id=command.owner_id,
            actor_id=command.actor_id,
            event_type="ledger.journal.posted",
            aggregate_type="journal_entry",
            aggregate_id=journal.id,
            payload={
                "currency_code": currency.code,
                "registry_release": currency.registry_release,
                "posting_count": len(normalized_lines),
                "effective_date": command.effective_date.isoformat(),
            },
            correlation_id=record.id,
        )
    )
    _complete_idempotency(record, journal, 201, body)
    session.flush()
    return PostingResult(status_code=201, body=body, replayed=False)


def _post_journal_once(
    session_factory: Callable[[], Session],
    command: PostJournalCommand,
    idempotency_key: str,
) -> PostingResult:
    """Standalone transaction-owning wrapper around the session-bound primitive."""
    with session_factory() as session:
        with session.begin():
            result = post_journal_in_session(session, command, idempotency_key)
    return result


def _reverse_journal_once(
    session_factory: Callable[[], Session],
    command: ReverseJournalCommand,
    idempotency_key: str,
) -> PostingResult:
    """Create one exact reversal, serialized on the original journal row."""
    key = _validate_idempotency_key(idempotency_key)
    request_hash = _hash_payload(
        {
            "owner_id": command.owner_id,
            "source_journal_id": str(command.source_journal_id),
            "effective_date": command.effective_date.isoformat(),
            "description": command.description,
        }
    )

    with session_factory() as session:
        with session.begin():
            record, replay = _claim_idempotency(
                session, command.owner_id, REVERSE_OPERATION, key, request_hash
            )
            if replay is not None:
                result = replay
            else:
                assert record is not None
                source = session.execute(
                    select(JournalEntryModel)
                    .where(
                        JournalEntryModel.id == command.source_journal_id,
                        JournalEntryModel.owner_id == command.owner_id,
                    )
                    .with_for_update()
                ).scalar_one_or_none()
                if source is None:
                    raise JournalNotFound("source journal not found for owner")
                if source.reversal_of is not None:
                    raise JournalAlreadyReversed("a reversal cannot itself be reversed")
                prior_reversal = session.execute(
                    select(JournalEntryModel.id).where(
                        JournalEntryModel.reversal_of == source.id
                    )
                ).scalar_one_or_none()
                if prior_reversal is not None:
                    raise JournalAlreadyReversed("source journal already has a reversal")

                source_lines = session.scalars(
                    select(JournalPostingModel)
                    .where(JournalPostingModel.journal_entry_id == source.id)
                    .order_by(JournalPostingModel.account_id)
                ).all()
                if len(source_lines) < 2:
                    raise InvalidJournal("source journal has no complete posting set")
                _lock_and_validate_accounts(
                    session,
                    command.owner_id,
                    source.currency_definition_id,
                    [line.account_id for line in source_lines],
                    allow_closed=True,
                )
                _check_period(session, command.owner_id, command.effective_date)
                currency = _currency_definition(session, source.currency_definition_id)

                reversal = JournalEntryModel(
                    id=uuid4(),
                    owner_id=command.owner_id,
                    effective_date=command.effective_date,
                    description=command.description,
                    currency_definition_id=source.currency_definition_id,
                    status="POSTED",
                    reversal_of=source.id,
                    created_by=command.actor_id,
                )
                session.add(reversal)
                session.flush()

                reversed_lines = [
                    (
                        line.account_id,
                        "CREDIT" if line.side == "DEBIT" else "DEBIT",
                        int(line.amount_minor),
                    )
                    for line in source_lines
                ]
                session.add_all(
                    [
                        JournalPostingModel(
                            id=uuid4(),
                            journal_entry_id=reversal.id,
                            owner_id=command.owner_id,
                            account_id=account_id,
                            currency_definition_id=source.currency_definition_id,
                            side=side,
                            amount_minor=Decimal(amount_minor),
                        )
                        for account_id, side, amount_minor in reversed_lines
                    ]
                )
                session.flush()
                session.refresh(reversal)
                body = _journal_response(reversal, currency, reversed_lines)
                body["reversal_of"] = str(source.id)
                session.add(
                    AuditEventModel(
                        id=uuid4(),
                        owner_id=command.owner_id,
                        actor_id=command.actor_id,
                        event_type="ledger.journal.reversed",
                        aggregate_type="journal_entry",
                        aggregate_id=reversal.id,
                        payload={
                            "reversal_of": str(source.id),
                            "currency_code": currency.code,
                            "posting_count": len(reversed_lines),
                        },
                        correlation_id=record.id,
                    )
                )
                _complete_idempotency(record, reversal, 201, body)
                session.flush()
                result = PostingResult(status_code=201, body=body, replayed=False)
    return result



def _is_retryable_database_error(error: DBAPIError) -> bool:
    """Retry only transaction-abort and connection-loss SQLSTATE classes."""
    original = error.orig
    sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    return (
        bool(error.connection_invalidated)
        or sqlstate in {"40001", "40P01", "57P01"}
        or (isinstance(sqlstate, str) and sqlstate.startswith("08"))
    )


def _run_with_transient_retry(operation: Callable[[], PostingResult]) -> PostingResult:
    """Bounded retry with the same idempotency key, including unknown commit outcomes."""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            return operation()
        except DBAPIError as exc:
            if not _is_retryable_database_error(exc) or attempt == max_attempts - 1:
                raise
            # The next attempt opens a fresh Session. Reusing the same key makes
            # a retry safe even if the previous connection failed during COMMIT.
            sleep(0.05 * (2**attempt))
    raise RuntimeError("unreachable retry loop exit")


def post_journal(
    session_factory: Callable[[], Session],
    command: PostJournalCommand,
    idempotency_key: str,
) -> PostingResult:
    return _run_with_transient_retry(
        lambda: _post_journal_once(session_factory, command, idempotency_key)
    )


def reverse_journal(
    session_factory: Callable[[], Session],
    command: ReverseJournalCommand,
    idempotency_key: str,
) -> PostingResult:
    return _run_with_transient_retry(
        lambda: _reverse_journal_once(session_factory, command, idempotency_key)
    )
