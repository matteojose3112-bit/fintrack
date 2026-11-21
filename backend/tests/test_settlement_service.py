"""Pure accounting tests for portfolio-to-ledger settlement line construction."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.domain.portfolio_lots import TradeExecution, TradeSide
from app.persistence.settlement_service import _settlement_postings


def make_execution(side, *, quantity="10", price="12.34", fee="1.00"):
    return TradeExecution(
        execution_id=uuid4(),
        portfolio_id=uuid4(),
        account_id=uuid4(),
        instrument_id=uuid4(),
        side=side,
        quantity=Decimal(quantity),
        unit_price=Decimal(price),
        quote_currency_code="USD",
        fee=Decimal(fee),
        executed_at=datetime(2026, 11, 21, 15, 0, tzinfo=timezone.utc),
        source="manual",
    )


def make_accounts():
    return SimpleNamespace(
        cash_account=SimpleNamespace(id=uuid4()),
        investment_control_account=SimpleNamespace(id=uuid4()),
        realized_gain_account=SimpleNamespace(id=uuid4()),
        realized_loss_account=SimpleNamespace(id=uuid4()),
    )


def make_portfolio_result(*cost_basis):
    allocations = tuple(
        SimpleNamespace(cost_basis=Decimal(value)) for value in cost_basis
    )
    return SimpleNamespace(
        application=SimpleNamespace(allocations=allocations)
    )


def test_buy_capitalizes_fee_and_posts_equal_cash_credit():
    execution = make_execution(TradeSide.BUY)
    accounts = make_accounts()

    lines = _settlement_postings(
        execution, make_portfolio_result(), accounts, exponent=2
    )

    assert [(line.account_id, line.side, line.amount_minor) for line in lines] == [
        (accounts.investment_control_account.id, "DEBIT", 12440),
        (accounts.cash_account.id, "CREDIT", 12440),
    ]


def test_sell_with_gain_reconciles_cash_basis_and_gain():
    execution = make_execution(
        TradeSide.SELL, quantity="4", price="15.00", fee="0.60"
    )
    accounts = make_accounts()

    lines = _settlement_postings(
        execution, make_portfolio_result("49.76"), accounts, exponent=2
    )

    assert {(line.account_id, line.side, line.amount_minor) for line in lines} == {
        (accounts.cash_account.id, "DEBIT", 5940),
        (accounts.investment_control_account.id, "CREDIT", 4976),
        (accounts.realized_gain_account.id, "CREDIT", 964),
    }


def test_sell_with_loss_reconciles_cash_basis_and_loss():
    execution = make_execution(
        TradeSide.SELL, quantity="3", price="15.20", fee="0.60"
    )
    accounts = make_accounts()

    lines = _settlement_postings(
        execution, make_portfolio_result("49.76"), accounts, exponent=2
    )

    assert {(line.account_id, line.side, line.amount_minor) for line in lines} == {
        (accounts.cash_account.id, "DEBIT", 4500),
        (accounts.investment_control_account.id, "CREDIT", 4976),
        (accounts.realized_loss_account.id, "DEBIT", 476),
    }


def test_sell_fee_cannot_exceed_gross_proceeds():
    execution = make_execution(
        TradeSide.SELL, quantity="1", price="1.00", fee="1.01"
    )
    import pytest
    from app.persistence.settlement_service import SettlementPrecisionError

    with pytest.raises(SettlementPrecisionError, match="exceed gross"):
        _settlement_postings(
            execution, make_portfolio_result("1.00"), make_accounts(), exponent=2
        )


def test_zero_value_buy_is_rejected():
    execution = make_execution(
        TradeSide.BUY, quantity="1", price="0.00", fee="0.00"
    )
    import pytest
    from app.persistence.settlement_service import SettlementPrecisionError

    with pytest.raises(SettlementPrecisionError, match="zero-value BUY"):
        _settlement_postings(
            execution, make_portfolio_result(), make_accounts(), exponent=2
        )
