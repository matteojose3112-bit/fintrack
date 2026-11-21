from datetime import date, datetime
from uuid import uuid4

import pytest

from app.persistence.posting_service import (
    InvalidJournal,
    PostJournalCommand,
    PostingLine,
)


def valid_command():
    return PostJournalCommand(
        owner_id=1,
        actor_id=1,
        effective_date=date(2026, 11, 17),
        description="test journal",
        currency_definition_id=uuid4(),
        postings=(
            PostingLine(uuid4(), "DEBIT", 100),
            PostingLine(uuid4(), "CREDIT", 100),
        ),
    )


def test_posting_line_normalizes_side_and_accepts_integer_minor_units():
    line = PostingLine(uuid4(), "debit", 100)
    assert line.side == "DEBIT"
    assert line.amount_minor == 100


@pytest.mark.parametrize("amount", [True, 1.0, "100", 0, -1, 10**38])
def test_posting_line_rejects_non_integer_or_out_of_range_minor_units(amount):
    with pytest.raises((TypeError, ValueError)):
        PostingLine(uuid4(), "DEBIT", amount)


def test_posting_command_rejects_unbalanced_lines():
    currency_id = uuid4()
    with pytest.raises(InvalidJournal, match="debits must equal credits"):
        PostJournalCommand(
            owner_id=1,
            actor_id=1,
            effective_date=date(2026, 11, 17),
            description="unbalanced",
            currency_definition_id=currency_id,
            postings=(
                PostingLine(uuid4(), "DEBIT", 100),
                PostingLine(uuid4(), "CREDIT", 99),
            ),
        )


def test_posting_command_rejects_duplicate_account_lines():
    currency_id = uuid4()
    account_id = uuid4()
    with pytest.raises(InvalidJournal, match="only once"):
        PostJournalCommand(
            owner_id=1,
            actor_id=1,
            effective_date=date(2026, 11, 17),
            description="duplicate account",
            currency_definition_id=currency_id,
            postings=(
                PostingLine(account_id, "DEBIT", 100),
                PostingLine(account_id, "CREDIT", 100),
            ),
        )


def test_posting_command_rejects_datetime_as_effective_date():
    command = valid_command()
    with pytest.raises(TypeError, match="calendar date"):
        PostJournalCommand(
            owner_id=command.owner_id,
            actor_id=command.actor_id,
            effective_date=datetime(2026, 11, 17, 12, 0),
            description=command.description,
            currency_definition_id=command.currency_definition_id,
            postings=command.postings,
        )


def test_posting_command_rejects_boolean_owner_id():
    command = valid_command()
    with pytest.raises(ValueError, match="owner_id"):
        PostJournalCommand(
            owner_id=True,
            actor_id=command.actor_id,
            effective_date=command.effective_date,
            description=command.description,
            currency_definition_id=command.currency_definition_id,
            postings=command.postings,
        )


class FakePostgresError(Exception):
    def __init__(self, sqlstate):
        super().__init__(sqlstate)
        self.sqlstate = sqlstate


def test_transient_postgres_sqlstates_are_retryable():
    from sqlalchemy.exc import DBAPIError
    from app.persistence.posting_service import _is_retryable_database_error

    assert _is_retryable_database_error(DBAPIError("stmt", {}, FakePostgresError("40001")))
    assert _is_retryable_database_error(DBAPIError("stmt", {}, FakePostgresError("40P01")))
    assert _is_retryable_database_error(DBAPIError("stmt", {}, FakePostgresError("08006")))
    assert not _is_retryable_database_error(DBAPIError("stmt", {}, FakePostgresError("23514")))


def test_retry_wrapper_retries_with_bounded_attempts(monkeypatch):
    from app.persistence import posting_service

    monkeypatch.setattr(posting_service, "sleep", lambda _: None)
    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        if attempts["count"] < 3:
            from sqlalchemy.exc import DBAPIError
            raise DBAPIError("stmt", {}, FakePostgresError("40001"))
        return "committed-or-replayed"

    result = posting_service._run_with_transient_retry(operation)
    assert result == "committed-or-replayed"
    assert attempts["count"] == 3


def test_retry_wrapper_does_not_retry_integrity_errors(monkeypatch):
    from sqlalchemy.exc import DBAPIError
    from app.persistence import posting_service

    monkeypatch.setattr(posting_service, "sleep", lambda _: None)
    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        raise DBAPIError("stmt", {}, FakePostgresError("23514"))

    with pytest.raises(DBAPIError):
        posting_service._run_with_transient_retry(operation)
    assert attempts["count"] == 1



def test_public_posting_retry_reuses_the_exact_idempotency_key(monkeypatch):
    from sqlalchemy.exc import DBAPIError
    from app.persistence import posting_service
    from app.persistence.posting_service import PostingResult

    monkeypatch.setattr(posting_service, "sleep", lambda _: None)
    command = valid_command()
    keys = []

    def fail_once_then_return(session_factory, received_command, key):
        keys.append(key)
        if len(keys) == 1:
            raise DBAPIError(
                "COMMIT",
                {},
                FakePostgresError("08006"),
                connection_invalidated=True,
            )
        return PostingResult(201, {"journal_id": "stable-result"})

    monkeypatch.setattr(posting_service, "_post_journal_once", fail_once_then_return)
    result = posting_service.post_journal(None, command, "same-key-after-unknown-commit")
    assert result.body["journal_id"] == "stable-result"
    assert keys == ["same-key-after-unknown-commit", "same-key-after-unknown-commit"]
