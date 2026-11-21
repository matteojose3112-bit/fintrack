"""PostgreSQL-only, license-aware ingestion of normalized provider observations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.domain.providers import (
    MarketDataRequest,
    ProviderAdapter,
    ProviderCoverageError,
    ProviderLicensePolicy,
    ProviderObservation,
)
from app.persistence.instrument_models import (
    InstrumentDefinitionModel,
    MarketObservationModel,
    ProviderSourceModel,
    UnitDefinitionModel,
)
from app.persistence.models import CurrencyDefinitionModel


class ProviderLicenseError(PermissionError):
    pass


class ProviderSourceUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IngestionResult:
    provider_key: str
    terms_version: str
    received: int
    inserted: int
    duplicates: int


def _validate_coverage(adapter: ProviderAdapter, request: MarketDataRequest) -> None:
    capabilities = adapter.capabilities
    if not set(request.observation_types).issubset(capabilities.data_types):
        raise ProviderCoverageError("provider does not support all requested observation types")
    if request.asset_class and request.asset_class not in capabilities.asset_classes:
        raise ProviderCoverageError("provider does not cover the requested asset class")
    if request.instrument_type and request.instrument_type not in capabilities.instrument_types:
        raise ProviderCoverageError("provider does not cover the requested instrument type")
    if request.region_code and not capabilities.global_region_coverage:
        if request.region_code not in capabilities.region_codes:
            raise ProviderCoverageError("provider has no declared coverage for the requested region")
    if request.venue_mic and request.venue_mic not in capabilities.venue_mics:
        raise ProviderCoverageError("provider has no declared coverage for the requested venue")
    if request.granularity == "realtime" and not capabilities.supports_realtime:
        raise ProviderCoverageError("provider does not supply real-time observations")
    if request.granularity == "intraday" and not capabilities.supports_intraday:
        raise ProviderCoverageError("provider does not supply intraday observations")


def _validate_license(
    source: ProviderSourceModel,
    adapter: ProviderAdapter,
    policy: ProviderLicensePolicy,
    purpose: str,
    region_code: str | None,
) -> None:
    capabilities = adapter.capabilities
    if source.status != "ACTIVE":
        raise ProviderSourceUnavailable("provider source is not active")
    if source.provider_key != capabilities.provider_key or source.provider_key != policy.provider_key:
        raise ProviderLicenseError("provider identity does not match registered terms")
    if source.terms_version != policy.terms_version:
        raise ProviderLicenseError("provider terms version does not match the stored source")
    if source.rights_scope != capabilities.rights_scope:
        raise ProviderLicenseError("provider rights scope does not match its registered capability")
    if source.rights_scope not in policy.allowed_purposes:
        raise ProviderLicenseError("stored provider rights scope is not permitted by the supplied terms")
    if purpose not in policy.allowed_purposes:
        raise ProviderLicenseError("requested purpose is not permitted by provider terms")
    coverage = source.geographic_coverage
    if policy.global_region_coverage:
        if not isinstance(coverage, dict) or coverage.get("global") is not True:
            raise ProviderLicenseError("stored provider source does not declare global coverage")
    else:
        if region_code is None:
            raise ProviderLicenseError("a region must be declared for region-scoped provider terms")
        if region_code not in policy.allowed_regions:
            raise ProviderLicenseError("provider license does not cover the requested region")
        source_regions = coverage.get("regions", []) if isinstance(coverage, dict) else coverage
        if not source_regions or region_code not in source_regions:
            raise ProviderLicenseError("stored provider coverage does not include the requested region")


def _validate_observations(
    observations: tuple[ProviderObservation, ...],
    request: MarketDataRequest,
) -> None:
    requested_ids = set(request.instrument_ids)
    requested_types = set(request.observation_types)
    for item in observations:
        if item.instrument_id not in requested_ids:
            raise ProviderCoverageError("provider returned an instrument outside the request")
        if item.observation_type not in requested_types:
            raise ProviderCoverageError("provider returned an observation type outside the request")
        if not request.start_at <= item.observed_at <= request.end_at:
            raise ProviderCoverageError("provider returned an observation outside the requested time range")


def ingest_market_observations(
    session_factory: Callable[[], Session],
    provider_source_id: UUID,
    adapter: ProviderAdapter,
    request: MarketDataRequest,
    license_policy: ProviderLicensePolicy,
    *,
    purpose: str,
) -> IngestionResult:
    """Fetch outside the write transaction, then persist one atomic idempotent batch."""
    _validate_coverage(adapter, request)
    if license_policy.provider_key != adapter.capabilities.provider_key:
        raise ProviderLicenseError("provider license policy belongs to another provider")
    if purpose not in license_policy.allowed_purposes:
        raise ProviderLicenseError("requested purpose is not permitted by provider terms")
    if not license_policy.global_region_coverage:
        if request.region_code is None:
            raise ProviderLicenseError("a region must be declared for region-scoped provider terms")
        if request.region_code not in license_policy.allowed_regions:
            raise ProviderLicenseError("provider license does not cover the requested region")

    with session_factory() as session:
        source = session.get(ProviderSourceModel, provider_source_id)
        if source is None:
            raise ProviderSourceUnavailable("provider source record was not found")
        _validate_license(
            source, adapter, license_policy, purpose, request.region_code
        )
        if session.bind.dialect.name != "postgresql":
            raise RuntimeError("market observation ingestion requires PostgreSQL")

    observations = tuple(adapter.fetch(request))
    _validate_observations(observations, request)

    inserted = 0
    with session_factory() as session:
        if session.bind.dialect.name != "postgresql":
            raise RuntimeError("market observation ingestion requires PostgreSQL")
        with session.begin():
            source = session.get(ProviderSourceModel, provider_source_id)
            if source is None:
                raise ProviderSourceUnavailable("provider source record was not found")
            _validate_license(
                source, adapter, license_policy, purpose, request.region_code
            )

            instrument_ids = {item.instrument_id for item in observations}
            existing_instruments = set(
                session.scalars(
                    select(InstrumentDefinitionModel.id).where(
                        InstrumentDefinitionModel.id.in_(instrument_ids)
                    )
                ).all()
            )
            if existing_instruments != instrument_ids:
                raise ProviderCoverageError("provider returned an unknown instrument")

            for item in observations:
                if item.unit_code is not None:
                    unit = session.scalars(
                        select(UnitDefinitionModel).where(
                            UnitDefinitionModel.code == item.unit_code
                        )
                    ).first()
                    if unit is None:
                        raise ProviderCoverageError(
                            f"provider returned an unknown quantity unit: {item.unit_code}"
                        )

                currency_definition_id = None
                if item.quote_currency_code is not None:
                    currency = session.scalars(
                        select(CurrencyDefinitionModel)
                        .where(
                            CurrencyDefinitionModel.code == item.quote_currency_code,
                            CurrencyDefinitionModel.registry_list == "one",
                            CurrencyDefinitionModel.withdrawal_key == "",
                            CurrencyDefinitionModel.fund.is_(False),
                        )
                        .order_by(CurrencyDefinitionModel.published_on.desc())
                        .limit(1)
                    ).first()
                    if currency is None:
                        raise ProviderCoverageError(
                            f"provider returned an unsupported quote currency: {item.quote_currency_code}"
                        )
                    currency_definition_id = currency.id

                statement = (
                    pg_insert(MarketObservationModel)
                    .values(
                        id=uuid4(),
                        instrument_id=item.instrument_id,
                        observation_type=item.observation_type,
                        value=item.value,
                        unit_code=item.unit_code,
                        quote_currency_definition_id=currency_definition_id,
                        provider_source_id=provider_source_id,
                        source_record_id=item.source_record_id,
                        observed_at=item.observed_at,
                        retrieved_at=item.retrieved_at,
                        market_session=item.market_session,
                        methodology=item.methodology,
                        license_reference=license_policy.terms_version,
                    )
                    .on_conflict_do_nothing(
                        index_elements=[
                            MarketObservationModel.provider_source_id,
                            MarketObservationModel.source_record_id,
                            MarketObservationModel.observation_type,
                            MarketObservationModel.instrument_id,
                        ]
                    )
                    .returning(MarketObservationModel.id)
                )
                result = session.execute(statement)
                inserted += 1 if result.scalar_one_or_none() is not None else 0

    return IngestionResult(
        provider_key=adapter.capabilities.provider_key,
        terms_version=license_policy.terms_version,
        received=len(observations),
        inserted=inserted,
        duplicates=len(observations) - inserted,
    )
