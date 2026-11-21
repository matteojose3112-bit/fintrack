from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from app.domain.providers import MarketDataRequest, ProviderAdapterError, ProviderCoverageError
from app.providers.ecb_reference_fx import ECBReferenceFXAdapter, ECBSeriesMapping


CSV = """KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE
D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-11-16,1.1580
D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-11-17,1.1605
"""


def make_request(instrument_id, **overrides):
    start = datetime(2026, 11, 16, tzinfo=timezone.utc)
    end = datetime(2026, 11, 17, 23, 59, tzinfo=timezone.utc)
    values = {
        "instrument_ids": (instrument_id,),
        "observation_types": ("reference_rate",),
        "start_at": start,
        "end_at": end,
        "asset_class": "fx_pair",
        "instrument_type": "spot_fx_pair",
        "granularity": "daily",
    }
    values.update(overrides)
    return MarketDataRequest(**values)


def test_ecb_adapter_parses_exact_daily_reference_fx_and_provenance():
    instrument_id = uuid4()
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.path.endswith("/data/EXR/D.USD.EUR.SP00.A")
        assert request.url.params["startPeriod"] == "2026-11-16"
        assert request.url.params["endPeriod"] == "2026-11-17"
        assert request.url.params["format"] == "csvdata"
        return httpx.Response(200, text=CSV, headers={"Content-Type": "text/csv"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = ECBReferenceFXAdapter(
        (ECBSeriesMapping(instrument_id, "USD"),), client=client
    )
    observations = tuple(adapter.fetch(make_request(instrument_id)))

    assert len(observations) == 2
    assert observations[0].value == Decimal("1.1580")
    assert observations[0].quote_currency_code == "USD"
    assert observations[0].instrument_id == instrument_id
    assert observations[0].observed_at == datetime(2026, 11, 16, tzinfo=timezone.utc)
    assert observations[0].source_record_id.endswith("2026-11-16")
    assert "not an executable bid/ask quote" in observations[0].methodology
    assert len(requests) == 1
    client.close()


def test_ecb_adapter_marks_service_unavailability_retryable():
    instrument_id = uuid4()

    def handler(request):
        return httpx.Response(503, text="temporarily unavailable")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = ECBReferenceFXAdapter(
        (ECBSeriesMapping(instrument_id, "USD"),), client=client
    )
    with pytest.raises(ProviderAdapterError) as error:
        tuple(adapter.fetch(make_request(instrument_id)))
    assert error.value.retryable is True
    client.close()


def test_ecb_adapter_rejects_unknown_instrument_mapping():
    adapter = ECBReferenceFXAdapter((ECBSeriesMapping(uuid4(), "USD"),))
    with pytest.raises(ProviderCoverageError, match="no configured series"):
        tuple(adapter.fetch(make_request(uuid4())))
    adapter.close()


def test_ecb_adapter_rejects_intraday_or_non_fx_requests():
    instrument_id = uuid4()
    adapter = ECBReferenceFXAdapter((ECBSeriesMapping(instrument_id, "USD"),))
    with pytest.raises(ProviderCoverageError, match="daily"):
        tuple(adapter.fetch(make_request(instrument_id, granularity="intraday")))
    adapter.close()


def test_ecb_adapter_rejects_invalid_decimal_observation():
    instrument_id = uuid4()
    invalid_csv = """TIME_PERIOD,OBS_VALUE
2026-11-17,not-a-number
"""

    def handler(request):
        return httpx.Response(200, text=invalid_csv)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = ECBReferenceFXAdapter(
        (ECBSeriesMapping(instrument_id, "USD"),), client=client
    )
    with pytest.raises(ProviderAdapterError) as error:
        tuple(adapter.fetch(make_request(instrument_id)))
    assert error.value.retryable is False
    client.close()
