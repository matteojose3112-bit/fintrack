"""Create global unit, asset, instrument, venue, contract, and market-data tables."""

from alembic import op
import sqlalchemy as sa


revision = "0003_global_instrument_master"
down_revision = "0002_aurelius_ledger"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "unit_definitions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("dimension", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column(
            "base_unit_code",
            sa.String(64),
            sa.ForeignKey("unit_definitions.code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("conversion_numerator", sa.BigInteger(), nullable=True),
        sa.Column("conversion_denominator", sa.BigInteger(), nullable=True),
        sa.Column("quantity_precision", sa.SmallInteger(), nullable=False),
        sa.Column("context_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_unit_definitions_code"),
        sa.CheckConstraint("quantity_precision BETWEEN 0 AND 18", name="ck_unit_definitions_precision"),
        sa.CheckConstraint(
            "(context_required = TRUE AND conversion_numerator IS NULL AND conversion_denominator IS NULL) OR "
            "(context_required = FALSE AND conversion_numerator > 0 AND conversion_denominator > 0)",
            name="ck_unit_definitions_conversion_ratio",
        ),
    )

    op.create_table(
        "asset_definitions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("asset_id", sa.String(160), nullable=False),
        sa.Column("asset_class", sa.String(64), nullable=False),
        sa.Column("asset_type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "quantity_unit_code",
            sa.String(64),
            sa.ForeignKey("unit_definitions.code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("source_retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("asset_id", name="uq_asset_definitions_asset_id"),
    )
    op.create_index(
        "ix_asset_definitions_class_type", "asset_definitions", ["asset_class", "asset_type"]
    )

    op.create_table(
        "instrument_definitions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("instrument_type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column(
            "underlying_asset_id",
            sa.String(160),
            sa.ForeignKey("asset_definitions.asset_id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "quote_currency_definition_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("source_record_id", sa.String(200), nullable=True),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("source_retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_instrument_definitions_type_status",
        "instrument_definitions",
        ["instrument_type", "status"],
    )

    op.create_table(
        "instrument_identifiers",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "instrument_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("instrument_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("namespace", sa.String(64), nullable=False),
        sa.Column("value", sa.String(240), nullable=False),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_instrument_identifiers_valid_range",
        ),
    )
    op.create_index(
        "ix_instrument_identifiers_namespace_value",
        "instrument_identifiers",
        ["namespace", "value", "source_id"],
    )
    op.create_index(
        "ix_instrument_identifiers_instrument",
        "instrument_identifiers",
        ["instrument_id"],
    )

    op.create_table(
        "market_venues",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("mic", sa.String(4), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("venue_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("mic", name="uq_market_venues_mic"),
        sa.CheckConstraint("length(mic) = 4", name="ck_market_venues_mic_length"),
        sa.CheckConstraint("length(country_code) = 2", name="ck_market_venues_country_length"),
    )

    op.create_table(
        "instrument_listings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "instrument_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("instrument_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "venue_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("market_venues.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(80), nullable=False),
        sa.Column(
            "quote_currency_definition_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("active_from", sa.Date(), nullable=False),
        sa.Column("active_to", sa.Date(), nullable=True),
        sa.Column("trading_calendar_code", sa.String(64), nullable=False, server_default="default"),
        sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("source_record_id", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "active_to IS NULL OR active_to >= active_from",
            name="ck_instrument_listings_active_range",
        ),
        sa.UniqueConstraint(
            "venue_id", "symbol", "active_from",
            name="uq_instrument_listings_venue_symbol_start",
        ),
    )
    op.create_index(
        "ix_instrument_listings_instrument",
        "instrument_listings",
        ["instrument_id"],
    )

    op.create_table(
        "derivative_contract_specs",
        sa.Column(
            "instrument_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("instrument_definitions.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "underlying_asset_id",
            sa.String(160),
            sa.ForeignKey("asset_definitions.asset_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "contract_unit_code",
            sa.String(64),
            sa.ForeignKey("unit_definitions.code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("contract_size", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("tick_size", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("tick_value", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("first_notice_date", sa.Date(), nullable=True),
        sa.Column("last_trade_date", sa.Date(), nullable=True),
        sa.Column("settlement_type", sa.String(16), nullable=False),
        sa.Column(
            "margin_currency_definition_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("delivery_grade", sa.String(160), nullable=True),
        sa.Column("delivery_location", sa.String(240), nullable=True),
        sa.CheckConstraint("contract_size > 0", name="ck_derivative_contract_size_positive"),
        sa.CheckConstraint("tick_size > 0", name="ck_derivative_tick_size_positive"),
        sa.CheckConstraint("tick_value > 0", name="ck_derivative_tick_value_positive"),
        sa.CheckConstraint("settlement_type IN ('cash', 'physical')", name="ck_derivative_settlement_type"),
        sa.CheckConstraint(
            "first_notice_date IS NULL OR first_notice_date <= expiry_date",
            name="ck_derivative_first_notice_before_expiry",
        ),
        sa.CheckConstraint(
            "last_trade_date IS NULL OR last_trade_date <= expiry_date",
            name="ck_derivative_last_trade_before_expiry",
        ),
    )

    op.create_table(
        "bond_contract_specs",
        sa.Column(
            "instrument_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("instrument_definitions.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "issuer_asset_id",
            sa.String(160),
            sa.ForeignKey("asset_definitions.asset_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "currency_definition_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("face_value_minor", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("maturity_date", sa.Date(), nullable=False),
        sa.Column("coupon_type", sa.String(24), nullable=False),
        sa.Column("coupon_rate", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("coupon_frequency", sa.SmallInteger(), nullable=False),
        sa.Column("day_count_convention", sa.String(32), nullable=False),
        sa.Column("seniority", sa.String(64), nullable=False),
        sa.CheckConstraint("face_value_minor > 0", name="ck_bond_face_value_positive"),
        sa.CheckConstraint("coupon_rate >= 0", name="ck_bond_coupon_rate_nonnegative"),
        sa.CheckConstraint(
            "coupon_type IN ('fixed', 'floating', 'zero', 'inflation_linked')",
            name="ck_bond_coupon_type",
        ),
        sa.CheckConstraint("coupon_frequency IN (0, 1, 2, 4, 6, 12)", name="ck_bond_coupon_frequency"),
        sa.CheckConstraint("maturity_date > issue_date", name="ck_bond_maturity_after_issue"),
    )

    op.create_table(
        "prediction_contract_specs",
        sa.Column(
            "instrument_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("instrument_definitions.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("event_id", sa.String(200), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("outcomes", sa.JSON(), nullable=False),
        sa.Column("resolution_source_url", sa.String(1000), nullable=False),
        sa.Column("resolution_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "settlement_currency_definition_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("payout_minor", sa.Numeric(asdecimal=True), nullable=False),
        sa.CheckConstraint("payout_minor > 0", name="ck_prediction_payout_positive"),
    )

    op.create_table(
        "provider_sources",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("provider_key", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("website_url", sa.String(512), nullable=True),
        sa.Column("license_name", sa.String(200), nullable=True),
        sa.Column("license_url", sa.String(512), nullable=True),
        sa.Column("terms_version", sa.String(80), nullable=False),
        sa.Column("rights_scope", sa.String(80), nullable=False),
        sa.Column("geographic_coverage", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "provider_key", "terms_version", name="uq_provider_sources_key_terms"
        ),
    )

    op.create_table(
        "market_observations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "instrument_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("instrument_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("observation_type", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column(
            "unit_code",
            sa.String(64),
            sa.ForeignKey("unit_definitions.code", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "quote_currency_definition_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "provider_source_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("provider_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_record_id", sa.String(240), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_session", sa.String(64), nullable=True),
        sa.Column("methodology", sa.String(240), nullable=True),
        sa.Column("license_reference", sa.String(240), nullable=True),
        sa.CheckConstraint(
            "retrieved_at >= observed_at",
            name="ck_market_observations_retrieved_after_observed",
        ),
    )
    op.create_index(
        "ix_market_observations_instrument_observed",
        "market_observations",
        ["instrument_id", "observation_type", "observed_at"],
    )
    op.create_index(
        "ix_market_observations_source_record",
        "market_observations",
        ["provider_source_id", "source_record_id"],
    )

    op.create_table(
        "forecast_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("target_id", sa.String(240), nullable=False),
        sa.Column("model_id", sa.String(120), nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("probability", sa.Numeric(asdecimal=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "probability >= 0 AND probability <= 1",
            name="ck_forecast_records_probability_range",
        ),
        sa.CheckConstraint(
            "horizon_end >= generated_at",
            name="ck_forecast_records_horizon_after_generation",
        ),
    )
    op.create_index(
        "ix_forecast_records_target_horizon",
        "forecast_records",
        ["target_id", "horizon_end"],
    )

    op.create_table(
        "forecast_resolutions",
        sa.Column(
            "forecast_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("forecast_records.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("resolved_outcome", sa.String(240), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scoring_method", sa.String(64), nullable=False),
        sa.Column("score", sa.Numeric(asdecimal=True), nullable=True),
        sa.Column("resolution_source_url", sa.String(1000), nullable=True),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 1)",
            name="ck_forecast_resolutions_score_range",
        ),
    )

    if op.get_bind().dialect.name == "postgresql":
        _install_postgresql_guards()


def _install_postgresql_guards():
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE instrument_identifiers
        ADD CONSTRAINT ex_instrument_identifiers_no_overlapping_validity
        EXCLUDE USING gist (
            namespace WITH =,
            value WITH =,
            source_id WITH =,
            daterange(valid_from, valid_to, '[]') WITH &&
        )
        """
    )
    op.execute(
        """
        ALTER TABLE instrument_listings
        ADD CONSTRAINT ex_instrument_listings_no_overlapping_symbol
        EXCLUDE USING gist (
            venue_id WITH =,
            symbol WITH =,
            daterange(active_from, active_to, '[]') WITH &&
        )
        """
    )
    op.execute(
        """
        ALTER TABLE market_venues
        ADD CONSTRAINT ck_market_venues_mic_format
        CHECK (mic ~ '^[A-Z0-9]{4}$' AND country_code ~ '^[A-Z]{2}$')
        """
    )
    op.execute(
        """
        ALTER TABLE bond_contract_specs
        ADD CONSTRAINT ck_bond_face_value_integral_minor
        CHECK (
            face_value_minor = trunc(face_value_minor)
            AND face_value_minor > 0
            AND face_value_minor < 100000000000000000000000000000000000000::numeric
        )
        """
    )
    op.execute(
        """
        ALTER TABLE prediction_contract_specs
        ADD CONSTRAINT ck_prediction_payout_integral_minor
        CHECK (
            payout_minor = trunc(payout_minor)
            AND payout_minor > 0
            AND payout_minor < 100000000000000000000000000000000000000::numeric
        )
        """
    )
    for table in (
        "unit_definitions",
        "asset_definitions",
        "instrument_definitions",
        "instrument_identifiers",
        "market_venues",
        "instrument_listings",
        "derivative_contract_specs",
        "bond_contract_specs",
        "prediction_contract_specs",
        "provider_sources",
        "market_observations",
        "forecast_records",
        "forecast_resolutions",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION aurelius_reject_immutable_mutation()
            """
        )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table in (
            "unit_definitions",
            "asset_definitions",
            "instrument_definitions",
            "instrument_identifiers",
            "market_venues",
            "instrument_listings",
            "derivative_contract_specs",
            "bond_contract_specs",
            "prediction_contract_specs",
            "provider_sources",
            "market_observations",
            "forecast_records",
            "forecast_resolutions",
        ):
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")
        op.execute(
            "ALTER TABLE prediction_contract_specs "
            "DROP CONSTRAINT IF EXISTS ck_prediction_payout_integral_minor"
        )
        op.execute(
            "ALTER TABLE bond_contract_specs "
            "DROP CONSTRAINT IF EXISTS ck_bond_face_value_integral_minor"
        )
        op.execute(
            "ALTER TABLE market_venues "
            "DROP CONSTRAINT IF EXISTS ck_market_venues_mic_format"
        )
        op.execute(
            "ALTER TABLE instrument_listings "
            "DROP CONSTRAINT IF EXISTS ex_instrument_listings_no_overlapping_symbol"
        )
        op.execute(
            "ALTER TABLE instrument_identifiers "
            "DROP CONSTRAINT IF EXISTS ex_instrument_identifiers_no_overlapping_validity"
        )

    op.drop_table("forecast_resolutions")
    op.drop_index("ix_forecast_records_target_horizon", table_name="forecast_records")
    op.drop_table("forecast_records")
    op.drop_index("ix_market_observations_source_record", table_name="market_observations")
    op.drop_index("ix_market_observations_instrument_observed", table_name="market_observations")
    op.drop_table("market_observations")
    op.drop_table("provider_sources")
    op.drop_table("prediction_contract_specs")
    op.drop_table("bond_contract_specs")
    op.drop_table("derivative_contract_specs")
    op.drop_index("ix_instrument_listings_instrument", table_name="instrument_listings")
    op.drop_table("instrument_listings")
    op.drop_table("market_venues")
    op.drop_index("ix_instrument_identifiers_instrument", table_name="instrument_identifiers")
    op.drop_index("ix_instrument_identifiers_namespace_value", table_name="instrument_identifiers")
    op.drop_table("instrument_identifiers")
    op.drop_index("ix_instrument_definitions_type_status", table_name="instrument_definitions")
    op.drop_table("instrument_definitions")
    op.drop_index("ix_asset_definitions_class_type", table_name="asset_definitions")
    op.drop_table("asset_definitions")
    op.drop_table("unit_definitions")
