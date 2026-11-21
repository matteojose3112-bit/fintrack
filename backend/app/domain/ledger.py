"""Append-only, single-currency double-entry ledger primitives.

LedgerBook is a deterministic in-memory domain aggregate, not persistence. A
database adapter must preserve its invariants transactionally and concurrently.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.domain.accounts import AccountStatus, AccountType, FinancialAccount
from app.domain.money import Money


class EntrySide(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


@dataclass(frozen=True, slots=True)
class LedgerPosting:
    """One positive, single-currency debit or credit against an account."""

    account_id: str
    side: EntrySide
    amount: Money

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, str) or not self.account_id.strip():
            raise ValueError("posting account_id must be a non-empty string")
        if not isinstance(self.side, EntrySide):
            raise TypeError("posting side must be an EntrySide")
        if not isinstance(self.amount, Money):
            raise TypeError("posting amount must be Money")
        if self.amount.minor_units <= 0:
            raise ValueError("posting amount must be greater than zero")


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """Immutable balanced journal event; corrections are new reversing events."""

    entry_id: str
    owner_id: str
    effective_date: date
    description: str
    postings: tuple[LedgerPosting, ...]
    reversal_of: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("entry_id", "owner_id", "description"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.effective_date, date):
            raise TypeError("effective_date must be a date")
        postings = tuple(self.postings)
        if len(postings) < 2:
            raise ValueError("a journal entry requires at least two postings")
        if any(not isinstance(item, LedgerPosting) for item in postings):
            raise TypeError("all journal postings must be LedgerPosting values")
        account_ids = [item.account_id for item in postings]
        if len(set(account_ids)) != len(account_ids):
            raise ValueError("an account may appear only once in a journal entry")

        currencies = {item.amount.currency for item in postings}
        if len(currencies) != 1:
            raise ValueError("a journal entry must use one currency; FX requires explicit clearing entries")

        debit_total = sum(
            item.amount.minor_units for item in postings if item.side is EntrySide.DEBIT
        )
        credit_total = sum(
            item.amount.minor_units for item in postings if item.side is EntrySide.CREDIT
        )
        if debit_total != credit_total:
            raise ValueError("journal entry debits must equal credits")

        if self.reversal_of is not None:
            if not isinstance(self.reversal_of, str) or not self.reversal_of.strip():
                raise ValueError("reversal_of must be a non-empty entry id")

        object.__setattr__(self, "postings", postings)


class LedgerBook:
    """Append-only ledger aggregate with ownership and reversal enforcement."""

    def __init__(self) -> None:
        self._accounts: dict[str, FinancialAccount] = {}
        self._entries: list[JournalEntry] = []
        self._entry_ids: set[str] = set()
        self._reversed_entry_ids: set[str] = set()

    @property
    def entries(self) -> tuple[JournalEntry, ...]:
        return tuple(self._entries)

    @property
    def accounts(self) -> tuple[FinancialAccount, ...]:
        return tuple(self._accounts.values())

    def add_account(self, account: FinancialAccount) -> None:
        if not isinstance(account, FinancialAccount):
            raise TypeError("account must be a FinancialAccount")
        if account.account_id in self._accounts:
            raise ValueError("account_id already exists")
        self._accounts[account.account_id] = account

    def _validate_entry_accounts(self, entry: JournalEntry) -> None:
        for posting in entry.postings:
            account = self._accounts.get(posting.account_id)
            if account is None:
                raise ValueError(f"unknown account: {posting.account_id}")
            if account.owner_id != entry.owner_id:
                raise ValueError("all journal accounts must belong to the entry owner")
            if account.status is not AccountStatus.OPEN:
                raise ValueError("closed accounts cannot receive postings")
            if account.currency != posting.amount.currency:
                raise ValueError("posting currency must match its account currency")

    def post(self, entry: JournalEntry) -> None:
        """Append a new balanced entry; existing entries cannot be edited/deleted."""
        if not isinstance(entry, JournalEntry):
            raise TypeError("entry must be a JournalEntry")
        if entry.reversal_of is not None:
            raise ValueError("use reverse() to create a reversal")
        if entry.entry_id in self._entry_ids:
            raise ValueError("entry_id already exists")
        self._validate_entry_accounts(entry)
        self._entries.append(entry)
        self._entry_ids.add(entry.entry_id)

    def reverse(
        self,
        entry_id: str,
        reversal_id: str,
        effective_date: date,
        description: str | None = None,
    ) -> JournalEntry:
        """Append an exact debit/credit inversion of one original journal entry."""
        original = next((item for item in self._entries if item.entry_id == entry_id), None)
        if original is None:
            raise ValueError("original journal entry not found")
        if original.reversal_of is not None:
            raise ValueError("a reversal cannot itself be reversed")
        if entry_id in self._reversed_entry_ids:
            raise ValueError("journal entry has already been reversed")
        if reversal_id in self._entry_ids:
            raise ValueError("entry_id already exists")

        opposite = {EntrySide.DEBIT: EntrySide.CREDIT, EntrySide.CREDIT: EntrySide.DEBIT}
        reversal = JournalEntry(
            entry_id=reversal_id,
            owner_id=original.owner_id,
            effective_date=effective_date,
            description=description or f"Reversal of {entry_id}",
            postings=tuple(
                LedgerPosting(item.account_id, opposite[item.side], item.amount)
                for item in original.postings
            ),
            reversal_of=entry_id,
        )
        self._validate_entry_accounts(reversal)
        self._entries.append(reversal)
        self._entry_ids.add(reversal_id)
        self._reversed_entry_ids.add(entry_id)
        return reversal

    def transfer(
        self,
        transfer_id: str,
        owner_id: str,
        source_account_id: str,
        destination_account_id: str,
        amount: Money,
        effective_date: date,
        description: str = "Account transfer",
    ) -> JournalEntry:
        """Move value between two owned asset accounts in the same currency."""
        source = self._accounts.get(source_account_id)
        destination = self._accounts.get(destination_account_id)
        if source is None or destination is None:
            raise ValueError("both transfer accounts must exist")
        if source.account_id == destination.account_id:
            raise ValueError("source and destination accounts must differ")
        if source.owner_id != owner_id or destination.owner_id != owner_id:
            raise ValueError("transfer accounts must belong to the entry owner")
        if source.account_type is not AccountType.ASSET or destination.account_type is not AccountType.ASSET:
            raise ValueError("transfers require two asset accounts")
        if source.currency != destination.currency or amount.currency != source.currency:
            raise ValueError("transfer accounts and amount must use the same currency")

        entry = JournalEntry(
            entry_id=transfer_id,
            owner_id=owner_id,
            effective_date=effective_date,
            description=description,
            postings=(
                LedgerPosting(destination_account_id, EntrySide.DEBIT, amount),
                LedgerPosting(source_account_id, EntrySide.CREDIT, amount),
            ),
        )
        self.post(entry)
        return entry

    def balance_for(self, account_id: str) -> Money:
        """Derive a signed balance from immutable postings and normal account side."""
        account = self._accounts.get(account_id)
        if account is None:
            raise ValueError(f"unknown account: {account_id}")

        debit_total = 0
        credit_total = 0
        for entry in self._entries:
            for posting in entry.postings:
                if posting.account_id != account_id:
                    continue
                if posting.side is EntrySide.DEBIT:
                    debit_total += posting.amount.minor_units
                else:
                    credit_total += posting.amount.minor_units

        signed = debit_total - credit_total
        if account.normal_side == EntrySide.CREDIT.value:
            signed = -signed
        return Money.from_minor_units(signed, account.currency)
