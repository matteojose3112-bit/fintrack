from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.domain.reconciliation_csv import StatementRow
from app.domain.reconciliation_matching import (
    LedgerMatchCandidate,
    MatchStatus,
    MatchStrategy,
    build_match_proposals,
)


OWNER = 7
ACCOUNT = uuid4()
DAY = date(2026, 11, 21)


def row(number=2, amount=1000, *, source_id=None, reference=None, day=DAY, currency="USD"):
    return StatementRow(
        row_number=number,
        booking_date=day,
        amount_minor_units=amount,
        currency=currency,
        description="statement text",
        source_transaction_id=source_id,
        reference=reference,
    )


def candidate(
    amount=1000, *, owner=OWNER, account=ACCOUNT, currency="USD",
    source_id=None, reference=None, day=DAY, candidate_id=None,
):
    return LedgerMatchCandidate(
        candidate_id=candidate_id or uuid4(),
        journal_id=uuid4(),
        owner_id=owner,
        account_id=account,
        effective_date=day,
        amount_minor=amount,
        currency_code=currency,
        source_transaction_id=source_id,
        reference=reference,
        description="ledger text",
    )


def propose(rows, candidates, *, window=3):
    return build_match_proposals(
        rows, candidates, owner_id=OWNER, account_id=ACCOUNT,
        currency_code="USD", date_window_days=window,
    )


def test_exact_source_transaction_id_is_first_priority_and_requires_exact_amount():
    ledger = candidate(amount=1000, source_id="bank-77", day=DAY - timedelta(days=20))
    decision = propose([row(source_id="bank-77")], [ledger])[0]
    assert decision.status is MatchStatus.PROPOSED
    assert decision.proposal.strategy is MatchStrategy.SOURCE_TRANSACTION_ID

    mismatch = propose([row(source_id="bank-77", amount=999)], [ledger])[0]
    assert mismatch.status is MatchStatus.UNMATCHED


def test_exact_reference_matches_only_exact_amount_and_date():
    ledger = candidate(reference=" INV  204 ", day=DAY)
    decision = propose([row(reference="inv 204")], [ledger])[0]
    assert decision.status is MatchStatus.PROPOSED
    assert decision.proposal.strategy is MatchStrategy.EXACT_REFERENCE

    wrong_day = propose([row(reference="inv 204", day=DAY + timedelta(days=10))], [ledger])[0]
    assert wrong_day.status is MatchStatus.UNMATCHED


def test_amount_date_fallback_requires_one_unique_candidate():
    ledger = candidate(amount=-12345)
    decision = propose([row(amount=-12345)], [ledger])[0]
    assert decision.status is MatchStatus.PROPOSED
    assert decision.proposal.strategy is MatchStrategy.EXACT_AMOUNT_DATE_WINDOW


def test_multiple_candidates_for_same_amount_are_ambiguous():
    first, second = candidate(), candidate()
    decision = propose([row()], [first, second])[0]
    assert decision.status is MatchStatus.AMBIGUOUS
    assert decision.proposal is None
    assert set(decision.candidate_ids) == {first.candidate_id, second.candidate_id}


def test_one_candidate_cannot_be_assigned_to_two_statement_rows():
    ledger = candidate()
    decisions = propose([row(2), row(3)], [ledger])
    assert [item.status for item in decisions] == [MatchStatus.AMBIGUOUS, MatchStatus.AMBIGUOUS]


def test_conflicting_references_prevent_amount_date_fallback():
    ledger = candidate(reference="other-ref")
    decision = propose([row(reference="statement-ref")], [ledger])[0]
    assert decision.status is MatchStatus.UNMATCHED


def test_stable_source_id_prevents_weaker_reference_or_amount_fallback():
    ledger = candidate(source_id="bank-id", reference="ref-1")
    decision = propose([row(source_id="different-id", reference="ref-1")], [ledger])[0]
    assert decision.status is MatchStatus.UNMATCHED


def test_owner_account_and_currency_are_hard_candidate_boundaries():
    candidates = [
        candidate(owner=OWNER + 1),
        candidate(account=uuid4()),
        candidate(currency="EUR"),
    ]
    decision = propose([row()], candidates)[0]
    assert decision.status is MatchStatus.UNMATCHED


def test_date_window_is_bounded_and_exact_minor_units_are_required():
    near = candidate(day=DAY - timedelta(days=2))
    far = candidate(day=DAY - timedelta(days=4))
    decisions = propose([row()], [near, far], window=2)
    assert decisions[0].status is MatchStatus.PROPOSED
    assert decisions[0].proposal.candidate_id == near.candidate_id


def test_statement_currency_mismatch_and_duplicate_identity_are_rejected():
    with pytest.raises(ValueError, match="account currency"):
        propose([row(currency="EUR")], [])
    repeated = candidate()
    with pytest.raises(ValueError, match="candidate IDs"):
        propose([row()], [repeated, repeated])
    with pytest.raises(ValueError, match="row numbers"):
        propose([row(2), row(2)], [])
