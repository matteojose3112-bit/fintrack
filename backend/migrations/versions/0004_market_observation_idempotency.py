"""Add idempotency uniqueness for provider market observations."""

from alembic import op


revision = "0004_obs_idempotency"
down_revision = "0003_global_instrument_master"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "uq_market_observations_provider_record",
        "market_observations",
        ["provider_source_id", "source_record_id", "observation_type", "instrument_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        "uq_market_observations_provider_record",
        table_name="market_observations",
    )
