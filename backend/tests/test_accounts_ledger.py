from datetime import date

import pytest

from app.domain.accounts import AccountStatus, AccountType, FinancialAccount
from app.domain.ledger import EntrySide, JournalEntry, LedgerBook, LedgerPosting
from app.domain.money import Money


DAY = date(2026, 11, 17)


def account(account_id, kind=AccountType.ASSET, owner="user-1", currency="USD", status=AccountStatus.OPEN):
    return FinancialAccount(account_id, owner, account_id.title(), kind, currency, status)


def money(amount, currency="USD"):
    return Money.from_decimal_string(amount, currency)


def journal(entry_id, *postings, owner="user-1"):
    return JournalEntry(entry_id, owner, DAY, entry_id, tuple(postings))


def test_account_normal_balance_rules_and_currency_normalization():
    assert account("cash", currency="usd").currency == "USD"
    assert account("cash").normal_side == "debit"
    assert account("expense", AccountType.EXPENSE).normal_side == "debit"
    assert account("debt", AccountType.LIABILITY).normal_side == "credit"
    assert account("equity", AccountType.EQUITY).normal_side == "credit"
    assert account("income", AccountType.INCOME).normal_side == "credit"


def test_account_identity_and_classification_are_immutable():
    item = account("cash")
    with pytest.raises((AttributeError, TypeError)):
        item.name = "Changed"


def test_journal_must_balance_and_use_at_least_two_postings():
    with pytest.raises(ValueError, match="debits must equal credits"):
        journal("unbalanced",
            LedgerPosting("cash", EntrySide.DEBIT, money("10.00")),
            LedgerPosting("equity", EntrySide.CREDIT, money("9.00")))
    with pytest.raises(ValueError, match="at least two"):
        journal("single", LedgerPosting("cash", EntrySide.DEBIT, money("1.00")))


def test_journal_rejects_zero_and_duplicate_account_postings():
    with pytest.raises(ValueError, match="greater than zero"):
        LedgerPosting("cash", EntrySide.DEBIT, money("0.00"))
    with pytest.raises(ValueError, match="only once"):
        journal("duplicate",
            LedgerPosting("cash", EntrySide.DEBIT, money("5.00")),
            LedgerPosting("cash", EntrySide.CREDIT, money("5.00")))


def test_journal_rejects_mixed_currency_without_explicit_fx_clearing():
    with pytest.raises(ValueError, match="one currency"):
        journal("mixed",
            LedgerPosting("cash-usd", EntrySide.DEBIT, money("10.00", "USD")),
            LedgerPosting("cash-cad", EntrySide.CREDIT, money("10.00", "CAD")))


def test_income_and_expense_golden_case():
    ledger = LedgerBook()
    ledger.add_account(account("cash"))
    ledger.add_account(account("salary", AccountType.INCOME))
    ledger.add_account(account("food", AccountType.EXPENSE))
    ledger.post(journal("salary-payment",
        LedgerPosting("cash", EntrySide.DEBIT, money("2000.00")),
        LedgerPosting("salary", EntrySide.CREDIT, money("2000.00"))))
    ledger.post(journal("groceries",
        LedgerPosting("food", EntrySide.DEBIT, money("125.50")),
        LedgerPosting("cash", EntrySide.CREDIT, money("125.50"))))
    assert ledger.balance_for("cash").to_decimal_string() == "1874.50"
    assert ledger.balance_for("salary").to_decimal_string() == "2000.00"
    assert ledger.balance_for("food").to_decimal_string() == "125.50"


def test_transfer_is_balanced_and_has_no_income_or_expense_effect():
    ledger = LedgerBook()
    ledger.add_account(account("checking"))
    ledger.add_account(account("savings"))
    ledger.add_account(account("opening-equity", AccountType.EQUITY))
    ledger.post(journal("opening",
        LedgerPosting("checking", EntrySide.DEBIT, money("1000.00")),
        LedgerPosting("opening-equity", EntrySide.CREDIT, money("1000.00"))))
    transfer = ledger.transfer("move-to-savings", "user-1", "checking", "savings", money("300.00"), DAY)
    assert transfer.postings[0].side is EntrySide.DEBIT
    assert transfer.postings[1].side is EntrySide.CREDIT
    assert ledger.balance_for("checking").to_decimal_string() == "700.00"
    assert ledger.balance_for("savings").to_decimal_string() == "300.00"
    assert ledger.balance_for("opening-equity").to_decimal_string() == "1000.00"


