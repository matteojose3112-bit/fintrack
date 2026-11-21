"""Add explicit owner-scoped portfolio-to-ledger account mappings."""

from alembic import op
import sqlalchemy as sa


revision = "0006_settlement_account_mapping"
down_revision = "0005_portfolio_lots"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "portfolio_ledger_account_mappings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("cash_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("investment_control_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("realized_gain_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("realized_loss_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("currency_definition_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "portfolio_id", "cash_account_id", "currency_definition_id",
            name="uq_portfolio_ledger_mapping_scope",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id", "owner_id"],
            ["investment_portfolios.id", "investment_portfolios.owner_id"],
            ondelete="RESTRICT", name="fk_portfolio_ledger_mapping_portfolio_owner",
        ),
        sa.ForeignKeyConstraint(
            ["cash_account_id", "owner_id", "currency_definition_id"],
            ["financial_accounts.id", "financial_accounts.owner_id", "financial_accounts.currency_definition_id"],
            ondelete="RESTRICT", name="fk_portfolio_ledger_mapping_cash_owner_currency",
        ),
        sa.ForeignKeyConstraint(
            ["investment_control_account_id", "owner_id", "currency_definition_id"],
            ["financial_accounts.id", "financial_accounts.owner_id", "financial_accounts.currency_definition_id"],
            ondelete="RESTRICT", name="fk_portfolio_ledger_mapping_investment_owner_currency",
        ),
        sa.ForeignKeyConstraint(
            ["realized_gain_account_id", "owner_id", "currency_definition_id"],
            ["financial_accounts.id", "financial_accounts.owner_id", "financial_accounts.currency_definition_id"],
            ondelete="RESTRICT", name="fk_portfolio_ledger_mapping_gain_owner_currency",
        ),
        sa.ForeignKeyConstraint(
            ["realized_loss_account_id", "owner_id", "currency_definition_id"],
            ["financial_accounts.id", "financial_accounts.owner_id", "financial_accounts.currency_definition_id"],
            ondelete="RESTRICT", name="fk_portfolio_ledger_mapping_loss_owner_currency",
        ),
        sa.CheckConstraint(
            "cash_account_id <> investment_control_account_id "
            "AND cash_account_id <> realized_gain_account_id "
            "AND cash_account_id <> realized_loss_account_id "
            "AND investment_control_account_id <> realized_gain_account_id "
            "AND investment_control_account_id <> realized_loss_account_id "
            "AND realized_gain_account_id <> realized_loss_account_id",
            name="ck_portfolio_ledger_mapping_distinct_accounts",
        ),
    )
    op.create_index(
        "ix_portfolio_ledger_mapping_owner_portfolio",
        "portfolio_ledger_account_mappings",
        ["owner_id", "portfolio_id"],
    )

    # Composite FKs enforce owner and currency equality. PostgreSQL additionally
    # enforces account role types and OPEN status at mapping creation/update time.
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
        CREATE FUNCTION aurelius_validate_portfolio_ledger_account_mapping()
        RETURNS trigger AS $$
        DECLARE
            v_portfolio_status text;
            v_account_type text;
            v_account_status text;
        BEGIN
            SELECT status INTO v_portfolio_status
            FROM investment_portfolios
            WHERE id = NEW.portfolio_id AND owner_id = NEW.owner_id
            FOR KEY SHARE;
            IF v_portfolio_status IS DISTINCT FROM 'ACTIVE' THEN
                RAISE EXCEPTION 'portfolio ledger mapping requires an active owned portfolio'
                    USING ERRCODE = '23514';
            END IF;

            SELECT fa.account_type, fa.status INTO v_account_type, v_account_status
            FROM financial_accounts AS fa
            WHERE fa.id = NEW.cash_account_id
              AND fa.owner_id = NEW.owner_id
              AND fa.currency_definition_id = NEW.currency_definition_id
            FOR KEY SHARE;
            IF v_account_type IS DISTINCT FROM 'ASSET' OR v_account_status IS DISTINCT FROM 'OPEN' THEN
                RAISE EXCEPTION 'mapped brokerage cash account must be an open ASSET account'
                    USING ERRCODE = '23514';
            END IF;

            SELECT fa.account_type, fa.status INTO v_account_type, v_account_status
            FROM financial_accounts AS fa
            WHERE fa.id = NEW.investment_control_account_id
              AND fa.owner_id = NEW.owner_id
              AND fa.currency_definition_id = NEW.currency_definition_id
            FOR KEY SHARE;
            IF v_account_type IS DISTINCT FROM 'ASSET' OR v_account_status IS DISTINCT FROM 'OPEN' THEN
                RAISE EXCEPTION 'investment control account must be an open ASSET account'
                    USING ERRCODE = '23514';
            END IF;

            SELECT fa.account_type, fa.status INTO v_account_type, v_account_status
            FROM financial_accounts AS fa
            WHERE fa.id = NEW.realized_gain_account_id
              AND fa.owner_id = NEW.owner_id
              AND fa.currency_definition_id = NEW.currency_definition_id
            FOR KEY SHARE;
            IF v_account_type IS DISTINCT FROM 'INCOME' OR v_account_status IS DISTINCT FROM 'OPEN' THEN
                RAISE EXCEPTION 'realized gain account must be an open INCOME account'
                    USING ERRCODE = '23514';
            END IF;

            SELECT fa.account_type, fa.status INTO v_account_type, v_account_status
            FROM financial_accounts AS fa
            WHERE fa.id = NEW.realized_loss_account_id
              AND fa.owner_id = NEW.owner_id
              AND fa.currency_definition_id = NEW.currency_definition_id
            FOR KEY SHARE;
            IF v_account_type IS DISTINCT FROM 'EXPENSE' OR v_account_status IS DISTINCT FROM 'OPEN' THEN
                RAISE EXCEPTION 'realized loss account must be an open EXPENSE account'
                    USING ERRCODE = '23514';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
        )
        op.execute(
            """
        CREATE TRIGGER trg_portfolio_ledger_mapping_validate
        BEFORE INSERT OR UPDATE ON portfolio_ledger_account_mappings
        FOR EACH ROW EXECUTE FUNCTION aurelius_validate_portfolio_ledger_account_mapping()
        """
        )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_portfolio_ledger_mapping_validate "
            "ON portfolio_ledger_account_mappings"
        )
        op.execute("DROP FUNCTION IF EXISTS aurelius_validate_portfolio_ledger_account_mapping()")
    op.drop_index(
        "ix_portfolio_ledger_mapping_owner_portfolio",
        table_name="portfolio_ledger_account_mappings",
    )
    op.drop_table("portfolio_ledger_account_mappings")
