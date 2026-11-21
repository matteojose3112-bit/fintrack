"""Extensible global asset, instrument, and exact-unit reference domain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction
import re
from types import MappingProxyType
from typing import Mapping
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_ASSET_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,31}\.[a-z0-9][a-z0-9_.-]{0,127}$")


@dataclass(frozen=True, slots=True)
class UnitDefinition:
    code: str
    dimension: str
    symbol: str
    base_unit_code: str
    conversion_numerator: int | None
    conversion_denominator: int | None
    quantity_precision: int
    context_required: bool = False

    def __post_init__(self) -> None:
        if not _CODE_PATTERN.fullmatch(self.code):
            raise ValueError("unit code must be a lowercase namespaced-safe identifier")
        if not _CODE_PATTERN.fullmatch(self.dimension):
            raise ValueError("unit dimension must be a lowercase identifier")
        if not _CODE_PATTERN.fullmatch(self.base_unit_code):
            raise ValueError("base unit code must be a lowercase identifier")
        if not 0 <= self.quantity_precision <= 18:
            raise ValueError("quantity precision must be between 0 and 18")
        has_numerator = self.conversion_numerator is not None
        has_denominator = self.conversion_denominator is not None
        if has_numerator != has_denominator:
            raise ValueError("unit conversion numerator and denominator must be supplied together")
        if has_numerator and (
            self.conversion_numerator <= 0 or self.conversion_denominator <= 0
        ):
            raise ValueError("unit conversion ratio must be positive")
        if self.context_required and has_numerator:
            raise ValueError("context-required units cannot claim a universal conversion")
        if not self.context_required and not has_numerator:
            raise ValueError("non-contextual units require an exact conversion ratio")

    @property
    def conversion_to_base(self) -> Fraction | None:
        if self.context_required:
            return None
        return Fraction(self.conversion_numerator, self.conversion_denominator)


class UnitRegistry:
    def __init__(self, definitions: tuple[UnitDefinition, ...]) -> None:
        by_code: dict[str, UnitDefinition] = {}
        for definition in definitions:
            if definition.code in by_code:
                raise ValueError(f"duplicate unit definition: {definition.code}")
            by_code[definition.code] = definition
        for definition in definitions:
            if definition.base_unit_code not in by_code:
                raise ValueError(f"unknown base unit: {definition.base_unit_code}")
            base = by_code[definition.base_unit_code]
            if base.dimension != definition.dimension:
                raise ValueError(f"base unit dimension mismatch for {definition.code}")
            if (
                definition.code == definition.base_unit_code
                and not definition.context_required
                and definition.conversion_to_base != Fraction(1, 1)
            ):
                raise ValueError("base unit must have an exact 1:1 conversion")
        self._definitions: Mapping[str, UnitDefinition] = MappingProxyType(by_code)

    @property
    def definitions(self) -> tuple[UnitDefinition, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    def get(self, code: str) -> UnitDefinition:
        try:
            return self._definitions[code]
        except KeyError as exc:
            raise ValueError(f"unsupported quantity unit: {code}") from exc

    def conversion_ratio(self, source_code: str, target_code: str) -> Fraction:
        source = self.get(source_code)
        target = self.get(target_code)
        if source_code == target_code:
            return Fraction(1, 1)
        if source.context_required or target.context_required:
            raise ValueError("unit conversion requires instrument/commodity context")
        if source.dimension != target.dimension:
            raise ValueError("unit dimensions do not match")
        if source.base_unit_code != target.base_unit_code:
            raise ValueError("units do not share a canonical base unit")
        return source.conversion_to_base / target.conversion_to_base

    def convert_exact(
        self, quantity: Decimal | int | str, source_code: str, target_code: str
    ) -> Fraction:
        if isinstance(quantity, bool):
            raise TypeError("quantity cannot be boolean")
        if isinstance(quantity, float):
            raise TypeError("binary floating-point quantities are not accepted")
        decimal_quantity = quantity if isinstance(quantity, Decimal) else Decimal(str(quantity))
        if not decimal_quantity.is_finite():
            raise ValueError("quantity must be finite")
        numerator, denominator = decimal_quantity.as_integer_ratio()
        return Fraction(numerator, denominator) * self.conversion_ratio(
            source_code, target_code
        )


@dataclass(frozen=True, slots=True)
class AssetDefinition:
    asset_id: str
    asset_class: str
    asset_type: str
    name: str
    quantity_unit_code: str
    description: str = ""

    def __post_init__(self) -> None:
        if not _ASSET_ID_PATTERN.fullmatch(self.asset_id):
            raise ValueError("asset_id must be a stable namespace-qualified identifier")
        if not _CODE_PATTERN.fullmatch(self.asset_class):
            raise ValueError("asset_class must be an open lowercase identifier")
        if not _CODE_PATTERN.fullmatch(self.asset_type):
            raise ValueError("asset_type must be an open lowercase identifier")
        if not self.name.strip():
            raise ValueError("asset name must be non-empty")
        if not self.quantity_unit_code:
            raise ValueError("asset quantity unit is required")


class AssetRegistry:
    def __init__(
        self,
        definitions: tuple[AssetDefinition, ...],
        units: UnitRegistry,
    ) -> None:
        by_id: dict[str, AssetDefinition] = {}
        for definition in definitions:
            if definition.asset_id in by_id:
                raise ValueError(f"duplicate asset definition: {definition.asset_id}")
            units.get(definition.quantity_unit_code)
            by_id[definition.asset_id] = definition
        self._definitions: Mapping[str, AssetDefinition] = MappingProxyType(by_id)
        self._units = units

    @property
    def definitions(self) -> tuple[AssetDefinition, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    def get(self, asset_id: str) -> AssetDefinition:
        try:
            return self._definitions[asset_id]
        except KeyError as exc:
            raise ValueError(f"unsupported asset: {asset_id}") from exc

    def by_class(self, asset_class: str) -> tuple[AssetDefinition, ...]:
        return tuple(
            item
            for item in self.definitions
            if item.asset_class == asset_class
        )


@dataclass(frozen=True, slots=True)
class InstrumentIdentifier:
    namespace: str
    value: str
    source: str
    valid_from: date | None = None
    valid_to: date | None = None

    def __post_init__(self) -> None:
        if not _CODE_PATTERN.fullmatch(self.namespace):
            raise ValueError("identifier namespace must be a lowercase identifier")
        if not self.value.strip() or not self.source.strip():
            raise ValueError("identifier value and source must be non-empty")
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("identifier validity range is inverted")


@dataclass(frozen=True, slots=True)
class InstrumentDefinition:
    instrument_id: UUID
    instrument_type: str
    name: str
    underlying_asset_id: str | None = None
    quote_currency_code: str | None = None
    identifiers: tuple[InstrumentIdentifier, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, UUID):
            raise TypeError("instrument_id must be UUID")
        if not _CODE_PATTERN.fullmatch(self.instrument_type):
            raise ValueError("instrument_type must be an open lowercase identifier")
        if not self.name.strip():
            raise ValueError("instrument name must be non-empty")
        if self.underlying_asset_id is not None and not _ASSET_ID_PATTERN.fullmatch(
            self.underlying_asset_id
        ):
            raise ValueError("underlying_asset_id must be namespace-qualified")
        if self.quote_currency_code is not None and not re.fullmatch(
            r"[A-Z]{3}", self.quote_currency_code
        ):
            raise ValueError("quote currency must be a three-letter uppercase code")
        namespaces = [(item.namespace, item.value, item.source) for item in self.identifiers]
        if len(namespaces) != len(set(namespaces)):
            raise ValueError("duplicate instrument identifier/source pair")


UNIT_DEFINITIONS = (
    UnitDefinition("gram", "mass", "g", "gram", 1, 1, 6),
    UnitDefinition("troy_ounce", "mass", "ozt", "gram", 311034768, 10000000, 6),
    UnitDefinition("ounce", "mass", "oz", "gram", 28349523125, 1000000000, 6),
    UnitDefinition("pound", "mass", "lb", "gram", 45359237, 100000, 6),
    UnitDefinition("metric_tonne", "mass", "t", "gram", 1000000, 1, 6),
    UnitDefinition("litre", "volume", "L", "litre", 1, 1, 6),
    UnitDefinition("barrel", "volume", "bbl", "litre", 158987294928, 1000000000, 6),
    UnitDefinition("us_gallon", "volume", "gal", "litre", 3785411784, 1000000000, 6),
    UnitDefinition("joule", "energy", "J", "joule", 1, 1, 6),
    UnitDefinition("mmbtu", "energy", "MMBtu", "joule", 105505585262, 100, 6),
    UnitDefinition("mwh", "energy", "MWh", "joule", 3600000000, 1, 6),
    UnitDefinition("share", "security_quantity", "sh", "share", 1, 1, 8),
    UnitDefinition("contract", "derivative_quantity", "contract", "contract", 1, 1, 8),
    UnitDefinition("token", "token_quantity", "token", "token", 1, 1, 18),
    UnitDefinition("event_share", "event_contract_quantity", "share", "event_share", 1, 1, 8),
    UnitDefinition("square_metre", "area", "m2", "square_metre", 1, 1, 6),
    UnitDefinition("index_point", "index_points", "pt", "index_point", 1, 1, 8),
    UnitDefinition("bushel", "commodity_specific", "bu", "bushel", None, None, 6, True),
)
DEFAULT_UNIT_REGISTRY = UnitRegistry(UNIT_DEFINITIONS)


ASSET_DEFINITIONS = (
    AssetDefinition("commodity.gold", "commodity", "precious_metal", "Gold", "troy_ounce"),
    AssetDefinition("commodity.silver", "commodity", "precious_metal", "Silver", "troy_ounce"),
    AssetDefinition("commodity.platinum", "commodity", "precious_metal", "Platinum", "troy_ounce"),
    AssetDefinition("commodity.palladium", "commodity", "precious_metal", "Palladium", "troy_ounce"),
    AssetDefinition("commodity.wti_crude_oil", "commodity", "energy", "WTI crude oil", "barrel"),
    AssetDefinition("commodity.brent_crude_oil", "commodity", "energy", "Brent crude oil", "barrel"),
    AssetDefinition("commodity.natural_gas", "commodity", "energy", "Natural gas", "mmbtu"),
    AssetDefinition("commodity.copper", "commodity", "industrial_metal", "Copper", "metric_tonne"),
    AssetDefinition("commodity.aluminium", "commodity", "industrial_metal", "Aluminium", "metric_tonne"),
    AssetDefinition("commodity.wheat", "commodity", "agriculture", "Wheat", "bushel"),
    AssetDefinition("commodity.corn", "commodity", "agriculture", "Corn", "bushel"),
    AssetDefinition("commodity.soybeans", "commodity", "agriculture", "Soybeans", "bushel"),
    AssetDefinition("commodity.coffee", "commodity", "agriculture", "Coffee", "pound"),
    AssetDefinition("commodity.cocoa", "commodity", "agriculture", "Cocoa", "metric_tonne"),
    AssetDefinition("commodity.electricity", "commodity", "energy", "Electricity", "mwh"),
    AssetDefinition("issuer.example_public_company", "equity_issuer", "public_company", "Example public company", "share"),
    AssetDefinition("fixed_income.sovereign_debt", "fixed_income", "sovereign_bond", "Sovereign debt", "contract"),
    AssetDefinition("fund.global_equity_etf", "fund", "exchange_traded_fund", "Global equity ETF", "share"),
    AssetDefinition("crypto.bitcoin", "crypto_asset", "native_coin", "Bitcoin", "token"),
    AssetDefinition("crypto.ethereum", "crypto_asset", "native_coin", "Ether", "token"),
    AssetDefinition("real_estate.residential_property", "real_estate", "residential_property", "Residential property", "square_metre"),
    AssetDefinition("prediction.election_event", "prediction_contract", "binary_event", "Election outcome event", "event_share"),
    AssetDefinition("liability.mortgage", "liability", "secured_loan", "Mortgage liability", "contract"),
    AssetDefinition("benchmark.global_equity_index", "benchmark", "equity_index", "Global equity benchmark", "index_point"),
    AssetDefinition("fx.eur_usd_pair", "fx_pair", "spot_fx_pair", "EUR/USD currency pair", "contract"),
    AssetDefinition("private_equity.venture_company", "private_equity", "venture_equity", "Private venture company", "share"),
    AssetDefinition("derivative.interest_rate_swap", "derivative", "interest_rate_swap", "Interest rate swap", "contract"),
)
DEFAULT_ASSET_REGISTRY = AssetRegistry(ASSET_DEFINITIONS, DEFAULT_UNIT_REGISTRY)


@dataclass(frozen=True, slots=True)
class MarketVenue:
    mic: str
    name: str
    country_code: str
    timezone: str
    venue_type: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z0-9]{4}", self.mic):
            raise ValueError("venue MIC must be a four-character ISO 10383 identifier")
        if not re.fullmatch(r"[A-Z]{2}", self.country_code):
            raise ValueError("venue country code must be ISO 3166 alpha-2")
        if not self.name.strip() or not _CODE_PATTERN.fullmatch(self.venue_type):
            raise ValueError("venue name and type are required")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
            raise ValueError("venue timezone must be a valid IANA timezone") from exc


@dataclass(frozen=True, slots=True)
class InstrumentListing:
    instrument_id: UUID
    venue_mic: str
    symbol: str
    quote_currency_code: str
    active_from: date
    active_to: date | None = None
    trading_calendar_code: str = "default"

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, UUID):
            raise TypeError("listing instrument_id must be UUID")
        if not re.fullmatch(r"[A-Z0-9]{4}", self.venue_mic):
            raise ValueError("listing venue_mic must be a four-character MIC")
        if not self.symbol.strip():
            raise ValueError("listing symbol must be non-empty")
        if not re.fullmatch(r"[A-Z]{3}", self.quote_currency_code):
            raise ValueError("listing quote currency must be ISO alpha-3")
        if self.active_to and self.active_to < self.active_from:
            raise ValueError("listing active date range is inverted")
        if not _CODE_PATTERN.fullmatch(self.trading_calendar_code):
            raise ValueError("trading calendar code must be a lowercase identifier")


@dataclass(frozen=True, slots=True)
class DerivativeContractSpec:
    instrument_id: UUID
    underlying_asset_id: str
    contract_unit_code: str
    contract_size: Decimal
    tick_size: Decimal
    tick_value: Decimal
    expiry_date: date
    settlement_type: str
    margin_currency_code: str
    first_notice_date: date | None = None
    last_trade_date: date | None = None
    delivery_grade: str | None = None
    delivery_location: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, UUID):
            raise TypeError("derivative instrument_id must be UUID")
        if not _ASSET_ID_PATTERN.fullmatch(self.underlying_asset_id):
            raise ValueError("derivative underlying asset ID is invalid")
        for value_name in ("contract_size", "tick_size", "tick_value"):
            value = getattr(self, value_name)
            if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
                raise ValueError(f"{value_name} must be a positive finite Decimal")
        if self.settlement_type not in {"cash", "physical"}:
            raise ValueError("settlement_type must be cash or physical")
        if not re.fullmatch(r"[A-Z]{3}", self.margin_currency_code):
            raise ValueError("margin currency must be ISO alpha-3")
        if self.first_notice_date and self.first_notice_date > self.expiry_date:
            raise ValueError("first notice date cannot be after expiry")
        if self.last_trade_date and self.last_trade_date > self.expiry_date:
            raise ValueError("last trade date cannot be after expiry")
        if self.first_notice_date and self.last_trade_date:
            if self.first_notice_date > self.last_trade_date:
                raise ValueError("first notice date cannot follow last trade date")


@dataclass(frozen=True, slots=True)
class BondContractSpec:
    instrument_id: UUID
    issuer_asset_id: str
    currency_code: str
    face_value: Decimal
    issue_date: date
    maturity_date: date
    coupon_type: str
    coupon_rate: Decimal
    coupon_frequency: int
    day_count_convention: str
    seniority: str

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, UUID):
            raise TypeError("bond instrument_id must be UUID")
        if not _ASSET_ID_PATTERN.fullmatch(self.issuer_asset_id):
            raise ValueError("bond issuer asset ID is invalid")
        if not re.fullmatch(r"[A-Z]{3}", self.currency_code):
            raise ValueError("bond currency must be ISO alpha-3")
        if not isinstance(self.face_value, Decimal) or not self.face_value.is_finite() or self.face_value <= 0:
            raise ValueError("bond face value must be a positive finite Decimal")
        if not isinstance(self.coupon_rate, Decimal) or not self.coupon_rate.is_finite() or self.coupon_rate < 0:
            raise ValueError("bond coupon rate must be a non-negative finite Decimal")
        if self.maturity_date <= self.issue_date:
            raise ValueError("bond maturity must follow issue date")
        if self.coupon_type not in {"fixed", "floating", "zero", "inflation_linked"}:
            raise ValueError("unsupported bond coupon type")
        if self.coupon_frequency not in {0, 1, 2, 4, 6, 12}:
            raise ValueError("unsupported bond coupon frequency")
        if not self.day_count_convention.strip() or not self.seniority.strip():
            raise ValueError("bond day-count convention and seniority are required")


@dataclass(frozen=True, slots=True)
class PredictionContractSpec:
    instrument_id: UUID
    event_id: str
    question: str
    outcomes: tuple[str, ...]
    resolution_source_url: str
    resolution_deadline: datetime
    settlement_currency_code: str
    payout_per_contract: Decimal

    def __post_init__(self) -> None:
        from urllib.parse import urlparse

        if not isinstance(self.instrument_id, UUID):
            raise TypeError("prediction instrument_id must be UUID")
        if not self.event_id.strip() or not self.question.strip():
            raise ValueError("prediction event ID and question are required")
        outcomes = tuple(self.outcomes)
        if len(outcomes) < 2 or any(not item.strip() for item in outcomes):
            raise ValueError("prediction contract requires at least two named outcomes")
        if len(set(outcomes)) != len(outcomes):
            raise ValueError("prediction outcomes must be unique")
        parsed = urlparse(self.resolution_source_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("resolution source must be an HTTPS URL")
        if not isinstance(self.resolution_deadline, datetime):
            raise TypeError("resolution deadline must be a datetime")
        if self.resolution_deadline.tzinfo is None:
            raise ValueError("resolution deadline must be timezone-aware")
        if not re.fullmatch(r"[A-Z]{3}", self.settlement_currency_code):
            raise ValueError("settlement currency must be ISO alpha-3")
        if (
            not isinstance(self.payout_per_contract, Decimal)
            or not self.payout_per_contract.is_finite()
            or self.payout_per_contract <= 0
        ):
            raise ValueError("prediction payout must be a positive finite Decimal")
        object.__setattr__(self, "outcomes", outcomes)
