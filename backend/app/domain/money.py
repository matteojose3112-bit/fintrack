"""Exact, registry-backed money primitives for Aurelius.

Amounts use Decimal and integer minor units only; binary floats are rejected.
The domain remains independent of SQLAlchemy, FastAPI, and market-data providers.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from types import MappingProxyType
from typing import ClassVar, Mapping

from .currency import DEFAULT_CURRENCY_REGISTRY


_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True, slots=True)
class Money:
    """An amount in a current ISO 4217 monetary unit.

    Construction rounds to the published minor-unit scale using ROUND_HALF_UP.
    Cross-currency arithmetic is rejected; FX conversion is a separate,
    timestamped, evidence-bearing domain operation.
    """

    amount: Decimal
    currency: str

    # Compatibility surface for callers that used the former class mapping.
    # The values now come from the complete bundled SIX/ISO snapshot.
    CURRENCY_EXPONENTS: ClassVar[Mapping[str, int]] = MappingProxyType(
        DEFAULT_CURRENCY_REGISTRY.current_money_units
    )

    def __post_init__(self) -> None:
        currency = self.currency.upper() if isinstance(self.currency, str) else ""
        if not _CURRENCY_PATTERN.fullmatch(currency):
            raise ValueError("currency must be a three-letter uppercase currency code")
        try:
            definition = DEFAULT_CURRENCY_REGISTRY.get_money_unit(currency)
        except ValueError as exc:
            raise ValueError(f"unsupported currency: {currency}") from exc
        exponent = definition.minor_unit_exponent
        assert exponent is not None

        if isinstance(self.amount, bool) or isinstance(self.amount, float):
            raise TypeError("money amounts must be Decimal or decimal strings, never float")
        if isinstance(self.amount, str):
            try:
                amount = Decimal(self.amount)
            except InvalidOperation as exc:
                raise ValueError("amount must be a valid decimal string") from exc
        elif isinstance(self.amount, Decimal):
            amount = self.amount
        else:
            raise TypeError("money amounts must be Decimal or decimal strings")

        if not amount.is_finite():
            raise ValueError("money amount must be finite")

        quantum = Decimal(1).scaleb(-exponent)
        try:
            normalized = amount.quantize(quantum, rounding=ROUND_HALF_UP)
        except InvalidOperation as exc:
            raise ValueError("amount exceeds the supported Decimal precision") from exc
        if normalized.is_zero():
            normalized = abs(normalized)
        object.__setattr__(self, "amount", normalized)
        object.__setattr__(self, "currency", currency)

    @classmethod
    def from_minor_units(cls, minor_units: int, currency: str) -> "Money":
        """Create Money from an exact integer count of currency minor units."""
        if isinstance(minor_units, bool) or not isinstance(minor_units, int):
            raise TypeError("minor units must be an integer, never bool or float")

        normalized_currency = currency.upper() if isinstance(currency, str) else ""
        exponent = cls.CURRENCY_EXPONENTS.get(normalized_currency)
        if exponent is None:
            raise ValueError(f"unsupported currency: {normalized_currency}")

        sign = "-" if minor_units < 0 else ""
        digits = str(abs(minor_units))
        if exponent:
            digits = digits.zfill(exponent + 1)
            amount = f"{sign}{digits[:-exponent]}.{digits[-exponent:]}"
        else:
            amount = f"{sign}{digits}"
        return cls(amount=amount, currency=normalized_currency)

    @classmethod
    def from_decimal_string(cls, amount: str, currency: str) -> "Money":
        """Create Money from an exact API/import decimal string."""
        if not isinstance(amount, str):
            raise TypeError("API money amounts must be decimal strings")
        return cls(amount=amount, currency=currency)

    @property
    def minor_units(self) -> int:
        exponent = self.CURRENCY_EXPONENTS[self.currency]
        return int(self.amount.scaleb(exponent))

    def to_decimal_string(self) -> str:
        exponent = self.CURRENCY_EXPONENTS[self.currency]
        return f"{self.amount:.{exponent}f}"

    def _require_same_currency(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise TypeError("money arithmetic requires another Money value")
        if self.currency != other.currency:
            raise ValueError(
                "cannot combine different currencies without an explicit FX conversion"
            )

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)
