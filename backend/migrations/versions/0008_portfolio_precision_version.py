"""Version portfolio lot monetary precision without rewriting history."""

from alembic import op
import sqlalchemy as sa


revision = "0008_portfolio_precision_version"
down_revision = "0006_settlement_account_mapping"
branch_labels = None
depends_on = None


def upgrade():
    # Batch mode keeps the revision portable to SQLite migration tests.
    with op.batch_alter_table("trade_executions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "accounting_precision_version",
                sa.SmallInteger(),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.create_check_constraint(
            "ck_trade_executions_precision_version",
            "accounting_precision_version IN (1, 2)",
        )


def downgrade():
    with op.batch_alter_table("trade_executions") as batch_op:
        batch_op.drop_constraint(
            "ck_trade_executions_precision_version",
            type_="check",
        )
        batch_op.drop_column("accounting_precision_version")
