"""Deterministic, explainable reconciliation match proposals.

This module proposes matches only. It never confirms them, changes ledger
postings, or uses fuzzy text/LLM inference.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import unicodedata
from uuid import UUID


class MatchStatus(str, Enum):
    PROPOSED = "PROPOSED"
    AMBIGUOUS = "AMBIGUOUS"
    UNMATCHED = "UNMATCHED"


class MatchStrategy(str, Enum):
    SOURCE_TRANSACTION_ID = "SOURCE_TRANSACTION_ID"
    EXACT_REFERENCE = "EXACT_REFERENCE"
    EXACT_AMOUNT_DATE_WINDOW = "EXACT_AMOUNT_DATE_WINDOW"


@dataclass(frozen=True, slots=True)
class LedgerMatchCandidate:
    candidate_id: UUID
    journal_id: UUID
    owner_id: int
    account_id: UUID
    effective_date: date
    amount_minor: int
    currency_code: str
    source_transaction_id: str | None = None
    reference: str | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class MatchProposal:
    row_number: int
    candidate_id: UUID
    journal_id: UUID
    strategy: MatchStrategy
    date_difference_days: int


@dataclass(frozen=True, slots=True)
class MatchDecision:
    row_number: int
    status: MatchStatus
    proposal: MatchProposal | None = None
    candidate_ids: tuple[UUID, ...] = ()


def _normalize_reference(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(unicodedata.normalize("NFKC", value).casefold().split())
    return normalized or None


def _validate_minor_units(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be integer minor units")


def build_match_proposals(
    statement_rows,
    ledger_candidates,
    *,
    owner_id: int,
    account_id: UUID,
    currency_code: str,
    date_window_days: int = 3,
) -> tuple[MatchDecision, ...]:
    """Build one-to-one proposals using strict references, then exact amounts.

    Rows with a supplied stable source transaction ID are never downgraded to
    weaker matching if that ID cannot be matched exactly. Amount/date fallback
    is allowed only when both sides resolve uniquely and no references conflict.
    """
    from app.domain.reconciliation_csv import StatementRow

    if isinstance(owner_id, bool) or not isinstance(owner_id, int) or owner_id <= 0:
        raise ValueError("owner_id must be a positive integer")
    if not isinstance(account_id, UUID):
        raise TypeError("account_id must be UUID")
    if not isinstance(currency_code, str) or len(currency_code) != 3:
        raise ValueError("currency_code must be a three-letter code")
    if isinstance(date_window_days, bool) or not isinstance(date_window_days, int) or not 0 <= date_window_days <= 31:
        raise ValueError("date_window_days must be between 0 and 31")

    rows = tuple(statement_rows)
    candidates = tuple(ledger_candidates)
    if any(not isinstance(row, StatementRow) for row in rows):
        raise TypeError("statement_rows must contain StatementRow values")
    if any(not isinstance(item, LedgerMatchCandidate) for item in candidates):
        raise TypeError("ledger_candidates must contain LedgerMatchCandidate values")

    row_numbers = [row.row_number for row in rows]
    candidate_ids = [item.candidate_id for item in candidates]
    if len(row_numbers) != len(set(row_numbers)):
        raise ValueError("statement row numbers must be unique")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("ledger candidate IDs must be unique")

    normalized_currency = currency_code.upper()
    for row in rows:
        _validate_minor_units(row.amount_minor_units, "statement amount")
        if row.currency != normalized_currency:
            raise ValueError("all statement rows must use the requested account currency")
    for item in candidates:
        _validate_minor_units(item.amount_minor, "ledger candidate amount")
        if item.owner_id <= 0:
            raise ValueError("ledger candidate owner_id must be positive")

    eligible = tuple(
        item for item in candidates
        if item.owner_id == owner_id
        and item.account_id == account_id
        and item.currency_code == normalized_currency
    )
    decisions: dict[int, MatchDecision] = {}
    remaining_rows = {row.row_number: row for row in rows}
    remaining_candidates = {item.candidate_id: item for item in eligible}
    blocked_rows = {
        row.row_number for row in rows if row.source_transaction_id
    }

    def resolve_pass(strategy: MatchStrategy, matcher, row_subset=None):
        active = row_subset if row_subset is not None else set(remaining_rows)
        edges: dict[int, tuple[LedgerMatchCandidate, ...]] = {}
        reverse: dict[UUID, list[int]] = {}
        for number in active:
            row = remaining_rows[number]
            matches = tuple(
                candidate for candidate in remaining_candidates.values()
                if matcher(row, candidate)
            )
            if matches:
                edges[number] = matches
                for candidate in matches:
                    reverse.setdefault(candidate.candidate_id, []).append(number)

        consumed_candidates: set[UUID] = set()
        consumed_rows: set[int] = set()
        for number, matches in edges.items():
            consumed_rows.add(number)
            ids = tuple(sorted((item.candidate_id for item in matches), key=str))
            if len(matches) == 1 and len(reverse[matches[0].candidate_id]) == 1:
                candidate = matches[0]
                decisions[number] = MatchDecision(
                    row_number=number,
                    status=MatchStatus.PROPOSED,
                    proposal=MatchProposal(
                        row_number=number,
                        candidate_id=candidate.candidate_id,
                        journal_id=candidate.journal_id,
                        strategy=strategy,
                        date_difference_days=abs(
                            (remaining_rows[number].booking_date - candidate.effective_date).days
                        ),
                    ),
                    candidate_ids=ids,
                )
            else:
                decisions[number] = MatchDecision(
                    row_number=number,
                    status=MatchStatus.AMBIGUOUS,
                    candidate_ids=ids,
                )
            consumed_candidates.update(ids)

        for number in consumed_rows:
            remaining_rows.pop(number, None)
        for candidate_id in consumed_candidates:
            remaining_candidates.pop(candidate_id, None)

    resolve_pass(
        MatchStrategy.SOURCE_TRANSACTION_ID,
        lambda row, candidate: bool(row.source_transaction_id)
        and candidate.source_transaction_id == row.source_transaction_id
        and candidate.amount_minor == row.amount_minor_units,
    )

    resolve_pass(
        MatchStrategy.EXACT_REFERENCE,
        lambda row, candidate: bool(_normalize_reference(row.reference))
        and _normalize_reference(candidate.reference) == _normalize_reference(row.reference)
        and candidate.amount_minor == row.amount_minor_units
        and candidate.effective_date == row.booking_date,
    )

    resolve_pass(
        MatchStrategy.EXACT_AMOUNT_DATE_WINDOW,
        lambda row, candidate: (
            candidate.amount_minor == row.amount_minor_units
            and abs((row.booking_date - candidate.effective_date).days) <= date_window_days
            and not (
                _normalize_reference(row.reference)
                and _normalize_reference(candidate.reference)
                and _normalize_reference(row.reference) != _normalize_reference(candidate.reference)
            )
        ),
        row_subset=set(remaining_rows) - blocked_rows,
    )

    for number in remaining_rows:
        decisions[number] = MatchDecision(number, MatchStatus.UNMATCHED)

    return tuple(decisions[row.row_number] for row in rows)