def test_reversal_is_a_new_immutable_exact_opposite_entry():
    ledger = LedgerBook()
    ledger.add_account(account("cash"))
    ledger.add_account(account("income", AccountType.INCOME))
    original = journal("deposit",
        LedgerPosting("cash", EntrySide.DEBIT, money("75.25")),
        LedgerPosting("income", EntrySide.CREDIT, money("75.25")))
    ledger.post(original)
    reversal = ledger.reverse("deposit", "deposit-reversal", DAY)
    assert reversal.reversal_of == "deposit"
    assert reversal.postings[0].side is EntrySide.CREDIT
    assert reversal.postings[1].side is EntrySide.DEBIT
    assert ledger.balance_for("cash").to_decimal_string() == "0.00"
    assert ledger.balance_for("income").to_decimal_string() == "0.00"
    assert ledger.entries[0] is original
    assert len(ledger.entries) == 2


def test_entry_cannot_be_reversed_twice_or_reverse_a_reversal():
    ledger = LedgerBook()
    ledger.add_account(account("cash"))
    ledger.add_account(account("equity", AccountType.EQUITY))
    ledger.post(journal("opening",
        LedgerPosting("cash", EntrySide.DEBIT, money("10.00")),
        LedgerPosting("equity", EntrySide.CREDIT, money("10.00"))))
    ledger.reverse("opening", "opening-reversal", DAY)
    with pytest.raises(ValueError, match="already been reversed"):
        ledger.reverse("opening", "second-reversal", DAY)
    with pytest.raises(ValueError, match="cannot itself be reversed"):
        ledger.reverse("opening-reversal", "reverse-reversal", DAY)


def test_posting_enforces_owner_currency_and_open_account():
    ledger = LedgerBook()
    ledger.add_account(account("cash"))
    ledger.add_account(account("foreign", owner="user-2"))
    ledger.add_account(account("cad", currency="CAD"))
    ledger.add_account(account("closed", status=AccountStatus.CLOSED))
    with pytest.raises(ValueError, match="belong to the entry owner"):
        ledger.post(journal("cross-owner",
            LedgerPosting("cash", EntrySide.DEBIT, money("1.00")),
            LedgerPosting("foreign", EntrySide.CREDIT, money("1.00"))))
    with pytest.raises(ValueError, match="match its account"):
        ledger.post(journal("wrong-currency",
            LedgerPosting("cash", EntrySide.DEBIT, money("1.00")),
            LedgerPosting("cad", EntrySide.CREDIT, money("1.00"))))
    with pytest.raises(ValueError, match="closed accounts"):
        ledger.post(journal("closed-account",
            LedgerPosting("cash", EntrySide.DEBIT, money("1.00")),
            LedgerPosting("closed", EntrySide.CREDIT, money("1.00"))))


def test_transfer_requires_owned_same_currency_asset_accounts():
    ledger = LedgerBook()
    ledger.add_account(account("checking"))
    ledger.add_account(account("other-user", owner="user-2"))
    ledger.add_account(account("cad", currency="CAD"))
    ledger.add_account(account("liability", AccountType.LIABILITY))
    with pytest.raises(ValueError, match="belong to the entry owner"):
        ledger.transfer("bad-owner", "user-1", "checking", "other-user", money("1.00"), DAY)
    with pytest.raises(ValueError, match="same currency"):
        ledger.transfer("bad-currency", "user-1", "checking", "cad", money("1.00"), DAY)
    with pytest.raises(ValueError, match="two asset accounts"):
        ledger.transfer("bad-type", "user-1", "checking", "liability", money("1.00"), DAY)


def test_duplicate_entry_ids_and_unknown_accounts_are_rejected():
    ledger = LedgerBook()
    ledger.add_account(account("cash"))
    ledger.add_account(account("equity", AccountType.EQUITY))
    entry = journal("opening",
        LedgerPosting("cash", EntrySide.DEBIT, money("1.00")),
        LedgerPosting("equity", EntrySide.CREDIT, money("1.00")))
    ledger.post(entry)
    with pytest.raises(ValueError, match="already exists"):
        ledger.post(entry)
    with pytest.raises(ValueError, match="unknown account"):
        ledger.post(journal("unknown",
            LedgerPosting("cash", EntrySide.DEBIT, money("1.00")),
            LedgerPosting("missing", EntrySide.CREDIT, money("1.00"))))
