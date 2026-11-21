from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.providers import (
    MarketDataRequest,
    ProviderAdapterError,
    ProviderCapabilities,
    ProviderLicensePolicy,
    ProviderObservation,
    ProviderRegistry,
)


class FakeAdapter:
    def __init__(self, capabilities):
        self._capabilities = capabilities

    @property
    def capabilities(self):
        return self._capabilities

    def fetch(self, request):
        return ()


def make_capabilities(**overrides):
    values = {
        "provider_key": "test_provider",
        "data_types": ("last_price", "volume"),
        "asset_classes": ("equity",),
        "instrument_types": ("equity_share",),
        "region_codes": ("US",),
        "venue_mics": ("XNAS",),
        "delay_class": "delayed",
        "supports_historical": True,
        "supports_intraday": True,
        "supports_realtime": True,
        "rights_scope": "internal_research",
    }
    values.update(overrides)
    return ProviderCapabilities(**values)


def make_request(**overrides):
    now = datetime(2026, 11, 17, 15, 0, tzinfo=timezone.utc)
    values = {
        "instrument_ids": (uuid4(),),
        "observation_types": ("last_price",),
        "start_at": now,
        "end_at": now,
        "asset_class": "equity",
        "instrument_type": "equity_share",
        "region_code": "US",
        "venue_mic": "XNAS",
        "granularity": "realtime",
    }
    values.update(overrides)
    return MarketDataRequest(**values)


def test_provider_registry_selects_only_explicitly_supported_coverage():
    registry = ProviderRegistry()
    registry.register(FakeAdapter(make_capabilities()))
    registry.register(
        FakeAdapter(
            make_capabilities(
                provider_key="uk_provider",
                region_codes=("GB",),
                venue_mics=("XLON",),
                supports_realtime=False,
            )
        )
    )
    result = registry.supporting(make_request())
    assert [item.capabilities.provider_key for item in result] == ["test_provider"]


def test_provider_registry_does_not_assume_empty_region_means_global():
    registry = ProviderRegistry()
    registry.register(FakeAdapter(make_capabilities(region_codes=())))
    assert registry.supporting(make_request(region_code="US")) == ()


def test_provider_registry_respects_data_type_and_realtime_capabilities():
    registry = ProviderRegistry()
    registry.register(
        FakeAdapter(make_capabilities(supports_realtime=False))
    )
    assert registry.supporting(make_request()) == ()
    assert registry.supporting(make_request(granularity="daily"))


def test_provider_registry_rejects_duplicate_provider_key():
    registry = ProviderRegistry()
    adapter = FakeAdapter(make_capabilities())
    registry.register(adapter)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(adapter)


def test_market_data_request_requires_aware_ordered_times_and_unique_ids():
    now = datetime(2026, 11, 17, 15, 0, tzinfo=timezone.utc)
    instrument_id = uuid4()
    with pytest.raises(ValueError, match="unique"):
        MarketDataRequest(
            instrument_ids=(instrument_id, instrument_id),
            observation_types=("last_price",),
            start_at=now,
            end_at=now,
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        MarketDataRequest(
            instrument_ids=(uuid4(),),
            observation_types=("last_price",),
            start_at=datetime(2026, 11, 17),
            end_at=now,
        )


def test_provider_observation_requires_exact_decimal_and_source_record_id():
    now = datetime(2026, 11, 17, 15, 0, tzinfo=timezone.utc)
    observation = ProviderObservation(
        source_record_id="source-row-1",
        instrument_id=uuid4(),
        observation_type="last_price",
        value=Decimal("12.345"),
        observed_at=now,
        retrieved_at=now,
        quote_currency_code="USD",
    )
    assert observation.value == Decimal("12.345")
    with pytest.raises(ValueError, match="finite Decimal"):
        ProviderObservation(
            source_record_id="source-row-2",
            instrument_id=uuid4(),
            observation_type="last_price",
            value=12.345,
            observed_at=now,
            retrieved_at=now,
        )


def test_provider_license_policy_requires_explicit_purposes_and_regions():
    policy = ProviderLicensePolicy(
        provider_key="market_data_x",
        terms_version="2026-01",
        allowed_purposes=("internal_research", "derived_analytics"),
        allowed_regions=("US", "CA"),
        retention_days=365,
        attribution_required=True,
        redistribution_allowed=False,
    )
    assert policy.redistribution_allowed is False
    with pytest.raises(ValueError, match="allowed purposes"):
        ProviderLicensePolicy(
            provider_key="market_data_x",
            terms_version="2026-01",
            allowed_purposes=(),
        )


def test_provider_adapter_error_exposes_retryability_without_hiding_reason():
    error = ProviderAdapterError("rate limited", retryable=True)
    assert error.retryable is True
    assert str(error) == "rate limited"



def test_global_provider_coverage_must_be_explicit():
    registry = ProviderRegistry()
    registry.register(
        FakeAdapter(
            make_capabilities(
                provider_key="global_provider",
                region_codes=(),
                venue_mics=("XNAS",),
                global_region_coverage=True,
            )
        )
    )
    assert len(registry.supporting(make_request(region_code="CA"))) == 1
