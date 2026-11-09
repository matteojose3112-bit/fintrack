"""Convert monetary columns to fixed-precision decimals.

Existing values are converted to Numeric(14, 2), rounding to the nearest
cent during the database type conversion. Back up production data before
applying this migration; this file does not execute or initiate a deployment.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_fixed_money"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

MONEY = sa.Numeric(precision=14, scale=2)


def upgrade():
    # Batch mode uses table recreation on SQLite and native ALTER on PostgreSQL.
    # Both paths preserve rows while applying the explicitly chosen 2dp scale.
    for table, columns in (
        ("transactions", ("amount",)),
        ("budgets", ("limit",)),
        ("goals", ("target_amount", "saved_amount")),
    ):
        with op.batch_alter_table(table) as batch_op:
            for column in columns:
                batch_op.alter_column(
                    column,
                    existing_type=sa.Float(),
                    type_=MONEY,
                    existing_nullable=False,
                )


def downgrade():
    # Downgrading back to binary floats is inherently lossy.
    for table, columns in (
        ("transactions", ("amount",)),
        ("budgets", ("limit",)),
        ("goals", ("target_amount", "saved_amount")),
    ):
        with op.batch_alter_table(table) as batch_op:
            for column in columns:
                batch_op.alter_column(
                    column,
                    existing_type=MONEY,
                    type_=sa.Float(),
                    existing_nullable=False,
                )
