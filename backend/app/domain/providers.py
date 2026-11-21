"""Provider-neutral contracts for licensed global financial data adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Protocol
from uuid import UUID
import re


_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_REGION = re.compile(r"^[A-Z]{2}$")
_MIC = re.compile(r"^[A-Z0-9]{4}$")


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    provider_key: str
    data_types: tuple[str, ...]
    asset_classes: tuple[str, ...]
    instrument_types: tuple[str, ...]
    region_codes: tuple[str, ...] = ()
    venue_mics: tuple[str, ...] = ()
    global_region_coverage: bool = False
    delay_class: str = "historical"
    supports_historical: bool = True
    supports_intraday: bool = False
    supports_realtime: bool = False
    rights_scope: str = "internal_research"

    def __post_init__(self) -> None:
        if not _CODE.fullmatch(self.provider_key):
            raise ValueError("provider_key must be a lowercase identifier")
        if not self.data_types or any(not _CODE.fullmatch(item) for item in self.data_types):
            raise ValueError("provider must declare supported data types")
        if not self.asset_classes or any(not _CODE.fullmatch(item) for item in self.asset_classes):
            raise ValueError("provider must declare supported asset classes")
        if any(not _CODE.fullmatch(item) for item in self.instrument_types):
            raise ValueError("instrument types must be lowercase identifiers")
        if any(not _REGION.fullmatch(item) for item in self.region_codes):
            raise ValueError("region codes must be ISO alpha-2")
        if any(not _MIC.fullmatch(item) for item in self.venue_mics):
            raise ValueError("venue coverage must use four-character MICs")
        if self.delay_class not in {"real_time", "delayed", "end_of_day", "historical", "indicative"}:
            raise ValueError("unsupported provider delay class")
        if not _CODE.fullmatch(self.rights_scope):
            raise ValueError("rights_scope must be a lowercase identifier")


@dataclass(frozen=True, slots=True)
class MarketDataRequest:
    instrument_ids: tuple[UUID, ...]
    observation_types: tuple[str, ...]
    start_at: datetime
    end_at: datetime
    asset_class: str | None = None
    instrument_type: str | None = None
    region_code: str | None = None
    venue_mic: str | None = None
    granularity: str = "daily"

    def __post_init__(self) -> None:
        if not self.instrument_ids or any(not isinstance(item, UUID) for item in self.instrument_ids):
            raise ValueError("request requires one or more instrument UUIDs")
        if len(set(self.instrument_ids)) != len(self.instrument_ids):
            raise ValueError("request instrument IDs must be unique")
        if not self.observation_types or any(not _CODE.fullmatch(item) for item in self.observation_types):
            raise ValueError("request requires valid observation types")
        if len(set(self.observation_types)) != len(self.observation_types):
            raise ValueError("request observation types must be unique")
        for name in ("start_at", "end_at"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.end_at < self.start_at:
            raise ValueError("request end_at cannot precede start_at")
        if self.asset_class is not None and not _CODE.fullmatch(self.asset_class):
            raise ValueError("asset_class must be a lowercase identifier")
        if self.instrument_type is not None and not _CODE.fullmatch(self.instrument_type):
            raise ValueError("instrument_type must be a lowercase identifier")
        if self.region_code is not None and not _REGION.fullmatch(self.region_code):
            raise ValueError("region_code must be ISO alpha-2")
        if self.venue_mic is not None and not _MIC.fullmatch(self.venue_mic):
            raise ValueError("venue_mic must be a four-character MIC")
        if not _CODE.fullmatch(self.granularity):
            raise ValueError("granularity must be a lowercase identifier")


@dataclass(frozen=True, slots=True)
class ProviderObservation:
    source_record_id: str
    instrument_id: UUID
    observation_type: str
    value: Decimal
    observed_at: datetime
    retrieved_at: datetime
    unit_code: str | None = None
    quote_currency_code: str | None = None
    market_session: str | None = None
    methodology: str | None = None

    def __post_init__(self) -> None:
        if not self.source_record_id.strip():
            raise ValueError("provider source record ID is required for deduplication")
        if not isinstance(self.instrument_id, UUID):
            raise TypeError("instrument_id must be UUID")
        if not _CODE.fullmatch(self.observation_type):
            raise ValueError("observation_type must be a lowercase identifier")
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise ValueError("provider values must be finite Decimal values")
        for name in ("observed_at", "retrieved_at"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.retrieved_at < self.observed_at:
            raise ValueError("retrieved_at cannot precede observed_at")
        if self.unit_code is not None and not _CODE.fullmatch(self.unit_code):
            raise ValueError("unit_code must be a lowercase identifier")
        if self.quote_currency_code is not None and not re.fullmatch(
            r"[A-Z]{3}", self.quote_currency_code
        ):
            raise ValueError("quote currency must be ISO alpha-3")


@dataclass(frozen=True, slots=True)
class ProviderLicensePolicy:
    provider_key: str
    terms_version: str
    allowed_purposes: tuple[str, ...]
    allowed_regions: tuple[str, ...] = ()
    global_region_coverage: bool = False
    retention_days: int | None = None
    attribution_required: bool = True
    redistribution_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.provider_key.strip() or not self.terms_version.strip():
            raise ValueError("provider and terms version are required")
        if not self.allowed_purposes or any(not item.strip() for item in self.allowed_purposes):
            raise ValueError("license policy must declare allowed purposes")
        if any(not _REGION.fullmatch(item) for item in self.allowed_regions):
            raise ValueError("license regions must be ISO alpha-2")
        if self.retention_days is not None and self.retention_days < 1:
            raise ValueError("retention_days must be positive")


class ProviderAdapter(Protocol):
    @property
    def capabilities(self) -> ProviderCapabilities:
        ...

    def fetch(self, request: MarketDataRequest) -> Iterable[ProviderObservation]:
        ...


class ProviderAdapterError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class ProviderCoverageError(ValueError):
    pass


class ProviderRegistry:
    """Explicit registry; no dynamic imports or implicit provider selection."""

    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    @property
    def provider_keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def register(self, adapter: ProviderAdapter) -> None:
        key = adapter.capabilities.provider_key
        if key in self._adapters:
            raise ValueError(f"provider already registered: {key}")
        self._adapters[key] = adapter

    def get(self, provider_key: str) -> ProviderAdapter:
        try:
            return self._adapters[provider_key]
        except KeyError as exc:
            raise ValueError(f"provider is not registered: {provider_key}") from exc

    def supporting(self, request: MarketDataRequest) -> tuple[ProviderAdapter, ...]:
        supported: list[ProviderAdapter] = []
        for adapter in self._adapters.values():
            capabilities = adapter.capabilities
            if not set(request.observation_types).issubset(capabilities.data_types):
                continue
            if request.asset_class and request.asset_class not in capabilities.asset_classes:
                continue
            if request.instrument_type and request.instrument_type not in capabilities.instrument_types:
                continue
            if request.region_code and not capabilities.global_region_coverage:
                if request.region_code not in capabilities.region_codes:
                    continue
            if request.venue_mic and request.venue_mic not in capabilities.venue_mics:
                continue
            if request.granularity == "realtime" and not capabilities.supports_realtime:
                continue
            if request.granularity == "intraday" and not capabilities.supports_intraday:
                continue
            supported.append(adapter)
        return tuple(sorted(supported, key=lambda item: item.capabilities.provider_key))
