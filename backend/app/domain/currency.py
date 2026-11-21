"""Versioned ISO 4217 currency registry.

The bundled data is a reproducible snapshot, not a runtime network dependency.
Only current List One entries with a published minor-unit exponent are eligible
for Money arithmetic. Historical List Three entries are preserved as reference
records; List Three does not publish exponents, so we never guess them.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


_CODE = re.compile(r"^[A-Z]{3}$")
_NUMERIC = re.compile(r"^[0-9]{3}$")


@dataclass(frozen=True, slots=True)
class CurrencyDefinition:
    code: str
    numeric_code: str | None
    name: str
    minor_unit_exponent: int | None
    registry_list: str
    registry_release: str
    published: str
    fund: bool
    countries: tuple[str, ...]
    withdrawn: str | None = None

    @property
    def is_historical(self) -> bool:
        return self.registry_list == "three"

    @property
    def supports_exact_money(self) -> bool:
        return (
            self.registry_list == "one"
            and self.minor_unit_exponent is not None
        )


class CurrencyRegistry:
    """Immutable in-memory view of bundled current and historical ISO facts."""

    def __init__(self, snapshot: dict[str, Any]) -> None:
        if snapshot.get("schema_version") != 1:
            raise ValueError("unsupported currency snapshot schema version")

        self.registry_release = str(snapshot["registry_release"])
        self.source = dict(snapshot["source"])
        self.current_published = str(snapshot["current_published"])
        self.historical_published = str(snapshot["historical_published"])

        current = tuple(
            self._definition(row, "one", self.current_published)
            for row in snapshot["current"]
        )
        historical = tuple(
            self._definition(row, "three", self.historical_published)
            for row in snapshot["historical"]
        )
        self._validate_unique(current, "current")
        self._validate_unique(historical, "historical", include_withdrawal_date=True)

        self._current = {item.code: item for item in current}
        self._historical = historical
        self._historical_by_code: dict[str, list[CurrencyDefinition]] = {}
        for item in historical:
            self._historical_by_code.setdefault(item.code, []).append(item)

    @staticmethod
    def _definition(
        row: dict[str, Any], registry_list: str, published: str
    ) -> CurrencyDefinition:
        code = str(row["code"]).upper()
        numeric = row.get("numeric_code")
        exponent = row.get("minor_unit_exponent")
        if not _CODE.fullmatch(code):
            raise ValueError(f"invalid ISO 4217 alphabetic code: {code}")
        if numeric is not None and not _NUMERIC.fullmatch(str(numeric)):
            raise ValueError(f"invalid ISO 4217 numeric code for {code}")
        if exponent is not None and (
            isinstance(exponent, bool) or not isinstance(exponent, int) or exponent < 0
        ):
            raise ValueError(f"invalid minor-unit exponent for {code}")
        return CurrencyDefinition(
            code=code,
            numeric_code=str(numeric) if numeric is not None else None,
            name=str(row["name"]),
            minor_unit_exponent=exponent,
            registry_list=registry_list,
            registry_release=f"SIX-ISO4217-L{registry_list}-{published}",
            published=published,
            fund=bool(row.get("fund", False)),
            countries=tuple(str(country) for country in row.get("countries", [])),
            withdrawn=row.get("withdrawn"),
        )

    @staticmethod
    def _validate_unique(
        definitions: tuple[CurrencyDefinition, ...],
        label: str,
        include_withdrawal_date: bool = False,
    ) -> None:
        keys = [
            (item.code, item.withdrawn) if include_withdrawal_date else item.code
            for item in definitions
        ]
        if len(keys) != len(set(keys)):
            raise ValueError(f"duplicate currency definition in {label} registry snapshot")

    @classmethod
    def from_file(cls, path: str | Path) -> "CurrencyRegistry":
        with Path(path).open("r", encoding="utf-8") as source_file:
            return cls(json.load(source_file))

    @classmethod
    def bundled(cls) -> "CurrencyRegistry":
        path = Path(__file__).parent / "data" / "iso4217_snapshot.json"
        return cls.from_file(path)

    @property
    def current_definitions(self) -> tuple[CurrencyDefinition, ...]:
        return tuple(self._current.values())

    @property
    def historical_definitions(self) -> tuple[CurrencyDefinition, ...]:
        return self._historical

    @property
    def current_money_units(self) -> dict[str, int]:
        return {
            item.code: item.minor_unit_exponent
            for item in self._current.values()
            if item.supports_exact_money
        }

    def get_current(self, code: str) -> CurrencyDefinition:
        normalized = code.upper() if isinstance(code, str) else ""
        try:
            return self._current[normalized]
        except KeyError as exc:
            raise ValueError(f"unsupported current ISO 4217 code: {normalized}") from exc

    def get_money_unit(self, code: str) -> CurrencyDefinition:
        definition = self.get_current(code)
        if not definition.supports_exact_money:
            raise ValueError(
                f"ISO 4217 code {definition.code} is not a current monetary unit "
                "with a defined minor-unit exponent"
            )
        return definition

    def get_historical(self, code: str) -> tuple[CurrencyDefinition, ...]:
        normalized = code.upper() if isinstance(code, str) else ""
        return tuple(self._historical_by_code.get(normalized, ()))


DEFAULT_CURRENCY_REGISTRY = CurrencyRegistry.bundled()
