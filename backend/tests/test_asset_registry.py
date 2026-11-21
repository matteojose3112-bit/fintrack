from datetime import date
from decimal import Decimal
from fractions import Fraction
from uuid import uuid4

import pytest

from app.domain.asset_registry import (
    ASSET_DEFINITIONS,
    DEFAULT_ASSET_REGISTRY,
    DEFAULT_UNIT_REGISTRY,
    AssetDefinition,
    AssetRegistry,
    InstrumentDefinition,
    InstrumentIdentifier,
    UnitDefinition,
    UnitRegistry,
)


def test_troy_ounce_to_gram_conversion_is_exact():
    ratio = DEFAULT_UNIT_REGISTRY.conversion_ratio("troy_ounce", "gram")
    assert ratio == Fraction(311034768, 10000000)
    assert DEFAULT_UNIT_REGISTRY.convert_exact(
        Decimal("2"), "troy_ounce", "gram"
    ) == Fraction(622069536, 10000000)


def test_barrel_to_litre_conversion_is_exact():
    assert DEFAULT_UNIT_REGISTRY.conversion_ratio("barrel", "litre") == Fraction(
        158987294928, 1000000000
    )


def test_context_dependent_bushel_conversion_requires_contract_context():
    with pytest.raises(ValueError, match="requires instrument/commodity context"):
        DEFAULT_UNIT_REGISTRY.conversion_ratio("bushel", "metric_tonne")


def test_unit_registry_rejects_dimension_mismatch():
    with pytest.raises(ValueError, match="dimensions do not match"):
        DEFAULT_UNIT_REGISTRY.conversion_ratio("troy_ounce", "barrel")


def test_unit_registry_rejects_binary_float_quantities():
    with pytest.raises(TypeError, match="floating-point"):
        DEFAULT_UNIT_REGISTRY.convert_exact(1.5, "troy_ounce", "gram")


def test_default_global_asset_catalog_covers_multiple_commodity_families():
    classes = {asset.asset_class for asset in ASSET_DEFINITIONS}
    assert {
        "commodity", "equity_issuer", "fixed_income", "fund", "crypto_asset",
        "real_estate", "prediction_contract", "liability", "benchmark",
        "fx_pair", "private_equity", "derivative",
    } <= classes
    assert DEFAULT_ASSET_REGISTRY.get("commodity.gold").quantity_unit_code == "troy_ounce"
    assert DEFAULT_ASSET_REGISTRY.get("commodity.wti_crude_oil").quantity_unit_code == "barrel"
    assert DEFAULT_ASSET_REGISTRY.get("commodity.natural_gas").quantity_unit_code == "mmbtu"


def test_asset_class_vocabulary_is_open_and_extensible():
    custom = AssetDefinition(
        asset_id="environmental.blue_carbon_credit",
        asset_class="environmental_asset",
        asset_type="blue_carbon_credit",
        name="Blue carbon credit",
        quantity_unit_code="contract",
    )
    registry = AssetRegistry((custom,), DEFAULT_UNIT_REGISTRY)
    assert registry.by_class("environmental_asset") == (custom,)


def test_asset_registry_rejects_unknown_quantity_units():
    custom = AssetDefinition(
        asset_id="commodity.unknown",
        asset_class="commodity",
        asset_type="specialty",
        name="Unknown commodity",
        quantity_unit_code="unknown_unit",
    )
    with pytest.raises(ValueError, match="unsupported quantity unit"):
        AssetRegistry((custom,), DEFAULT_UNIT_REGISTRY)


def test_instrument_identifier_supports_time_bounded_namespaced_ids():
    identifier = InstrumentIdentifier(
        namespace="isin",
        value="US0378331005",
        source="official issuer filing",
        valid_from=date(1980, 12, 12),
    )
    instrument = InstrumentDefinition(
        instrument_id=uuid4(),
        instrument_type="equity_share",
        name="Example common stock",
        underlying_asset_id="issuer.example_corporation",
        quote_currency_code="USD",
        identifiers=(identifier,),
    )
    assert instrument.identifiers[0].namespace == "isin"


def test_instrument_types_are_open_for_futures_and_prediction_contracts():
    future = InstrumentDefinition(
        instrument_id=uuid4(),
        instrument_type="future",
        name="WTI crude oil futures contract",
        underlying_asset_id="commodity.wti_crude_oil",
        quote_currency_code="USD",
    )
    prediction = InstrumentDefinition(
        instrument_id=uuid4(),
        instrument_type="prediction_contract",
        name="Event outcome contract",
        underlying_asset_id="event.example_election",
        quote_currency_code="USD",
    )
    assert future.instrument_type == "future"
    assert prediction.instrument_type == "prediction_contract"


def test_instrument_identifier_rejects_inverted_validity_range():
    with pytest.raises(ValueError, match="validity range is inverted"):
        InstrumentIdentifier(
            namespace="figi",
            value="BBG000BLNNH6",
            source="test",
            valid_from=date(2026, 1, 1),
            valid_to=date(2025, 12, 31),
        )
