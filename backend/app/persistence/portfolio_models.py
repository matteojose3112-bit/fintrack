"""Owner-scoped, append-only portfolio trade and lot persistence."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InvestmentPortfolioModel(Base):
    __tablename__ = "investment_portfolios"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'ARCHIVED')", name="ck_investment_portfolios_status"),
        UniqueConstraint("id", "owner_id", name="uq_investment_portfolios_id_owner"),
        Index("ix_investment_portfolios_owner_status", "owner_id", "status"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TradeExecutionModel(Base):
    """Immutable imported/recorded fill; never represents an order instruction."""

    __tablename__ = "trade_executions"
    __table_args__ = (
        CheckConstraint("side IN ('BUY', 'SELL')", name="ck_trade_executions_side"),
        CheckConstraint(
            "cost_basis_method IN ('fifo', 'lifo', 'specific')",
            name="ck_trade_executions_cost_basis_method",
        ),
        CheckConstraint("quantity > 0", name="ck_trade_executions_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_trade_executions_unit_price_nonnegative"),
        CheckConstraint("fee >= 0", name="ck_trade_executions_fee_nonnegative"),
        CheckConstraint("accounting_precision_version IN (1, 2)", name="ck_trade_executions_precision_version"),
        CheckConstraint(
            "(cost_basis_method = 'specific' AND specific_lot_id IS NOT NULL) OR "
            "(cost_basis_method <> 'specific' AND specific_lot_id IS NULL)",
            name="ck_trade_executions_specific_lot_argument",
        ),
        UniqueConstraint("id", "owner_id", name="uq_trade_executions_id_owner"),
        UniqueConstraint(
            "id", "owner_id", "portfolio_id", "account_id", "instrument_id",
            "quote_currency_definition_id",
            name="uq_trade_executions_position_scope",
        ),
        ForeignKeyConstraint(
            ["portfolio_id", "owner_id"],
            ["investment_portfolios.id", "investment_portfolios.owner_id"],
            ondelete="RESTRICT",
            name="fk_trade_executions_portfolio_owner",
        ),
        ForeignKeyConstraint(
            ["account_id", "owner_id"],
            ["financial_accounts.id", "financial_accounts.owner_id"],
            ondelete="RESTRICT",
            name="fk_trade_executions_account_owner",
        ),
        ForeignKeyConstraint(
            ["instrument_id"],
            ["instrument_definitions.id"],
            ondelete="RESTRICT",
            name="fk_trade_executions_instrument",
        ),
        ForeignKeyConstraint(
            ["quote_currency_definition_id"],
            ["currency_definitions.id"],
            ondelete="RESTRICT",
            name="fk_trade_executions_quote_currency",
        ),
        Index(
            "ix_trade_executions_position_time",
            "portfolio_id", "account_id", "instrument_id",
            "quote_currency_definition_id", "executed_at", "id",
        ),
        Index("ix_trade_executions_owner_time", "owner_id", "executed_at"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    portfolio_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    account_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    instrument_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    quote_currency_definition_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    unit_price: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    fee: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    executed_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    cost_basis_method: Mapped[str] = mapped_column(String(16), nullable=False, default="fifo")
    specific_lot_id: Mapped[object | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    accounting_precision_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PortfolioLotModel(Base):
    """Immutable acquisition lot; remaining quantity/cost are derived from disposals."""

    __tablename__ = "portfolio_lots"
    __table_args__ = (
        CheckConstraint("original_quantity > 0", name="ck_portfolio_lots_quantity_positive"),
        CheckConstraint("original_cost >= 0", name="ck_portfolio_lots_cost_nonnegative"),
        UniqueConstraint("id", "owner_id", "portfolio_id", "account_id", "instrument_id",
                         "quote_currency_definition_id", name="uq_portfolio_lots_position_scope"),
        ForeignKeyConstraint(
            ["portfolio_id", "owner_id"],
            ["investment_portfolios.id", "investment_portfolios.owner_id"],
            ondelete="RESTRICT",
            name="fk_portfolio_lots_portfolio_owner",
        ),
        ForeignKeyConstraint(
            ["account_id", "owner_id"],
            ["financial_accounts.id", "financial_accounts.owner_id"],
            ondelete="RESTRICT",
            name="fk_portfolio_lots_account_owner",
        ),
        ForeignKeyConstraint(
            ["opened_by_execution_id", "owner_id", "portfolio_id", "account_id",
             "instrument_id", "quote_currency_definition_id"],
            ["trade_executions.id", "trade_executions.owner_id",
             "trade_executions.portfolio_id", "trade_executions.account_id",
             "trade_executions.instrument_id", "trade_executions.quote_currency_definition_id"],
            ondelete="RESTRICT",
            name="fk_portfolio_lots_opening_execution_scope",
        ),
        Index("ix_portfolio_lots_position_opened", "portfolio_id", "account_id",
              "instrument_id", "quote_currency_definition_id", "opened_at"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    portfolio_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    account_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    instrument_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    quote_currency_definition_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    opened_by_execution_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    opened_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    original_quantity: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    original_cost: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LotDisposalAllocationModel(Base):
    """Immutable slice of one acquisition lot consumed by a sell execution."""

    __tablename__ = "lot_disposal_allocations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_lot_disposals_quantity_positive"),
        CheckConstraint("cost_basis >= 0", name="ck_lot_disposals_cost_basis_nonnegative"),
        CheckConstraint("gross_proceeds >= 0", name="ck_lot_disposals_gross_nonnegative"),
        CheckConstraint("allocated_sale_fee >= 0", name="ck_lot_disposals_fee_nonnegative"),
        UniqueConstraint("disposal_execution_id", "lot_id", name="uq_lot_disposals_execution_lot"),
        ForeignKeyConstraint(
            ["disposal_execution_id", "owner_id", "portfolio_id", "account_id",
             "instrument_id", "quote_currency_definition_id"],
            ["trade_executions.id", "trade_executions.owner_id",
             "trade_executions.portfolio_id", "trade_executions.account_id",
             "trade_executions.instrument_id", "trade_executions.quote_currency_definition_id"],
            ondelete="RESTRICT",
            name="fk_lot_disposals_execution_scope",
        ),
        ForeignKeyConstraint(
            ["lot_id", "owner_id", "portfolio_id", "account_id", "instrument_id",
             "quote_currency_definition_id"],
            ["portfolio_lots.id", "portfolio_lots.owner_id", "portfolio_lots.portfolio_id",
             "portfolio_lots.account_id", "portfolio_lots.instrument_id",
             "portfolio_lots.quote_currency_definition_id"],
            ondelete="RESTRICT",
            name="fk_lot_disposals_lot_scope",
        ),
        Index("ix_lot_disposals_lot", "lot_id"),
        Index("ix_lot_disposals_owner_execution", "owner_id", "disposal_execution_id"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    portfolio_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    account_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    instrument_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    quote_currency_definition_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    disposal_execution_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    lot_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), nullable=False)
    quantity: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    cost_basis: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    gross_proceeds: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    allocated_sale_fee: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    net_proceeds: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    realized_gain_loss: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PortfolioPositionLockModel(Base):
    """Mutable serialization row; financial facts remain append-only elsewhere."""

    __tablename__ = "portfolio_position_locks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["portfolio_id", "owner_id"],
            ["investment_portfolios.id", "investment_portfolios.owner_id"],
            ondelete="RESTRICT",
            name="fk_portfolio_position_locks_portfolio_owner",
        ),
        ForeignKeyConstraint(
            ["account_id", "owner_id"],
            ["financial_accounts.id", "financial_accounts.owner_id"],
            ondelete="RESTRICT",
            name="fk_portfolio_position_locks_account_owner",
        ),
        UniqueConstraint(
            "portfolio_id", "account_id", "instrument_id", "quote_currency_definition_id",
            name="uq_portfolio_position_locks_key",
        ),
        ForeignKeyConstraint(
            ["instrument_id"], ["instrument_definitions.id"],
            ondelete="RESTRICT", name="fk_portfolio_position_locks_instrument",
        ),
        ForeignKeyConstraint(
            ["quote_currency_definition_id"], ["currency_definitions.id"],
            ondelete="RESTRICT", name="fk_portfolio_position_locks_quote_currency",
        ),
    )

    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    portfolio_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    account_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    instrument_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    quote_currency_definition_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
