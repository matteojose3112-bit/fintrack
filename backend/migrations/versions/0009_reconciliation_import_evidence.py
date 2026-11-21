"""Persist immutable FinTrack reconciliation statement evidence."""

from alembic import op
import sqlalchemy as sa


revision = "0009_reconciliation_import"
down_revision = "0008_portfolio_precision_version"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reconciliation_import_batches",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("currency_definition_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(32), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("id", "owner_id", name="uq_reconciliation_batches_id_owner"),
        sa.UniqueConstraint(
            "owner_id", "account_id", "file_sha256", "parser_version",
            name="uq_reconciliation_batch_file_replay",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "owner_id", "currency_definition_id"],
            ["financial_accounts.id", "financial_accounts.owner_id", "financial_accounts.currency_definition_id"],
            ondelete="RESTRICT", name="fk_reconciliation_batch_account_owner_currency",
        ),
        sa.CheckConstraint(
            "status IN ('VALIDATED', 'HAS_ERRORS')",
            name="ck_reconciliation_batch_status",
        ),
        sa.CheckConstraint("row_count >= 0", name="ck_reconciliation_batch_row_count"),
    )
    op.create_index(
        "ix_reconciliation_batches_owner_account_imported",
        "reconciliation_import_batches", ["owner_id", "account_id", "imported_at"],
    )

    op.create_table(
        "reconciliation_statement_rows",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("batch_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("amount_minor", sa.Numeric(38, 0, asdecimal=True), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("description", sa.String(4096), nullable=False),
        sa.Column("source_transaction_id", sa.String(512), nullable=True),
        sa.Column("counterparty", sa.String(1024), nullable=True),
        sa.Column("reference", sa.String(1024), nullable=True),
        sa.Column("source_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "batch_id", "owner_id", "row_number",
            name="uq_reconciliation_statement_row_number",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id", "owner_id"],
            ["reconciliation_import_batches.id", "reconciliation_import_batches.owner_id"],
            ondelete="RESTRICT", name="fk_reconciliation_statement_row_batch_owner",
        ),
        sa.CheckConstraint("row_number > 0", name="ck_reconciliation_statement_row_number"),
        sa.CheckConstraint(
            "amount_minor BETWEEN -99999999999999999999999999999999999999 "
            "AND 99999999999999999999999999999999999999",
            name="ck_reconciliation_statement_amount_range",
        ),
    )
    op.create_index(
        "ix_reconciliation_statement_rows_owner_date",
        "reconciliation_statement_rows", ["owner_id", "booking_date"],
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
        CREATE FUNCTION fintrack_reconciliation_evidence_immutable()
        RETURNS trigger
        LANGUAGE plpgsql
        AS 'BEGIN
            RAISE EXCEPTION ''reconciliation source evidence is append-only''
                USING ERRCODE = ''55000'';
        END;'
        """)
        for table in ("reconciliation_import_batches", "reconciliation_statement_rows"):
            op.execute(f"""
            CREATE TRIGGER trg_{table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION fintrack_reconciliation_evidence_immutable()
            """)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table in ("reconciliation_import_batches", "reconciliation_statement_rows"):
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")
        op.execute("DROP FUNCTION IF EXISTS fintrack_reconciliation_evidence_immutable()")
    op.drop_index(
        "ix_reconciliation_statement_rows_owner_date",
        table_name="reconciliation_statement_rows",
    )
    op.drop_table("reconciliation_statement_rows")
    op.drop_index(
        "ix_reconciliation_batches_owner_account_imported",
        table_name="reconciliation_import_batches",
    )
    op.drop_table("reconciliation_import_batches")
