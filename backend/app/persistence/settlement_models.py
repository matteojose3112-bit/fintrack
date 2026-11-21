"""Owner-scoped ledger account mapping for portfolio trade settlement."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PortfolioLedgerAccountMappingModel(Base):
    """Explicit ledger roles for one portfolio, brokerage cash account, and currency.

    Every referenced financial account is constrained to the same owner and
    immutable currency-definition snapshot. PostgreSQL migration triggers
    additionally enforce the required account types and OPEN status at mapping
    creation/update time. Settlement must re-check status when it is used.
    """

    __tablename__ = "portfolio_ledger_account_mappings"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "cash_account_id",
            "currency_definition_id",
            name="uq_portfolio_ledger_mapping_scope",
        ),
        ForeignKeyConstraint(
            ["portfolio_id", "owner_id"],
            ["investment_portfolios.id", "investment_portfolios.owner_id"],
            ondelete="RESTRICT",
            name="fk_portfolio_ledger_mapping_portfolio_owner",
        ),
        ForeignKeyConstraint(
            ["cash_account_id", "owner_id", "currency_definition_id"],
            [
                "financial_accounts.id",
                "financial_accounts.owner_id",
                "financial_accounts.currency_definition_id",
            ],
            ondelete="RESTRICT",
            name="fk_portfolio_ledger_mapping_cash_owner_currency",
        ),
        ForeignKeyConstraint(
            ["investment_control_account_id", "owner_id", "currency_definition_id"],
            [
                "financial_accounts.id",
                "financial_accounts.owner_id",
                "financial_accounts.currency_definition_id",
            ],
            ondelete="RESTRICT",
            name="fk_portfolio_ledger_mapping_investment_owner_currency",
        ),
        ForeignKeyConstraint(
            ["realized_gain_account_id", "owner_id", "currency_definition_id"],
            [
                "financial_accounts.id",
                "financial_accounts.owner_id",
                "financial_accounts.currency_definition_id",
            ],
            ondelete="RESTRICT",
            name="fk_portfolio_ledger_mapping_gain_owner_currency",
        ),
        ForeignKeyConstraint(
            ["realized_loss_account_id", "owner_id", "currency_definition_id"],
            [
                "financial_accounts.id",
                "financial_accounts.owner_id",
                "financial_accounts.currency_definition_id",
            ],
            ondelete="RESTRICT",
            name="fk_portfolio_ledger_mapping_loss_owner_currency",
        ),
        CheckConstraint(
            "cash_account_id <> investment_control_account_id "
            "AND cash_account_id <> realized_gain_account_id "
            "AND cash_account_id <> realized_loss_account_id "
            "AND investment_control_account_id <> realized_gain_account_id "
            "AND investment_control_account_id <> realized_loss_account_id "
            "AND realized_gain_account_id <> realized_loss_account_id",
            name="ck_portfolio_ledger_mapping_distinct_accounts",
        ),
        Index(
            "ix_portfolio_ledger_mapping_owner_portfolio",
            "owner_id",
            "portfolio_id",
        ),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    portfolio_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    cash_account_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    investment_control_account_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    realized_gain_account_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    realized_loss_account_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    currency_definition_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
