"""Persist deterministic reconciliation proposals and explicit confirmations."""

from alembic import op
import sqlalchemy as sa


revision = "0010_reconciliation_matches"
down_revision = "0009_reconciliation_import"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("journal_postings") as batch_op:
        batch_op.create_unique_constraint(
            "uq_journal_postings_id_owner", ["id", "owner_id"]
        )
    with op.batch_alter_table("reconciliation_statement_rows") as batch_op:
        batch_op.create_unique_constraint(
            "uq_reconciliation_statement_rows_id_owner", ["id", "owner_id"]
        )

    op.create_table(
        "reconciliation_matches",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("batch_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("statement_row_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("journal_posting_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("strategy", sa.String(40), nullable=True),
        sa.Column("date_difference_days", sa.SmallInteger(), nullable=True),
        sa.Column("confirmed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_action_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("id", "owner_id", name="uq_reconciliation_matches_id_owner"),
        sa.UniqueConstraint("statement_row_id", name="uq_reconciliation_match_statement_row"),
        sa.ForeignKeyConstraint(
            ["batch_id", "owner_id"],
            ["reconciliation_import_batches.id", "reconciliation_import_batches.owner_id"],
            ondelete="RESTRICT", name="fk_reconciliation_match_batch_owner",
        ),
        sa.ForeignKeyConstraint(
            ["statement_row_id", "owner_id"],
            ["reconciliation_statement_rows.id", "reconciliation_statement_rows.owner_id"],
            ondelete="RESTRICT", name="fk_reconciliation_match_statement_row_owner",
        ),
        sa.ForeignKeyConstraint(
            ["journal_posting_id", "owner_id"],
            ["journal_postings.id", "journal_postings.owner_id"],
            ondelete="RESTRICT", name="fk_reconciliation_match_posting_owner",
        ),
        sa.CheckConstraint(
            "status IN ('PROPOSED', 'AMBIGUOUS', 'UNMATCHED', 'CONFIRMED', 'REJECTED')",
            name="ck_reconciliation_match_status",
        ),
        sa.CheckConstraint(
            "date_difference_days IS NULL OR date_difference_days BETWEEN 0 AND 31",
            name="ck_reconciliation_match_date_difference",
        ),
    )
    op.create_index(
        "uq_reconciliation_confirmed_posting",
        "reconciliation_matches",
        ["journal_posting_id"],
        unique=True,
        postgresql_where=sa.text("status = 'CONFIRMED' AND journal_posting_id IS NOT NULL"),
        sqlite_where=sa.text("status = 'CONFIRMED' AND journal_posting_id IS NOT NULL"),
    )
    op.create_index(
        "ix_reconciliation_matches_owner_status",
        "reconciliation_matches",
        ["owner_id", "status", "last_action_at"],
    )


def downgrade():
    op.drop_index(
        "ix_reconciliation_matches_owner_status",
        table_name="reconciliation_matches",
    )
    op.drop_index(
        "uq_reconciliation_confirmed_posting",
        table_name="reconciliation_matches",
    )
    op.drop_table("reconciliation_matches")
    with op.batch_alter_table("reconciliation_statement_rows") as batch_op:
        batch_op.drop_constraint(
            "uq_reconciliation_statement_rows_id_owner", type_="unique"
        )
    with op.batch_alter_table("journal_postings") as batch_op:
        batch_op.drop_constraint("uq_journal_postings_id_owner", type_="unique")
