from decimal import Decimal

import pytest

from app.domain.portfolio_money import (
    MAX_MINOR_UNITS,
    allocate_minor_units,
    from_minor_units,
    to_minor_units,
)


@pytest.mark.parametrize(
    ("amount", "exponent", "expected"),
    [
        ("12.5", 0, 13),
        ("12.345", 2, 1235),
        ("12.3455", 3, 12346),
        ("-1.005", 2, -101),
        ("0.004", 2, 0),
    ],
)
def test_to_minor_units_uses_currency_scale_and_half_up(amount, exponent, expected):
    assert to_minor_units(Decimal(amount), exponent) == expected


@pytest.mark.parametrize(
    ("minor", "exponent", "expected"),
    [
        (123, 0, "123"),
        (1234, 2, "12.34"),
        (12345, 3, "12.345"),
        (-5, 2, "-0.05"),
    ],
)
def test_from_minor_units_is_exact(minor, exponent, expected):
    assert format(from_minor_units(minor, exponent), "f") == expected


def test_float_and_non_finite_values_are_rejected():
    with pytest.raises(TypeError):
        to_minor_units(1.25, 2)
    with pytest.raises(ValueError):
        to_minor_units(Decimal("NaN"), 2)
    with pytest.raises(ValueError):
        to_minor_units(Decimal("Infinity"), 2)


def test_exponent_and_minor_unit_bounds_are_enforced():
    with pytest.raises(ValueError):
        to_minor_units(Decimal("1"), -1)
    with pytest.raises(TypeError):
        to_minor_units(Decimal("1"), True)
    with pytest.raises(ValueError):
        from_minor_units(MAX_MINOR_UNITS + 1, 2)
    with pytest.raises(ValueError):
        to_minor_units(Decimal("1e40"), 0)


def test_allocation_is_order_independent_and_residual_is_exact():
    first = allocate_minor_units(
        100,
        [("lot-b", Decimal("1")), ("lot-a", Decimal("1")), ("lot-c", Decimal("1"))],
    )
    second = allocate_minor_units(
        100,
        [("lot-c", Decimal("1")), ("lot-a", Decimal("1")), ("lot-b", Decimal("1"))],
    )
    assert first == second
    assert first == {"lot-a": 33, "lot-b": 33, "lot-c": 34}
    assert sum(first.values()) == 100


def test_allocation_supports_zero_total_and_rejects_invalid_inputs():
    assert allocate_minor_units(0, [("lot-a", Decimal("2"))]) == {"lot-a": 0}
    assert allocate_minor_units(0, []) == {}
    with pytest.raises(ValueError):
        allocate_minor_units(1, [])
    with pytest.raises(ValueError):
        allocate_minor_units(10, [("lot-a", Decimal("0"))])
    with pytest.raises(ValueError):
        allocate_minor_units(10, [("lot-a", Decimal("1")), ("lot-a", Decimal("2"))])
