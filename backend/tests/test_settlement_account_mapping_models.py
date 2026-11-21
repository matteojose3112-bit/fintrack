from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.persistence.settlement_models import PortfolioLedgerAccountMappingModel


def test_portfolio_ledger_mapping_is_scoped_by_portfolio_cash_account_and_currency():
    uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in PortfolioLedgerAccountMappingModel.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert uniques["uq_portfolio_ledger_mapping_scope"] == (
        "portfolio_id",
        "cash_account_id",
        "currency_definition_id",
    )


def test_all_four_ledger_roles_enforce_same_owner_and_currency():
    foreign_keys = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in PortfolioLedgerAccountMappingModel.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert foreign_keys["fk_portfolio_ledger_mapping_cash_owner_currency"] == (
        "cash_account_id", "owner_id", "currency_definition_id"
    )
    assert foreign_keys["fk_portfolio_ledger_mapping_investment_owner_currency"] == (
        "investment_control_account_id", "owner_id", "currency_definition_id"
    )
    assert foreign_keys["fk_portfolio_ledger_mapping_gain_owner_currency"] == (
        "realized_gain_account_id", "owner_id", "currency_definition_id"
    )
    assert foreign_keys["fk_portfolio_ledger_mapping_loss_owner_currency"] == (
        "realized_loss_account_id", "owner_id", "currency_definition_id"
    )


def test_mapping_requires_distinct_accounts_and_has_no_name_based_resolution():
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in PortfolioLedgerAccountMappingModel.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_portfolio_ledger_mapping_distinct_accounts" in checks
    assert "cash_account_id <> investment_control_account_id" in checks[
        "ck_portfolio_ledger_mapping_distinct_accounts"
    ]
    assert "name" not in PortfolioLedgerAccountMappingModel.__table__.c
    assert PortfolioLedgerAccountMappingModel.__table__.c.id.primary_key
