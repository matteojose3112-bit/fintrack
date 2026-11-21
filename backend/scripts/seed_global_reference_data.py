"""Seed Aurelius unit and illustrative asset reference data.

Default behavior is dry-run. Run from backend/:
  python -m scripts.seed_global_reference_data
  python -m scripts.seed_global_reference_data --apply

Production writes additionally require --allow-production.
"""
from __future__ import annotations

import argparse
import os

from app.database import SessionLocal, engine
from app.persistence.instrument_registry_seed import seed_global_reference_data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write missing reference rows")
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="explicitly permit writes when ENVIRONMENT=production",
    )
    args = parser.parse_args()

    if os.getenv("ENVIRONMENT", "development").lower() == "production" and not args.allow_production:
        parser.error("production writes require the explicit --allow-production flag")

    if not args.apply:
        from app.domain.asset_registry import DEFAULT_ASSET_REGISTRY, DEFAULT_UNIT_REGISTRY

        print(
            "Dry run: no rows written. "
            f"Target dialect={engine.dialect.name}; "
            f"units={len(DEFAULT_UNIT_REGISTRY.definitions)}; "
            f"assets={len(DEFAULT_ASSET_REGISTRY.definitions)}. "
            "Re-run with --apply to insert missing immutable reference rows."
        )
        return 0

    with SessionLocal() as session:
        with session.begin():
            result = seed_global_reference_data(session)
    print(f"Global reference seed complete on {engine.dialect.name}: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
