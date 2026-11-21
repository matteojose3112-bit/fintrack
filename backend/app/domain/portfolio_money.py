"""Currency-scale conversion and deterministic minor-unit allocation.

This module is a pure domain primitive. Callers must supply the immutable
currency exponent captured for the trade; it deliberately does not look up a
current registry definition or infer a currency from a display label.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP, localcontext
from typing import Iterable

MAX_MINOR_UNITS = 10**38 - 1


def _validate_exponent(exponent: int) -> int:
    if isinstance(exponent, bool) or not isinstance(exponent, int):
        raise TypeError("currency exponent must be an integer")
    if exponent < 0 or exponent > 9:
        raise ValueError("currency exponent must be between 0 and 9")
    return exponent


def _decimal(value: Decimal) -> Decimal:
    if isinstance(value, (bool, float)) or not isinstance(value, Decimal):
        raise TypeError("monetary values must be Decimal; binary floats are prohibited")
    if not value.is_finite():
        raise ValueError("monetary values must be finite")
    return value


def to_minor_units(amount: Decimal, exponent: int) -> int:
    """Round one final currency amount HALF_UP and return exact integer units."""
    exponent = _validate_exponent(exponent)
    amount = _decimal(amount)
    quantum = Decimal(1).scaleb(-exponent)
    with localcontext() as context:
        context.prec = max(50, len(amount.as_tuple().digits) + exponent + 8)
        try:
            rounded = amount.quantize(quantum, rounding=ROUND_HALF_UP)
        except InvalidOperation as exc:
            raise ValueError("amount exceeds supported Decimal precision") from exc
        minor = int(rounded.scaleb(exponent))
    if abs(minor) > MAX_MINOR_UNITS:
        raise ValueError("amount exceeds the ledger 38-digit minor-unit bound")
    return 0 if minor == 0 else minor


def from_minor_units(minor_units: int, exponent: int) -> Decimal:
    """Convert exact integer minor units to a Decimal at the currency scale."""
    exponent = _validate_exponent(exponent)
    if isinstance(minor_units, bool) or not isinstance(minor_units, int):
        raise TypeError("minor units must be an integer; bool and float are prohibited")
    if abs(minor_units) > MAX_MINOR_UNITS:
        raise ValueError("amount exceeds the ledger 38-digit minor-unit bound")
    return Decimal(minor_units).scaleb(-exponent)


def allocate_minor_units(
    total_minor_units: int,
    weighted_keys: Iterable[tuple[str, Decimal]],
) -> dict[str, int]:
    """Allocate a non-negative integer total proportionally and deterministically.

    Keys are sorted lexically before allocation. Every allocation except the
    final key is rounded down; the final key receives the exact residual.
    The result therefore sums to the requested total without losing a minor
    unit, and is independent of input iteration order.
    """
    if isinstance(total_minor_units, bool) or not isinstance(total_minor_units, int):
        raise TypeError("total_minor_units must be an integer")
    if total_minor_units < 0 or total_minor_units > MAX_MINOR_UNITS:
        raise ValueError("total_minor_units is outside the supported range")

    entries = list(weighted_keys)
    if not entries:
        if total_minor_units == 0:
            return {}
        raise ValueError("at least one allocation key is required for a positive total")

    normalized: list[tuple[str, Decimal]] = []
    seen: set[str] = set()
    for key, weight in entries:
        if not isinstance(key, str) or not key:
            raise TypeError("allocation keys must be non-empty strings")
        if key in seen:
            raise ValueError("allocation keys must be unique")
        seen.add(key)
        weight = _decimal(weight)
        if weight <= 0:
            raise ValueError("allocation weights must be positive")
        normalized.append((key, weight))

    normalized.sort(key=lambda item: item[0])
    if total_minor_units == 0:
        return {key: 0 for key, _ in normalized}

    with localcontext() as context:
        context.prec = 80
        total_weight = sum((weight for _, weight in normalized), Decimal("0"))
        result: dict[str, int] = {}
        allocated = 0
        for key, weight in normalized[:-1]:
            share = (Decimal(total_minor_units) * weight / total_weight).to_integral_value(
                rounding=ROUND_DOWN
            )
            units = int(share)
            result[key] = units
            allocated += units
        result[normalized[-1][0]] = total_minor_units - allocated

    assert sum(result.values()) == total_minor_units
    return result
