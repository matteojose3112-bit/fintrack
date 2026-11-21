import pytest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.persistence.instrument_models import (
    AssetDefinitionModel,
    BondContractSpecModel,
    DerivativeContractSpecModel,
    ForecastRecordModel,
    ForecastResolutionModel,
    InstrumentDefinitionModel,
    InstrumentIdentifierModel,
    InstrumentListingModel,
    MarketObservationModel,
    MarketVenueModel,
    PredictionContractSpecModel,
    ProviderSourceModel,
    UnitDefinitionModel,
)
from app.persistence.instrument_registry_seed import seed_global_reference_data


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_global_reference_seed_is_idempotent_and_covers_units_and_assets():
    engine, session = make_session()
    try:
        result = seed_global_reference_data(session)
        session.commit()
        assert result == {
            "unit_definitions_inserted": 18,
            "asset_definitions_inserted": 27,
        }
        assert session.scalar(select(func.count()).select_from(UnitDefinitionModel)) == 18
        assert session.scalar(select(func.count()).select_from(AssetDefinitionModel)) == 27

        assert seed_global_reference_data(session) == {
            "unit_definitions_inserted": 0,
            "asset_definitions_inserted": 0,
        }
        session.commit()

        gold = session.scalars(
            select(AssetDefinitionModel).where(
                AssetDefinitionModel.asset_id == "commodity.gold"
            )
        ).one()
        assert gold.quantity_unit_code == "troy_ounce"
        bitcoin = session.scalars(
            select(AssetDefinitionModel).where(
                AssetDefinitionModel.asset_id == "crypto.bitcoin"
            )
        ).one()
        assert bitcoin.asset_class == "crypto_asset"
    finally:
        session.close()
        engine.dispose()


def test_global_reference_seed_refuses_to_mutate_existing_unit_release():
    engine, session = make_session()
    try:
        seed_global_reference_data(session)
        session.commit()
        gram = session.scalars(
            select(UnitDefinitionModel).where(UnitDefinitionModel.code == "gram")
        ).one()
        gram.symbol = "tampered"
        session.commit()
        with pytest.raises(ValueError, match="immutable unit registry record changed"):
            seed_global_reference_data(session)
    finally:
        session.close()
        engine.dispose()


def test_instrument_master_models_are_registered_on_shared_metadata():
    expected = {
        "unit_definitions",
        "asset_definitions",
        "instrument_definitions",
        "instrument_identifiers",
        "market_venues",
        "instrument_listings",
        "derivative_contract_specs",
        "bond_contract_specs",
        "prediction_contract_specs",
        "provider_sources",
        "market_observations",
        "forecast_records",
        "forecast_resolutions",
    }
    assert expected <= set(Base.metadata.tables)
    assert InstrumentDefinitionModel.__tablename__ == "instrument_definitions"
    assert InstrumentIdentifierModel.__tablename__ == "instrument_identifiers"
    assert MarketVenueModel.__tablename__ == "market_venues"
    assert InstrumentListingModel.__tablename__ == "instrument_listings"
    assert DerivativeContractSpecModel.__tablename__ == "derivative_contract_specs"
    assert BondContractSpecModel.__tablename__ == "bond_contract_specs"
    assert PredictionContractSpecModel.__tablename__ == "prediction_contract_specs"
    assert ProviderSourceModel.__tablename__ == "provider_sources"
    assert MarketObservationModel.__tablename__ == "market_observations"
    assert ForecastRecordModel.__tablename__ == "forecast_records"
    assert ForecastResolutionModel.__tablename__ == "forecast_resolutions"
