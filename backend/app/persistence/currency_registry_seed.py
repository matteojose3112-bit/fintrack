"""Idempotent seeding of immutable SIX ISO 4217 reference definitions.

The caller owns the SQLAlchemy transaction and commit decision. Existing rows
are verified, never updated or deleted.
"""
from __future__ import annotations

from datetime import date
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.orm import Session

from app.domain.currency import CurrencyDefinition, DEFAULT_CURRENCY_REGISTRY
from app.persistence.models import CurrencyDefinitionModel


def _source_url(definition: CurrencyDefinition) -> str:
    key = "list_one_url" if definition.registry_list == "one" else "list_three_url"
    return str(DEFAULT_CURRENCY_REGISTRY.source[key])


def _record_values(definition: CurrencyDefinition) -> dict:
    return {
        "code": definition.code,
        "numeric_code": definition.numeric_code,
        "name": definition.name,
        "minor_unit_exponent": definition.minor_unit_exponent,
        "registry_list": definition.registry_list,
        "registry_release": definition.registry_release,
        "published_on": date.fromisoformat(definition.published),
        "fund": definition.fund,
        "withdrawal_key": definition.withdrawn or "",
        "withdrawn_label": definition.withdrawn,
        "countries": list(definition.countries),
        "source_url": _source_url(definition),
    }


def _record_id(definition: CurrencyDefinition):
    stable_key = "|".join(
        (
            "aurelius-iso4217",
            definition.registry_release,
            definition.code,
            definition.withdrawn or "",
        )
    )
    return uuid5(NAMESPACE_URL, stable_key)


def seed_currency_registry(
    session: Session,
    definitions: tuple[CurrencyDefinition, ...] | None = None,
) -> int:
    """Insert missing definitions and verify existing immutable rows.

    Returns the number of inserted records. Does not commit; callers can wrap
    the operation in a larger transaction and roll it back atomically.
    """
    if definitions is None:
        definitions = (
            DEFAULT_CURRENCY_REGISTRY.current_definitions
            + DEFAULT_CURRENCY_REGISTRY.historical_definitions
        )

    inserted = 0
    for definition in definitions:
        record_id = _record_id(definition)
        values = _record_values(definition)
        existing = session.get(CurrencyDefinitionModel, record_id)
        if existing is not None:
            for field, expected in values.items():
                if getattr(existing, field) != expected:
                    raise ValueError(
                        f"immutable currency registry record changed: "
                        f"{definition.code} ({definition.registry_release}) field {field}"
                    )
            continue

        session.add(CurrencyDefinitionModel(id=record_id, **values))
        inserted += 1

    session.flush()
    return inserted
