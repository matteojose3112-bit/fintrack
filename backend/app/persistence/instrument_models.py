"""Global reference-data and market-intelligence persistence models."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UnitDefinitionModel(Base):
    __tablename__ = "unit_definitions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_unit_definitions_code"),
        CheckConstraint(
            "quantity_precision BETWEEN 0 AND 18",
            name="ck_unit_definitions_precision",
        ),
        CheckConstraint(
            "(context_required = TRUE AND conversion_numerator IS NULL AND conversion_denominator IS NULL) OR "
            "(context_required = FALSE AND conversion_numerator > 0 AND conversion_denominator > 0)",
            name="ck_unit_definitions_conversion_ratio",
        ),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    base_unit_code: Mapped[str] = mapped_column(
        String(64), ForeignKey("unit_definitions.code", ondelete="RESTRICT"), nullable=False
    )
    conversion_numerator: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    conversion_denominator: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    quantity_precision: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    context_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AssetDefinitionModel(Base):
    __tablename__ = "asset_definitions"
    __table_args__ = (
        UniqueConstraint("asset_id", name="uq_asset_definitions_asset_id"),
        Index("ix_asset_definitions_class_type", "asset_class", "asset_type"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(160), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    quantity_unit_code: Mapped[str] = mapped_column(
        String(64), ForeignKey("unit_definitions.code", ondelete="RESTRICT"), nullable=False
    )
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_retrieved_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InstrumentDefinitionModel(Base):
    __tablename__ = "instrument_definitions"
    __table_args__ = (
        Index("ix_instrument_definitions_type_status", "instrument_type", "status"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    instrument_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    underlying_asset_id: Mapped[str | None] = mapped_column(
        String(160), ForeignKey("asset_definitions.asset_id", ondelete="RESTRICT"), nullable=True
    )
    quote_currency_definition_id: Mapped[object | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ACTIVE")
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_retrieved_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InstrumentIdentifierModel(Base):
    __tablename__ = "instrument_identifiers"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_instrument_identifiers_valid_range",
        ),
        Index(
            "ix_instrument_identifiers_namespace_value",
            "namespace",
            "value",
            "source_id",
        ),
        Index("ix_instrument_identifiers_instrument", "instrument_id"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    instrument_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("instrument_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    namespace: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(String(240), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    valid_from: Mapped[object | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[object | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MarketVenueModel(Base):
    __tablename__ = "market_venues"
    __table_args__ = (
        UniqueConstraint("mic", name="uq_market_venues_mic"),
        CheckConstraint("length(mic) = 4", name="ck_market_venues_mic_length"),
        CheckConstraint("length(country_code) = 2", name="ck_market_venues_country_length"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    mic: Mapped[str] = mapped_column(String(4), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    venue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ACTIVE")
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InstrumentListingModel(Base):
    __tablename__ = "instrument_listings"
    __table_args__ = (
        CheckConstraint(
            "active_to IS NULL OR active_to >= active_from",
            name="ck_instrument_listings_active_range",
        ),
        UniqueConstraint(
            "venue_id", "symbol", "active_from",
            name="uq_instrument_listings_venue_symbol_start",
        ),
        Index("ix_instrument_listings_instrument", "instrument_id"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    instrument_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("instrument_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    venue_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("market_venues.id", ondelete="RESTRICT"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(80), nullable=False)
    quote_currency_definition_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    active_from: Mapped[object] = mapped_column(Date, nullable=False)
    active_to: Mapped[object | None] = mapped_column(Date, nullable=True)
    trading_calendar_code: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default"
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ACTIVE")
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DerivativeContractSpecModel(Base):
    __tablename__ = "derivative_contract_specs"
    __table_args__ = (
        CheckConstraint("contract_size > 0", name="ck_derivative_contract_size_positive"),
        CheckConstraint("tick_size > 0", name="ck_derivative_tick_size_positive"),
        CheckConstraint("tick_value > 0", name="ck_derivative_tick_value_positive"),
        CheckConstraint(
            "settlement_type IN ('cash', 'physical')",
            name="ck_derivative_settlement_type",
        ),
        CheckConstraint(
            "first_notice_date IS NULL OR first_notice_date <= expiry_date",
            name="ck_derivative_first_notice_before_expiry",
        ),
        CheckConstraint(
            "last_trade_date IS NULL OR last_trade_date <= expiry_date",
            name="ck_derivative_last_trade_before_expiry",
        ),
    )

    instrument_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("instrument_definitions.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    underlying_asset_id: Mapped[str] = mapped_column(
        String(160), ForeignKey("asset_definitions.asset_id", ondelete="RESTRICT"), nullable=False
    )
    contract_unit_code: Mapped[str] = mapped_column(
        String(64), ForeignKey("unit_definitions.code", ondelete="RESTRICT"), nullable=False
    )
    contract_size: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    tick_size: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    tick_value: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    expiry_date: Mapped[object] = mapped_column(Date, nullable=False)
    first_notice_date: Mapped[object | None] = mapped_column(Date, nullable=True)
    last_trade_date: Mapped[object | None] = mapped_column(Date, nullable=True)
    settlement_type: Mapped[str] = mapped_column(String(16), nullable=False)
    margin_currency_definition_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    delivery_grade: Mapped[str | None] = mapped_column(String(160), nullable=True)
    delivery_location: Mapped[str | None] = mapped_column(String(240), nullable=True)


class BondContractSpecModel(Base):
    __tablename__ = "bond_contract_specs"
    __table_args__ = (
        CheckConstraint("face_value_minor > 0", name="ck_bond_face_value_positive"),
        CheckConstraint("coupon_rate >= 0", name="ck_bond_coupon_rate_nonnegative"),
        CheckConstraint(
            "coupon_type IN ('fixed', 'floating', 'zero', 'inflation_linked')",
            name="ck_bond_coupon_type",
        ),
        CheckConstraint(
            "coupon_frequency IN (0, 1, 2, 4, 6, 12)",
            name="ck_bond_coupon_frequency",
        ),
        CheckConstraint("maturity_date > issue_date", name="ck_bond_maturity_after_issue"),
    )

    instrument_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("instrument_definitions.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    issuer_asset_id: Mapped[str] = mapped_column(
        String(160), ForeignKey("asset_definitions.asset_id", ondelete="RESTRICT"), nullable=False
    )
    currency_definition_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    face_value_minor: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    issue_date: Mapped[object] = mapped_column(Date, nullable=False)
    maturity_date: Mapped[object] = mapped_column(Date, nullable=False)
    coupon_type: Mapped[str] = mapped_column(String(24), nullable=False)
    coupon_rate: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    coupon_frequency: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_count_convention: Mapped[str] = mapped_column(String(32), nullable=False)
    seniority: Mapped[str] = mapped_column(String(64), nullable=False)


class PredictionContractSpecModel(Base):
    __tablename__ = "prediction_contract_specs"
    __table_args__ = (
        CheckConstraint("payout_minor > 0", name="ck_prediction_payout_positive"),
    )

    instrument_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("instrument_definitions.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    outcomes: Mapped[list] = mapped_column(JSON, nullable=False)
    resolution_source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    resolution_deadline: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    settlement_currency_definition_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payout_minor: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)


class ProviderSourceModel(Base):
    __tablename__ = "provider_sources"
    __table_args__ = (
        UniqueConstraint("provider_key", "terms_version", name="uq_provider_sources_key_terms"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    provider_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    license_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    license_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    terms_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rights_scope: Mapped[str] = mapped_column(String(80), nullable=False)
    geographic_coverage: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ACTIVE")
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MarketObservationModel(Base):
    __tablename__ = "market_observations"
    __table_args__ = (
        Index(
            "uq_market_observations_provider_record",
            "provider_source_id",
            "source_record_id",
            "observation_type",
            "instrument_id",
            unique=True,
        ),
        Index(
            "ix_market_observations_instrument_observed",
            "instrument_id",
            "observation_type",
            "observed_at",
        ),
        Index(
            "ix_market_observations_source_record",
            "provider_source_id",
            "source_record_id",
        ),
        CheckConstraint(
            "retrieved_at >= observed_at",
            name="ck_market_observations_retrieved_after_observed",
        ),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    instrument_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("instrument_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    observation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    unit_code: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("unit_definitions.code", ondelete="RESTRICT"), nullable=True
    )
    quote_currency_definition_id: Mapped[object | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("currency_definitions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    provider_source_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("provider_sources.id", ondelete="RESTRICT"), nullable=False
    )
    source_record_id: Mapped[str | None] = mapped_column(String(240), nullable=True)
    observed_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    market_session: Mapped[str | None] = mapped_column(String(64), nullable=True)
    methodology: Mapped[str | None] = mapped_column(String(240), nullable=True)
    license_reference: Mapped[str | None] = mapped_column(String(240), nullable=True)


class ForecastRecordModel(Base):
    __tablename__ = "forecast_records"
    __table_args__ = (
        CheckConstraint(
            "probability >= 0 AND probability <= 1",
            name="ck_forecast_records_probability_range",
        ),
        CheckConstraint(
            "horizon_end >= generated_at",
            name="ck_forecast_records_horizon_after_generation",
        ),
        Index("ix_forecast_records_target_horizon", "target_id", "horizon_end"),
    )

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    target_id: Mapped[str] = mapped_column(String(240), nullable=False)
    model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    probability: Mapped[object] = mapped_column(Numeric(asdecimal=True), nullable=False)
    generated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_end: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ForecastResolutionModel(Base):
    __tablename__ = "forecast_resolutions"
    __table_args__ = (
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 1)",
            name="ck_forecast_resolutions_score_range",
        ),
    )

    forecast_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("forecast_records.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    resolved_outcome: Mapped[str] = mapped_column(String(240), nullable=False)
    resolved_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    scoring_method: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[object | None] = mapped_column(Numeric(asdecimal=True), nullable=True)
    resolution_source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
