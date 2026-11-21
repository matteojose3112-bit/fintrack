"""Seed the bundled immutable ISO 4217 definitions after Alembic upgrade.

Default behavior is dry-run. Use --apply for an explicit database write.
Production writes additionally require --allow-production.
Run from backend/: python -m scripts.seed_currency_registry
"""
from __future__ import annotations

import argparse
import os

from app.database import SessionLocal, engine
from app.persistence.currency_registry_seed import seed_currency_registry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write missing definitions")
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="explicitly permit writes when ENVIRONMENT=production",
    )
    args = parser.parse_args()

    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "production" and not args.allow_production:
        parser.error("production writes require the explicit --allow-production flag")

    if not args.apply:
        print(
            "Dry run: no rows written. "
            f"Target dialect={engine.dialect.name}. "
            "Re-run with --apply to insert missing immutable registry records."
        )
        return 0

    with SessionLocal() as session:
        with session.begin():
            inserted = seed_currency_registry(session)
    print(
        f"Currency registry seed complete: inserted {inserted} records "
        f"into {engine.dialect.name}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
