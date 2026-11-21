from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.asset_registry import (
    BondContractSpec,
    DerivativeContractSpec,
    InstrumentListing,
    MarketVenue,
    PredictionContractSpec,
)


def test_market_venue_uses_mic_and_iana_timezone():
    venue = MarketVenue(
        mic="XNAS",
        name="Nasdaq",
        country_code="US",
        timezone="America/New_York",
        venue_type="exchange",
    )
    assert venue.mic == "XNAS"


def test_market_venue_rejects_invalid_timezone():
    with pytest.raises(ValueError, match="IANA timezone"):
        MarketVenue(
            mic="XNAS",
            name="Nasdaq",
            country_code="US",
            timezone="Mars/Phobos",
            venue_type="exchange",
        )


def test_listing_ticker_is_scoped_to_venue_not_globally_unique():
    instrument_id = uuid4()
    nyse = InstrumentListing(
        instrument_id=instrument_id,
        venue_mic="XNYS",
        symbol="ABC",
        quote_currency_code="USD",
        active_from=date(2020, 1, 1),
    )
    nasdaq = InstrumentListing(
        instrument_id=instrument_id,
        venue_mic="XNAS",
        symbol="ABC",
        quote_currency_code="USD",
        active_from=date(2021, 1, 1),
    )
    assert nyse.symbol == nasdaq.symbol
    assert nyse.venue_mic != nasdaq.venue_mic


def test_listing_rejects_inverted_active_dates():
    with pytest.raises(ValueError, match="active date range is inverted"):
        InstrumentListing(
            instrument_id=uuid4(),
            venue_mic="XNAS",
            symbol="ABC",
            quote_currency_code="USD",
            active_from=date(2025, 1, 1),
            active_to=date(2024, 12, 31),
        )


def test_derivative_contract_requires_explicit_unit_size_ticks_and_lifecycle():
    spec = DerivativeContractSpec(
        instrument_id=uuid4(),
        underlying_asset_id="commodity.wti_crude_oil",
        contract_unit_code="barrel",
        contract_size=Decimal("1000"),
        tick_size=Decimal("0.01"),
        tick_value=Decimal("10"),
        expiry_date=date(2027, 3, 20),
        first_notice_date=date(2027, 2, 20),
        last_trade_date=date(2027, 3, 18),
        settlement_type="physical",
        margin_currency_code="USD",
        delivery_grade="WTI",
        delivery_location="Cushing, Oklahoma",
    )
    assert spec.contract_size == Decimal("1000")


def test_derivative_contract_rejects_inconsistent_notice_and_trade_dates():
    with pytest.raises(ValueError, match="first notice date cannot follow last trade date"):
        DerivativeContractSpec(
            instrument_id=uuid4(),
            underlying_asset_id="commodity.gold",
            contract_unit_code="troy_ounce",
            contract_size=Decimal("100"),
            tick_size=Decimal("0.1"),
            tick_value=Decimal("10"),
            expiry_date=date(2027, 3, 20),
            first_notice_date=date(2027, 3, 15),
            last_trade_date=date(2027, 3, 10),
            settlement_type="physical",
            margin_currency_code="USD",
        )


def test_bond_contract_retains_coupon_and_day_count_terms():
    spec = BondContractSpec(
        instrument_id=uuid4(),
        issuer_asset_id="issuer.example_public_company",
        currency_code="USD",
        face_value=Decimal("1000"),
        issue_date=date(2025, 1, 1),
        maturity_date=date(2030, 1, 1),
        coupon_type="fixed",
        coupon_rate=Decimal("0.045"),
        coupon_frequency=2,
        day_count_convention="30/360",
        seniority="senior_unsecured",
    )
    assert spec.coupon_frequency == 2


def test_prediction_contract_requires_aware_deadline_and_resolution_source():
    spec = PredictionContractSpec(
        instrument_id=uuid4(),
        event_id="election-2028",
        question="Will candidate A win?",
        outcomes=("YES", "NO"),
        resolution_source_url="https://example.gov/results",
        resolution_deadline=datetime(2028, 11, 10, tzinfo=timezone.utc),
        settlement_currency_code="USD",
        payout_per_contract=Decimal("1"),
    )
    assert len(spec.outcomes) == 2


def test_prediction_contract_rejects_naive_deadline_and_duplicate_outcomes():
    with pytest.raises(ValueError, match="timezone-aware"):
        PredictionContractSpec(
            instrument_id=uuid4(),
            event_id="event-1",
            question="Will event occur?",
            outcomes=("YES", "NO"),
            resolution_source_url="https://example.org/rules",
            resolution_deadline=datetime(2028, 11, 10),
            settlement_currency_code="USD",
            payout_per_contract=Decimal("1"),
        )

    with pytest.raises(ValueError, match="outcomes must be unique"):
        PredictionContractSpec(
            instrument_id=uuid4(),
            event_id="event-2",
            question="Will event occur?",
            outcomes=("YES", "YES"),
            resolution_source_url="https://example.org/rules",
            resolution_deadline=datetime(2028, 11, 10, tzinfo=timezone.utc),
            settlement_currency_code="USD",
            payout_per_contract=Decimal("1"),
        )
