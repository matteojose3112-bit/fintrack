"""Persist owner-scoped trade executions, acquisition lots, and disposals."""

from alembic import op
import sqlalchemy as sa


revision = "0005_portfolio_lots"
down_revision = "0004_obs_idempotency"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("financial_accounts") as batch_op:
        batch_op.create_unique_constraint(
            "uq_financial_accounts_id_owner", ["id", "owner_id"]
        )

    op.create_table(
        "investment_portfolios",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("id", "owner_id", name="uq_investment_portfolios_id_owner"),
        sa.CheckConstraint("status IN ('ACTIVE', 'ARCHIVED')", name="ck_investment_portfolios_status"),
    )
    op.create_index("ix_investment_portfolios_owner_status", "investment_portfolios", ["owner_id", "status"])

    op.create_table(
        "trade_executions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("instrument_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("quote_currency_definition_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("quantity", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("unit_price", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("fee", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("cost_basis_method", sa.String(16), nullable=False, server_default="fifo"),
        sa.Column("specific_lot_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("id", "owner_id", name="uq_trade_executions_id_owner"),
        sa.UniqueConstraint(
            "id", "owner_id", "portfolio_id", "account_id", "instrument_id",
            "quote_currency_definition_id", name="uq_trade_executions_position_scope"
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id", "owner_id"], ["investment_portfolios.id", "investment_portfolios.owner_id"],
            ondelete="RESTRICT", name="fk_trade_executions_portfolio_owner"
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "owner_id"], ["financial_accounts.id", "financial_accounts.owner_id"],
            ondelete="RESTRICT", name="fk_trade_executions_account_owner"
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"], ["instrument_definitions.id"], ondelete="RESTRICT",
            name="fk_trade_executions_instrument"
        ),
        sa.ForeignKeyConstraint(
            ["quote_currency_definition_id"], ["currency_definitions.id"], ondelete="RESTRICT",
            name="fk_trade_executions_quote_currency"
        ),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_trade_executions_side"),
        sa.CheckConstraint("cost_basis_method IN ('fifo', 'lifo', 'specific')", name="ck_trade_executions_cost_basis_method"),
        sa.CheckConstraint("quantity > 0", name="ck_trade_executions_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_trade_executions_unit_price_nonnegative"),
        sa.CheckConstraint("fee >= 0", name="ck_trade_executions_fee_nonnegative"),
        sa.CheckConstraint(
            "(cost_basis_method = 'specific' AND specific_lot_id IS NOT NULL) OR "
            "(cost_basis_method <> 'specific' AND specific_lot_id IS NULL)",
            name="ck_trade_executions_specific_lot_argument"
        ),
    )
    op.create_index(
        "ix_trade_executions_position_time", "trade_executions",
        ["portfolio_id", "account_id", "instrument_id", "quote_currency_definition_id", "executed_at", "id"]
    )
    op.create_index("ix_trade_executions_owner_time", "trade_executions", ["owner_id", "executed_at"])

    op.create_table(
        "portfolio_lots",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("instrument_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("quote_currency_definition_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("opened_by_execution_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("original_quantity", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("original_cost", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "id", "owner_id", "portfolio_id", "account_id", "instrument_id",
            "quote_currency_definition_id", name="uq_portfolio_lots_position_scope"
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id", "owner_id"], ["investment_portfolios.id", "investment_portfolios.owner_id"],
            ondelete="RESTRICT", name="fk_portfolio_lots_portfolio_owner"
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "owner_id"], ["financial_accounts.id", "financial_accounts.owner_id"],
            ondelete="RESTRICT", name="fk_portfolio_lots_account_owner"
        ),
        sa.ForeignKeyConstraint(
            ["opened_by_execution_id", "owner_id", "portfolio_id", "account_id",
             "instrument_id", "quote_currency_definition_id"],
            ["trade_executions.id", "trade_executions.owner_id", "trade_executions.portfolio_id",
             "trade_executions.account_id", "trade_executions.instrument_id",
             "trade_executions.quote_currency_definition_id"],
            ondelete="RESTRICT", name="fk_portfolio_lots_opening_execution_scope"
        ),
        sa.CheckConstraint("original_quantity > 0", name="ck_portfolio_lots_quantity_positive"),
        sa.CheckConstraint("original_cost >= 0", name="ck_portfolio_lots_cost_nonnegative"),
    )
    op.create_index(
        "ix_portfolio_lots_position_opened", "portfolio_lots",
        ["portfolio_id", "account_id", "instrument_id", "quote_currency_definition_id", "opened_at"]
    )

    op.create_table(
        "lot_disposal_allocations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("instrument_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("quote_currency_definition_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("disposal_execution_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("lot_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("cost_basis", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("gross_proceeds", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("allocated_sale_fee", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("net_proceeds", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("realized_gain_loss", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("disposal_execution_id", "lot_id", name="uq_lot_disposals_execution_lot"),
        sa.ForeignKeyConstraint(
            ["disposal_execution_id", "owner_id", "portfolio_id", "account_id",
             "instrument_id", "quote_currency_definition_id"],
            ["trade_executions.id", "trade_executions.owner_id", "trade_executions.portfolio_id",
             "trade_executions.account_id", "trade_executions.instrument_id",
             "trade_executions.quote_currency_definition_id"],
            ondelete="RESTRICT", name="fk_lot_disposals_execution_scope"
        ),
        sa.ForeignKeyConstraint(
            ["lot_id", "owner_id", "portfolio_id", "account_id", "instrument_id",
             "quote_currency_definition_id"],
            ["portfolio_lots.id", "portfolio_lots.owner_id", "portfolio_lots.portfolio_id",
             "portfolio_lots.account_id", "portfolio_lots.instrument_id",
             "portfolio_lots.quote_currency_definition_id"],
            ondelete="RESTRICT", name="fk_lot_disposals_lot_scope"
        ),
        sa.CheckConstraint("quantity > 0", name="ck_lot_disposals_quantity_positive"),
        sa.CheckConstraint("cost_basis >= 0", name="ck_lot_disposals_cost_basis_nonnegative"),
        sa.CheckConstraint("gross_proceeds >= 0", name="ck_lot_disposals_gross_nonnegative"),
        sa.CheckConstraint("allocated_sale_fee >= 0", name="ck_lot_disposals_fee_nonnegative"),
    )
    op.create_index("ix_lot_disposals_lot", "lot_disposal_allocations", ["lot_id"])
    op.create_index("ix_lot_disposals_owner_execution", "lot_disposal_allocations", ["owner_id", "disposal_execution_id"])

    op.create_table(
        "portfolio_position_locks",
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("portfolio_id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("account_id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("instrument_id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("quote_currency_definition_id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("lock_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["portfolio_id", "owner_id"], ["investment_portfolios.id", "investment_portfolios.owner_id"],
            ondelete="RESTRICT", name="fk_portfolio_position_locks_portfolio_owner"
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "owner_id"], ["financial_accounts.id", "financial_accounts.owner_id"],
            ondelete="RESTRICT", name="fk_portfolio_position_locks_account_owner"
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"], ["instrument_definitions.id"], ondelete="RESTRICT",
            name="fk_portfolio_position_locks_instrument"
        ),
        sa.ForeignKeyConstraint(
            ["quote_currency_definition_id"], ["currency_definitions.id"], ondelete="RESTRICT",
            name="fk_portfolio_position_locks_quote_currency"
        ),
        sa.UniqueConstraint(
            "portfolio_id", "account_id", "instrument_id", "quote_currency_definition_id",
            name="uq_portfolio_position_locks_key"
        ),
    )

    if op.get_bind().dialect.name == "postgresql":
        numeric_columns = {
            "trade_executions": ("quantity", "unit_price", "fee"),
            "portfolio_lots": ("original_quantity", "original_cost"),
            "lot_disposal_allocations": (
                "quantity", "cost_basis", "gross_proceeds", "allocated_sale_fee",
                "net_proceeds", "realized_gain_loss",
            ),
        }
        for table, columns in numeric_columns.items():
            for column in columns:
                op.execute(
                    f"ALTER TABLE {table} ADD CONSTRAINT ck_{table}_{column}_finite "
                    f"CHECK ({column} <> 'NaN'::numeric AND {column} > -1e38 AND {column} < 1e38)"
                )
        for table in ("trade_executions", "portfolio_lots", "lot_disposal_allocations"):
            op.execute(
                f"CREATE TRIGGER trg_{table}_append_only "
                f"BEFORE UPDATE OR DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION aurelius_reject_immutable_mutation()"
            )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table in ("trade_executions", "portfolio_lots", "lot_disposal_allocations"):
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")
        numeric_columns = {
            "trade_executions": ("quantity", "unit_price", "fee"),
            "portfolio_lots": ("original_quantity", "original_cost"),
            "lot_disposal_allocations": (
                "quantity", "cost_basis", "gross_proceeds", "allocated_sale_fee",
                "net_proceeds", "realized_gain_loss",
            ),
        }
        for table, columns in numeric_columns.items():
            for column in columns:
                op.execute(
                    f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS ck_{table}_{column}_finite"
                )

    op.drop_table("portfolio_position_locks")
    op.drop_index("ix_lot_disposals_owner_execution", table_name="lot_disposal_allocations")
    op.drop_index("ix_lot_disposals_lot", table_name="lot_disposal_allocations")
    op.drop_table("lot_disposal_allocations")
    op.drop_index("ix_portfolio_lots_position_opened", table_name="portfolio_lots")
    op.drop_table("portfolio_lots")
    op.drop_index("ix_trade_executions_owner_time", table_name="trade_executions")
    op.drop_index("ix_trade_executions_position_time", table_name="trade_executions")
    op.drop_table("trade_executions")
    op.drop_index("ix_investment_portfolios_owner_status", table_name="investment_portfolios")
    op.drop_table("investment_portfolios")
    with op.batch_alter_table("financial_accounts") as batch_op:
        batch_op.drop_constraint("uq_financial_accounts_id_owner", type_="unique")
