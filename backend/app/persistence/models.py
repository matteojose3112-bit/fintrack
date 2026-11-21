"""SQLAlchemy persistence models for Aurelius's durable financial core."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CurrencyDefinitionModel(Base):
    __tablename__ = "currency_definitions"
    __table_args__ = (
        UniqueConstraint(
            "code",
            "registry_release",
            "registry_list",
            "withdrawal_key",
            name="uq_currency_definition_release_record",
        ),
        CheckConstraint(
            "minor_unit_exponent IS NULL OR minor_unit_exponent >= 0",
            name="ck_currency_minor_unit_exponent_nonnegative",
        ),
        CheckConstraint(
            "registry_list IN ('one', 'three')",
            name="ck_currency_registry_list",
        ),
        Index("ix_currency_definitions_code", "code"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(3), nullable=False)
    numeric_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    minor_unit_exponent: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    registry_list: Mapped[str] = mapped_column(String(8), nullable=False)
    registry_release: Mapped[str] = mapped_column(String(80), nullable=False)
    published_on: Mapped[object] = mapped_column(Date, nullable=False)
    fund: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    withdrawal_key: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    withdrawn_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    countries: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FinancialAccountModel(Base):
    __tablename__ = "financial_accounts"
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE')",
            name="ck_financial_accounts_type",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'CLOSED')", name="ck_financial_accounts_status"
        ),
        UniqueConstraint(
            "id",
            "owner_id",
            "currency_definition_id",
            name="uq_financial_accounts_owner_currency",
        ),
        UniqueConstraint("id", "owner_id", name="uq_financial_accounts_id_owner"),
        Index("ix_financial_accounts_owner_status", "owner_id", "status"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    account_type: Mapped[str] = mapped_column(String(16), nullable=False)
    currency_definition_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="OPEN")
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    closed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JournalEntryModel(Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint("status = 'POSTED'", name="ck_journal_entries_posted_only"),
        UniqueConstraint("id", "owner_id", name="uq_journal_entries_id_owner"),
        UniqueConstraint("reversal_of", name="uq_journal_entries_reversal_source"),
        UniqueConstraint(
            "id",
            "owner_id",
            "currency_definition_id",
            name="uq_journal_entries_owner_currency",
        ),
        ForeignKeyConstraint(
            ["reversal_of", "owner_id"],
            ["journal_entries.id", "journal_entries.owner_id"],
            ondelete="RESTRICT",
            name="fk_journal_entries_reversal_owner",
        ),
        ForeignKeyConstraint(
            ["correction_of", "owner_id"],
            ["journal_entries.id", "journal_entries.owner_id"],
            ondelete="RESTRICT",
            name="fk_journal_entries_correction_owner",
        ),
        Index("ix_journal_entries_owner_effective_date", "owner_id", "effective_date"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    effective_date: Mapped[object] = mapped_column(Date, nullable=False)
    recorded_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    currency_definition_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="POSTED")
    reversal_of: Mapped[object | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    correction_of: Mapped[object | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class JournalPostingModel(Base):
    __tablename__ = "journal_postings"
    __table_args__ = (
        CheckConstraint("side IN ('DEBIT', 'CREDIT')", name="ck_journal_postings_side"),
        CheckConstraint(
            "amount_minor > 0",
            name="ck_journal_postings_positive_minor_units",
        ),
        ForeignKeyConstraint(
            ["journal_entry_id", "owner_id", "currency_definition_id"],
            [
                "journal_entries.id",
                "journal_entries.owner_id",
                "journal_entries.currency_definition_id",
            ],
            ondelete="RESTRICT",
            name="fk_journal_postings_journal_owner_currency",
        ),
        ForeignKeyConstraint(
            ["account_id", "owner_id", "currency_definition_id"],
            [
                "financial_accounts.id",
                "financial_accounts.owner_id",
                "financial_accounts.currency_definition_id",
            ],
            ondelete="RESTRICT",
            name="fk_journal_postings_account_owner_currency",
        ),
        Index("ix_journal_postings_journal", "journal_entry_id"),
        Index("ix_journal_postings_account_journal", "account_id", "journal_entry_id"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    journal_entry_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    currency_definition_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    amount_minor: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IdempotencyRecordModel(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "operation",
            "idempotency_key",
            name="uq_idempotency_owner_operation_key",
        ),
        ForeignKeyConstraint(
            ["journal_entry_id", "owner_id"],
            ["journal_entries.id", "journal_entries.owner_id"],
            ondelete="RESTRICT",
            name="fk_idempotency_journal_owner",
        ),
        Index("ix_idempotency_owner_created", "owner_id", "created_at"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    journal_entry_id: Mapped[object | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    response_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    response_body: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEventModel(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_owner_occurred", "owner_id", "occurred_at"),
        Index("ix_audit_events_aggregate", "aggregate_type", "aggregate_id"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    actor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    occurred_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payload: Mapped[dict | list] = mapped_column(JSON, nullable=False)
    correlation_id: Mapped[object | None] = mapped_column(Uuid(as_uuid=True), nullable=True)


class AccountingPeriodModel(Base):
    __tablename__ = "accounting_periods"
    __table_args__ = (
        CheckConstraint("ends_on >= starts_on", name="ck_accounting_periods_valid_range"),
        CheckConstraint(
            "status IN ('OPEN', 'CLOSED')", name="ck_accounting_periods_status"
        ),
        Index("ix_accounting_periods_owner_dates", "owner_id", "starts_on", "ends_on"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    starts_on: Mapped[object] = mapped_column(Date, nullable=False)
    ends_on: Mapped[object] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="OPEN")
    closed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FinancialOwnerPreferenceModel(Base):
    __tablename__ = "financial_owner_preferences"

    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    base_currency_definition_id: Mapped[object | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    accounting_timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="UTC"
    )
    locale: Mapped[str] = mapped_column(String(32), nullable=False, default="en-US")
    reporting_calendar: Mapped[str] = mapped_column(
        String(24), nullable=False, default="GREGORIAN"
    )
