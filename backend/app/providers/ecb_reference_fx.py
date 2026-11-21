"""ECB daily EUR reference-rate adapter.

The adapter is deliberately narrow: it does not provide executable FX quotes,
bid/ask spreads, or every currency pair. Internal instrument IDs must be mapped
explicitly to an ECB EUR-base series.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, time, timezone
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Iterable
from uuid import UUID

import httpx

from app.domain.providers import (
    MarketDataRequest,
    ProviderAdapterError,
    ProviderCapabilities,
    ProviderCoverageError,
    ProviderObservation,
)


@dataclass(frozen=True, slots=True)
class ECBSeriesMapping:
    instrument_id: UUID
    quote_currency_code: str

    def __post_init__(self) -> None:
        import re

        if not isinstance(self.instrument_id, UUID):
            raise TypeError("ECB mapping instrument_id must be UUID")
        if not re.fullmatch(r"[A-Z]{3}", self.quote_currency_code):
            raise ValueError("ECB quote currency must be ISO alpha-3")
        if self.quote_currency_code == "EUR":
            raise ValueError("EUR/EUR is not a valid FX reference pair")


class ECBReferenceFXAdapter:
    provider_key = "ecb_data_portal"
    base_url = "https://data-api.ecb.europa.eu/service"

    def __init__(
        self,
        mappings: tuple[ECBSeriesMapping, ...],
        *,
        client: httpx.Client | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        if not mappings:
            raise ValueError("at least one ECB FX series mapping is required")
        ids = [item.instrument_id for item in mappings]
        currencies = [item.quote_currency_code for item in mappings]
        if len(ids) != len(set(ids)):
            raise ValueError("ECB instrument mappings must be unique")
        if len(currencies) != len(set(currencies)):
            raise ValueError("ECB quote currencies must be unique")
        self._mappings = {item.instrument_id: item for item in mappings}
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._owns_client = client is None
        self._capabilities = ProviderCapabilities(
            provider_key=self.provider_key,
            data_types=("reference_rate",),
            asset_classes=("fx_pair",),
            instrument_types=("spot_fx_pair",),
            global_region_coverage=True,
            delay_class="end_of_day",
            supports_historical=True,
            supports_intraday=False,
            supports_realtime=False,
            rights_scope="internal_research",
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def fetch(self, request: MarketDataRequest) -> Iterable[ProviderObservation]:
        if request.asset_class != "fx_pair" or request.instrument_type != "spot_fx_pair":
            raise ProviderCoverageError("ECB adapter only supports spot FX pair instruments")
        if set(request.observation_types) != {"reference_rate"}:
            raise ProviderCoverageError("ECB adapter only supplies daily reference_rate observations")
        if request.granularity != "daily":
            raise ProviderCoverageError("ECB reference rates are daily observations")
        if request.venue_mic is not None:
            raise ProviderCoverageError("ECB reference rates are not exchange-listed venue quotes")

        start_period = request.start_at.astimezone(timezone.utc).date().isoformat()
        end_period = request.end_at.astimezone(timezone.utc).date().isoformat()
        observations: list[ProviderObservation] = []

        for instrument_id in request.instrument_ids:
            mapping = self._mappings.get(instrument_id)
            if mapping is None:
                raise ProviderCoverageError(
                    f"ECB adapter has no configured series for instrument {instrument_id}"
                )
            series_key = f"D.{mapping.quote_currency_code}.EUR.SP00.A"
            url = f"{self.base_url}/data/EXR/{series_key}"
            try:
                response = self._client.get(
                    url,
                    params={
                        "startPeriod": start_period,
                        "endPeriod": end_period,
                        "format": "csvdata",
                    },
                    headers={"Accept": "text/csv"},
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                retryable = exc.response.status_code == 429 or exc.response.status_code >= 500
                raise ProviderAdapterError(
                    f"ECB Data Portal returned HTTP {exc.response.status_code}",
                    retryable=retryable,
                ) from exc
            except httpx.RequestError as exc:
                raise ProviderAdapterError(
                    f"ECB Data Portal request failed: {exc}",
                    retryable=True,
                ) from exc

            try:
                rows = csv.DictReader(StringIO(response.text))
                for row in rows:
                    period = row.get("TIME_PERIOD") or row.get("TIME_PERIOD_START")
                    raw_value = row.get("OBS_VALUE")
                    if not period or raw_value in (None, "", "."):
                        continue
                    value = Decimal(raw_value)
                    if not value.is_finite():
                        raise ValueError("non-finite ECB observation")
                    period_date = datetime.strptime(period, "%Y-%m-%d").date()
                    observed_at = datetime.combine(
                        period_date, time.min, tzinfo=timezone.utc
                    )
                    observations.append(
                        ProviderObservation(
                            source_record_id=(
                                f"ECB:EXR:{series_key}:{period_date.isoformat()}"
                            ),
                            instrument_id=instrument_id,
                            observation_type="reference_rate",
                            value=value,
                            observed_at=observed_at,
                            retrieved_at=datetime.now(timezone.utc),
                            quote_currency_code=mapping.quote_currency_code,
                            market_session="ecb_daily_reference",
                            methodology=(
                                "ECB daily reference rate; quote currency units per EUR; "
                                "date-level observation represented at 00:00 UTC; "
                                "not an executable bid/ask quote"
                            ),
                        )
                    )
            except (csv.Error, ValueError, InvalidOperation, KeyError) as exc:
                raise ProviderAdapterError(
                    f"ECB Data Portal returned an invalid CSV observation: {exc}",
                    retryable=False,
                ) from exc

        return tuple(observations)

