"""Seed immutable unit and illustrative asset reference definitions."""

from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.asset_registry import DEFAULT_ASSET_REGISTRY, DEFAULT_UNIT_REGISTRY
from app.persistence.instrument_models import AssetDefinitionModel, UnitDefinitionModel


REFERENCE_SOURCE_ID = "aurelius-curated-reference-v1"


def _unit_values(definition):
    return {
        "code": definition.code,
        "dimension": definition.dimension,
        "symbol": definition.symbol,
        "base_unit_code": definition.base_unit_code,
        "conversion_numerator": definition.conversion_numerator,
        "conversion_denominator": definition.conversion_denominator,
        "quantity_precision": definition.quantity_precision,
        "context_required": definition.context_required,
        "source_id": REFERENCE_SOURCE_ID,
        "source_url": None,
    }


def _asset_values(definition):
    return {
        "asset_id": definition.asset_id,
        "asset_class": definition.asset_class,
        "asset_type": definition.asset_type,
        "name": definition.name,
        "description": definition.description,
        "quantity_unit_code": definition.quantity_unit_code,
        "metadata_json": None,
        "source_id": REFERENCE_SOURCE_ID,
        "source_url": None,
        "source_retrieved_at": None,
    }


def seed_unit_definitions(session: Session) -> int:
    """Insert missing unit definitions; never update or delete published rows."""
    definitions = sorted(
        DEFAULT_UNIT_REGISTRY.definitions,
        key=lambda item: (item.code != item.base_unit_code, item.code),
    )
    inserted = 0
    for definition in definitions:
        values = _unit_values(definition)
        existing = session.scalars(
            select(UnitDefinitionModel).where(UnitDefinitionModel.code == definition.code)
        ).one_or_none()
        if existing is not None:
            if any(getattr(existing, key) != value for key, value in values.items()):
                raise ValueError(
                    f"immutable unit registry record changed: {definition.code}"
                )
            continue
        session.add(
            UnitDefinitionModel(
                id=uuid5(NAMESPACE_URL, f"aurelius:unit:{definition.code}"),
                **values,
            )
        )
        session.flush()
        inserted += 1
    return inserted


def seed_asset_definitions(session: Session) -> int:
    """Insert missing illustrative global assets; preserve existing definitions."""
    inserted = 0
    for definition in DEFAULT_ASSET_REGISTRY.definitions:
        values = _asset_values(definition)
        existing = session.scalars(
            select(AssetDefinitionModel).where(
                AssetDefinitionModel.asset_id == definition.asset_id
            )
        ).one_or_none()
        if existing is not None:
            if any(getattr(existing, key) != value for key, value in values.items()):
                raise ValueError(
                    f"immutable asset registry record changed: {definition.asset_id}"
                )
            continue
        session.add(
            AssetDefinitionModel(
                id=uuid5(NAMESPACE_URL, f"aurelius:asset:{definition.asset_id}"),
                **values,
            )
        )
        session.flush()
        inserted += 1
    return inserted


def seed_global_reference_data(session: Session) -> dict[str, int]:
    units_inserted = seed_unit_definitions(session)
    assets_inserted = seed_asset_definitions(session)
    return {
        "unit_definitions_inserted": units_inserted,
        "asset_definitions_inserted": assets_inserted,
    }
