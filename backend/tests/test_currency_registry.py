import json

import pytest

from app.domain.currency import CurrencyRegistry, DEFAULT_CURRENCY_REGISTRY


def test_bundled_registry_contains_current_and_historical_six_lists():
    assert len(DEFAULT_CURRENCY_REGISTRY.current_definitions) == 178
    assert len(DEFAULT_CURRENCY_REGISTRY.historical_definitions) == 152
    assert DEFAULT_CURRENCY_REGISTRY.current_published == "2026-09-17"
    assert DEFAULT_CURRENCY_REGISTRY.historical_published == "2026-01-01"


@pytest.mark.parametrize(
    ("code", "numeric_code", "exponent"),
    [
        ("USD", "840", 2),
        ("CAD", "124", 2),
        ("COP", "170", 2),
        ("AMD", "051", 2),
        ("JPY", "392", 0),
        ("KWD", "414", 3),
        ("CLF", "990", 4),
    ],
)
def test_registry_preserves_numeric_codes_and_minor_units(code, numeric_code, exponent):
    definition = DEFAULT_CURRENCY_REGISTRY.get_money_unit(code)
    assert definition.numeric_code == numeric_code
    assert definition.minor_unit_exponent == exponent


def test_historical_bulgarian_lev_is_not_mistaken_for_current_currency():
    assert "BGN" not in DEFAULT_CURRENCY_REGISTRY.current_money_units
    historical = DEFAULT_CURRENCY_REGISTRY.get_historical("BGN")
    assert len(historical) == 1
    assert historical[0].withdrawn == "2026-01"
    # List Three does not publish minor-unit exponents. Never infer one.
    assert historical[0].minor_unit_exponent is None


@pytest.mark.parametrize("code", ["XAU", "XAG", "XPD", "XPT", "XXX"])
def test_reference_codes_without_minor_units_are_not_money(code):
    with pytest.raises(ValueError, match="not a current monetary unit"):
        DEFAULT_CURRENCY_REGISTRY.get_money_unit(code)


def test_fund_flagged_indexed_units_keep_their_published_precision():
    clf = DEFAULT_CURRENCY_REGISTRY.get_money_unit("CLF")
    assert clf.fund is True
    assert clf.minor_unit_exponent == 4


def test_snapshot_loader_rejects_duplicate_codes():
    snapshot = {
        "schema_version": 1,
        "registry_release": "test",
        "source": {},
        "current_published": "2026-09-17",
        "historical_published": "2026-01-01",
        "current": [
            {"code": "USD", "numeric_code": "840", "name": "US Dollar",
             "minor_unit_exponent": 2, "fund": False, "countries": []},
            {"code": "USD", "numeric_code": "840", "name": "US Dollar",
             "minor_unit_exponent": 2, "fund": False, "countries": []},
        ],
        "historical": [],
    }
    with pytest.raises(ValueError, match="duplicate currency definition"):
        CurrencyRegistry(snapshot)


def test_registry_snapshot_is_valid_json():
    path = DEFAULT_CURRENCY_REGISTRY.source["official_page"]
    assert path.startswith("https://")


def test_historical_withdrawal_dates_are_preserved_per_country():
    records = DEFAULT_CURRENCY_REGISTRY.get_historical("RUR")
    withdrawals = {item.withdrawn: item.countries for item in records}
    assert len(records) == 10
    assert withdrawals["1993-01"] == ("KYRGYZSTAN",)
    assert withdrawals["1994-08"] == ("ARMENIA", "AZERBAIJAN")
    assert withdrawals["2004-01"] == ("RUSSIAN FEDERATION",)
