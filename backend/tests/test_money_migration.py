"""Regression tests for upgrading populated legacy Float databases."""
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text


BACKEND = Path(__file__).resolve().parents[1]


def _run_alembic(database_url: str, revision: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        cwd=BACKEND,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def test_populated_legacy_sqlite_data_survives_fixed_precision_migration(tmp_path):
    database_path = tmp_path / "legacy-fintrack.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    # Build the exact pre-PR schema, then seed linked records as a legacy user.
    _run_alembic(database_url, "0001_initial")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (id, email, password_hash) VALUES (1, :email, :hash)"),
            {"email": "legacy@example.test", "hash": "not-a-real-password-hash"},
        )
        connection.execute(
            text("""INSERT INTO transactions
                (id, user_id, title, amount, type, category, date)
                VALUES (1, 1, 'Legacy transaction', 10.106, 'expense', 'Food', '2026-11-10')""")
        )
        connection.execute(
            text("""INSERT INTO budgets (id, user_id, category, "limit")
                VALUES (1, 1, 'Food', 100.004)""")
        )
        connection.execute(
            text("""INSERT INTO goals (id, user_id, name, target_amount, saved_amount)
                VALUES (1, 1, 'Legacy goal', 1000.006, 25.344)""")
        )
    engine.dispose()

    _run_alembic(database_url, "head")

    engine = create_engine(database_url)
    with engine.connect() as connection:
        transaction_amount = connection.execute(
            text("SELECT amount FROM transactions WHERE id = 1")
        ).scalar_one()
        budget_limit = connection.execute(
            text('SELECT "limit" FROM budgets WHERE id = 1')
        ).scalar_one()
        goal_target, goal_saved = connection.execute(
            text("SELECT target_amount, saved_amount FROM goals WHERE id = 1")
        ).one()

        assert Decimal(str(transaction_amount)).quantize(Decimal("0.01")) == Decimal("10.11")
        assert Decimal(str(budget_limit)).quantize(Decimal("0.01")) == Decimal("100.00")
        assert Decimal(str(goal_target)).quantize(Decimal("0.01")) == Decimal("1000.01")
        assert Decimal(str(goal_saved)).quantize(Decimal("0.01")) == Decimal("25.34")

        inspector = inspect(connection)
        assert {index["name"] for index in inspector.get_indexes("transactions")} >= {
            "ix_transactions_id", "ix_transactions_user_id"
        }
        assert {index["name"] for index in inspector.get_indexes("budgets")} >= {
            "ix_budgets_id", "ix_budgets_user_id"
        }
        assert {index["name"] for index in inspector.get_indexes("goals")} >= {
            "ix_goals_id", "ix_goals_user_id"
        }
        for table in ("transactions", "budgets", "goals"):
            foreign_keys = inspector.get_foreign_keys(table)
            assert any(
                fk["referred_table"] == "users"
                and fk["constrained_columns"] == ["user_id"]
                for fk in foreign_keys
            )

        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == "0002_fixed_money"
    engine.dispose()


def test_populated_legacy_postgresql_data_survives_fixed_precision_migration():
    import pytest

    database_url = os.getenv("TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("TEST_POSTGRES_URL is only configured in the PostgreSQL migration CI job")

    _run_alembic(database_url, "0001_initial")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (id, email, password_hash) VALUES (1, :email, :hash)"),
            {"email": "legacy@example.test", "hash": "not-a-real-password-hash"},
        )
        connection.execute(text("""INSERT INTO transactions
            (id, user_id, title, amount, type, category, date)
            VALUES (1, 1, 'Legacy transaction', 10.106, 'expense', 'Food', '2026-11-10')"""))
        connection.execute(text("""INSERT INTO budgets (id, user_id, category, "limit")
            VALUES (1, 1, 'Food', 100.004)"""))
        connection.execute(text("""INSERT INTO goals (id, user_id, name, target_amount, saved_amount)
            VALUES (1, 1, 'Legacy goal', 1000.006, 25.344)"""))
    engine.dispose()

    _run_alembic(database_url, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        transaction_amount = connection.execute(text(
            "SELECT amount FROM transactions WHERE id = 1"
        )).scalar_one()
        budget_limit = connection.execute(text(
            'SELECT "limit" FROM budgets WHERE id = 1'
        )).scalar_one()
        goal_target, goal_saved = connection.execute(text(
            "SELECT target_amount, saved_amount FROM goals WHERE id = 1"
        )).one()

        assert Decimal(str(transaction_amount)).quantize(Decimal("0.01")) == Decimal("10.11")
        assert Decimal(str(budget_limit)).quantize(Decimal("0.01")) == Decimal("100.00")
        assert Decimal(str(goal_target)).quantize(Decimal("0.01")) == Decimal("1000.01")
        assert Decimal(str(goal_saved)).quantize(Decimal("0.01")) == Decimal("25.34")

        inspector = inspect(connection)
        for table, expected_indexes in {
            "transactions": {"ix_transactions_id", "ix_transactions_user_id"},
            "budgets": {"ix_budgets_id", "ix_budgets_user_id"},
            "goals": {"ix_goals_id", "ix_goals_user_id"},
        }.items():
            assert expected_indexes <= {index["name"] for index in inspector.get_indexes(table)}
            assert any(
                fk["referred_table"] == "users"
                and fk["constrained_columns"] == ["user_id"]
                for fk in inspector.get_foreign_keys(table)
            )
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == "0002_fixed_money"
    engine.dispose()
