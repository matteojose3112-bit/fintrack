from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.market_data import ForecastRecord, ForecastResolution, MarketObservation


def test_market_observation_retains_source_and_observation_retrieval_times():
    observed = datetime(2026, 11, 17, 14, 30, tzinfo=timezone.utc)
    record = MarketObservation(
        observation_id=uuid4(),
        instrument_id=uuid4(),
        observation_type="last_price",
        value=Decimal("72.15"),
        source_id="provider-x:record-123",
        observed_at=observed,
        retrieved_at=observed + timedelta(seconds=3),
        quote_currency_code="USD",
        market_session="regular",
        methodology="unadjusted_close",
    )
    assert record.retrieved_at > record.observed_at


def test_market_observation_allows_exact_negative_market_values():
    observed = datetime(2026, 11, 17, 14, 30, tzinfo=timezone.utc)
    record = MarketObservation(
        observation_id=uuid4(),
        instrument_id=uuid4(),
        observation_type="settlement_price",
        value=Decimal("-3.25"),
        source_id="exchange-settlement",
        observed_at=observed,
        retrieved_at=observed,
        quote_currency_code="USD",
    )
    assert record.value == Decimal("-3.25")


def test_market_observation_rejects_naive_timestamps_and_float_values():
    observed = datetime(2026, 11, 17, 14, 30, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="observed_at must be timezone-aware"):
        MarketObservation(
            observation_id=uuid4(),
            instrument_id=uuid4(),
            observation_type="last_price",
            value=Decimal("1"),
            source_id="provider",
            observed_at=datetime(2026, 11, 17, 14, 30),
            retrieved_at=observed,
        )
    with pytest.raises(ValueError, match="finite Decimal"):
        MarketObservation(
            observation_id=uuid4(),
            instrument_id=uuid4(),
            observation_type="last_price",
            value=1.25,
            source_id="provider",
            observed_at=observed,
            retrieved_at=observed,
        )


def test_forecast_record_is_separate_probability_with_horizon_and_evidence():
    generated = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
    forecast = ForecastRecord(
        forecast_id=uuid4(),
        target_id="macro.us.inflation.next_release",
        model_id="aurelius-macro",
        model_version="0.1.0",
        probability=Decimal("0.72"),
        generated_at=generated,
        horizon_end=generated + timedelta(days=30),
        evidence_ids=("source:fred-series", "source:release-calendar"),
    )
    assert forecast.probability == Decimal("0.72")
    assert len(forecast.evidence_ids) == 2


def test_forecast_record_rejects_float_probability_and_invalid_range():
    generated = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="finite Decimal"):
        ForecastRecord(
            forecast_id=uuid4(),
            target_id="target",
            model_id="model",
            model_version="1",
            probability=0.5,
            generated_at=generated,
            horizon_end=generated,
        )
    with pytest.raises(ValueError, match="between zero and one"):
        ForecastRecord(
            forecast_id=uuid4(),
            target_id="target",
            model_id="model",
            model_version="1",
            probability=Decimal("1.01"),
            generated_at=generated,
            horizon_end=generated,
        )


def test_forecast_resolution_is_separate_and_validates_score_and_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        ForecastResolution(
            forecast_id=uuid4(),
            resolved_outcome="YES",
            resolved_at=datetime(2026, 11, 17),
            scoring_method="brier",
        )

    with pytest.raises(ValueError, match="between zero and one"):
        ForecastResolution(
            forecast_id=uuid4(),
            resolved_outcome="YES",
            resolved_at=datetime(2026, 11, 17, tzinfo=timezone.utc),
            scoring_method="brier",
            score=Decimal("1.5"),
        )
