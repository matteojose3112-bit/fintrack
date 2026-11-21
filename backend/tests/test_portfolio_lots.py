from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.portfolio_lots import (
    CostBasisMethod,
    PortfolioAccountingError,
    PortfolioLotBook,
    TradeExecution,
    TradeSide,
)


PORTFOLIO = uuid4()
ACCOUNT = uuid4()
INSTRUMENT = uuid4()
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def trade(side, quantity, price, *, fee="0", day=0, execution_id=None, currency="USD"):
    return TradeExecution(
        execution_id=execution_id or uuid4(),
        portfolio_id=PORTFOLIO,
        account_id=ACCOUNT,
        instrument_id=INSTRUMENT,
        side=side,
        quantity=Decimal(quantity),
        unit_price=Decimal(price),
        quote_currency_code=currency,
        fee=Decimal(fee),
        executed_at=T0 + timedelta(days=day),
        source="unit-test",
    )


def test_buy_creates_deterministic_lot_and_includes_acquisition_fee():
    book = PortfolioLotBook()
    execution = trade(TradeSide.BUY, "10", "12.50", fee="5")
    first = book.apply(execution)
    replay = book.apply(execution)

    assert first.opened_lot_id is not None
    assert first.opened_lot_id == replay.opened_lot_id
    assert replay.replayed is True
    assert book.position(PORTFOLIO, ACCOUNT, INSTRUMENT, "USD").quantity == Decimal("10")
    assert book.position(PORTFOLIO, ACCOUNT, INSTRUMENT, "USD").remaining_cost_basis == Decimal("130")


def test_fifo_disposal_allocates_oldest_lot_and_calculates_realized_gain():
    book = PortfolioLotBook()
    old = book.apply(trade(TradeSide.BUY, "5", "10", day=0))
    book.apply(trade(TradeSide.BUY, "5", "20", day=1))

    result = book.apply(trade(TradeSide.SELL, "3", "15", fee="3", day=2))

    assert result.allocations[0].lot_id == old.opened_lot_id
    assert result.allocations[0].cost_basis == Decimal("30")
    assert result.allocations[0].net_proceeds == Decimal("42")
    assert result.realized_gain_loss == Decimal("12")
    position = book.position(PORTFOLIO, ACCOUNT, INSTRUMENT, "USD")
    assert position.quantity == Decimal("7")
    assert position.remaining_cost_basis == Decimal("120")


def test_lifo_disposal_allocates_newest_lot():
    book = PortfolioLotBook()
    book.apply(trade(TradeSide.BUY, "2", "10", day=0))
    newest = book.apply(trade(TradeSide.BUY, "2", "20", day=1))
    result = book.apply(
        trade(TradeSide.SELL, "1", "25", day=2),
        cost_basis_method=CostBasisMethod.LIFO,
    )
    assert result.allocations[0].lot_id == newest.opened_lot_id
    assert result.allocations[0].cost_basis == Decimal("20")


def test_specific_lot_disposal_only_uses_requested_lot():
    book = PortfolioLotBook()
    book.apply(trade(TradeSide.BUY, "2", "10", day=0))
    selected = book.apply(trade(TradeSide.BUY, "3", "20", day=1))
    result = book.apply(
        trade(TradeSide.SELL, "2", "25", day=2),
        cost_basis_method=CostBasisMethod.SPECIFIC,
        specific_lot_id=selected.opened_lot_id,
    )
    assert len(result.allocations) == 1
    assert result.allocations[0].lot_id == selected.opened_lot_id
    assert book.position(PORTFOLIO, ACCOUNT, INSTRUMENT, "USD").quantity == Decimal("3")


def test_specific_method_requires_lot_and_rejects_unexpected_lot_argument():
    book = PortfolioLotBook()
    with pytest.raises(PortfolioAccountingError):
        book.apply(
            trade(TradeSide.SELL, "1", "10"),
            cost_basis_method=CostBasisMethod.SPECIFIC,
        )
    with pytest.raises(PortfolioAccountingError):
        book.apply(
            trade(TradeSide.BUY, "1", "10"),
            specific_lot_id=uuid4(),
        )


def test_sale_exceeding_position_is_atomic():
    book = PortfolioLotBook()
    buy = book.apply(trade(TradeSide.BUY, "2", "10"))
    before = book.position(PORTFOLIO, ACCOUNT, INSTRUMENT, "USD")
    with pytest.raises(PortfolioAccountingError):
        book.apply(trade(TradeSide.SELL, "3", "12"))
    after = book.position(PORTFOLIO, ACCOUNT, INSTRUMENT, "USD")
    assert after == before
    assert len(book.lots) == 1
    assert book.lots[0].lot_id == buy.opened_lot_id


def test_execution_id_replay_is_idempotent_but_payload_reuse_conflicts():
    book = PortfolioLotBook()
    execution_id = uuid4()
    original = trade(TradeSide.BUY, "1", "10", execution_id=execution_id)
    assert book.apply(original).replayed is False
    assert book.apply(original).replayed is True
    changed = trade(TradeSide.BUY, "2", "10", execution_id=execution_id)
    with pytest.raises(PortfolioAccountingError):
        book.apply(changed)
    assert book.position(PORTFOLIO, ACCOUNT, INSTRUMENT, "USD").quantity == Decimal("1")


def test_positions_are_isolated_by_account_and_currency():
    book = PortfolioLotBook()
    book.apply(trade(TradeSide.BUY, "2", "10", currency="USD"))
    other_account_trade = TradeExecution(
        execution_id=uuid4(), portfolio_id=PORTFOLIO, account_id=uuid4(),
        instrument_id=INSTRUMENT, side=TradeSide.BUY, quantity=Decimal("3"),
        unit_price=Decimal("10"), quote_currency_code="USD", fee=Decimal("0"),
        executed_at=T0, source="unit-test",
    )
    book.apply(other_account_trade)
    assert book.position(PORTFOLIO, ACCOUNT, INSTRUMENT, "USD").quantity == Decimal("2")
    assert book.position(PORTFOLIO, ACCOUNT, INSTRUMENT, "EUR").quantity == Decimal("0")


@pytest.mark.parametrize("field,value", [
    ("quantity", 1.5),
    ("unit_price", 2.5),
    ("fee", 0.1),
])
def test_binary_float_trade_values_are_rejected(field, value):
    kwargs = dict(
        execution_id=uuid4(), portfolio_id=PORTFOLIO, account_id=ACCOUNT,
        instrument_id=INSTRUMENT, side=TradeSide.BUY, quantity=Decimal("1"),
        unit_price=Decimal("2"), quote_currency_code="USD", fee=Decimal("0"),
        executed_at=T0, source="unit-test",
    )
    kwargs[field] = value
    with pytest.raises(TypeError):
        TradeExecution(**kwargs)


def test_trade_requires_timezone_aware_execution_time():
    with pytest.raises(ValueError):
        trade(TradeSide.BUY, "1", "1").__class__(
            execution_id=uuid4(), portfolio_id=PORTFOLIO, account_id=ACCOUNT,
            instrument_id=INSTRUMENT, side=TradeSide.BUY, quantity=Decimal("1"),
            unit_price=Decimal("1"), quote_currency_code="USD", fee=Decimal("0"),
            executed_at=datetime(2026, 1, 1), source="unit-test",
        )


def test_currency_precision_version_rounds_acquisition_basis_and_disposal_allocations():
    book = PortfolioLotBook()
    first = TradeExecution(
        execution_id=uuid4(), portfolio_id=PORTFOLIO, account_id=ACCOUNT,
        instrument_id=INSTRUMENT, side=TradeSide.BUY, quantity=Decimal("1"),
        unit_price=Decimal("1.005"), quote_currency_code="USD", fee=Decimal("0.004"),
        executed_at=T0, source="unit-test", currency_minor_unit_exponent=2,
    )
    book.apply(first)
    assert book.lots[0].original_cost == Decimal("1.01")

    second = TradeExecution(
        execution_id=uuid4(), portfolio_id=PORTFOLIO, account_id=ACCOUNT,
        instrument_id=INSTRUMENT, side=TradeSide.BUY, quantity=Decimal("1"),
        unit_price=Decimal("2.005"), quote_currency_code="USD", fee=Decimal("0"),
        executed_at=T0 + timedelta(days=1), source="unit-test",
        currency_minor_unit_exponent=2,
    )
    book.apply(second)

    sale = TradeExecution(
        execution_id=uuid4(), portfolio_id=PORTFOLIO, account_id=ACCOUNT,
        instrument_id=INSTRUMENT, side=TradeSide.SELL, quantity=Decimal("2"),
        unit_price=Decimal("2.005"), quote_currency_code="USD", fee=Decimal("0.015"),
        executed_at=T0 + timedelta(days=2), source="unit-test",
        currency_minor_unit_exponent=2,
    )
    result = book.apply(sale)
    assert sum((x.gross_proceeds for x in result.allocations), Decimal("0")) == Decimal("4.01")
    assert sum((x.allocated_sale_fee for x in result.allocations), Decimal("0")) == Decimal("0.02")
    assert sum((x.cost_basis for x in result.allocations), Decimal("0")) == Decimal("3.02")
    assert result.realized_gain_loss == Decimal("0.97")
    assert all(x.cost_basis == x.cost_basis.quantize(Decimal("0.01")) for x in result.allocations)
    assert book.position(PORTFOLIO, ACCOUNT, INSTRUMENT, "USD").remaining_cost_basis == Decimal("0.00")


def test_currency_precision_supports_zero_and_three_decimal_exponents():
    for exponent, price, expected in [
        (0, "12.5", Decimal("13")),
        (3, "1.2345", Decimal("1.235")),
    ]:
        book = PortfolioLotBook()
        execution = TradeExecution(
            execution_id=uuid4(), portfolio_id=PORTFOLIO, account_id=ACCOUNT,
            instrument_id=INSTRUMENT, side=TradeSide.BUY, quantity=Decimal("1"),
            unit_price=Decimal(price), quote_currency_code="TST", fee=Decimal("0"),
            executed_at=T0, source="unit-test",
            currency_minor_unit_exponent=exponent,
        )
        book.apply(execution)
        assert book.lots[0].original_cost == expected


def test_currency_precision_rejects_sale_fee_above_gross_without_mutation():
    book = PortfolioLotBook()
    buy = TradeExecution(
        execution_id=uuid4(), portfolio_id=PORTFOLIO, account_id=ACCOUNT,
        instrument_id=INSTRUMENT, side=TradeSide.BUY, quantity=Decimal("1"),
        unit_price=Decimal("1"), quote_currency_code="USD", fee=Decimal("0"),
        executed_at=T0, source="unit-test", currency_minor_unit_exponent=2,
    )
    book.apply(buy)
    sell = TradeExecution(
        execution_id=uuid4(), portfolio_id=PORTFOLIO, account_id=ACCOUNT,
        instrument_id=INSTRUMENT, side=TradeSide.SELL, quantity=Decimal("1"),
        unit_price=Decimal("1"), quote_currency_code="USD", fee=Decimal("1.01"),
        executed_at=T0 + timedelta(days=1), source="unit-test",
        currency_minor_unit_exponent=2,
    )
    before = book.position(PORTFOLIO, ACCOUNT, INSTRUMENT, "USD")
    with pytest.raises(PortfolioAccountingError, match="fee cannot exceed"):
        book.apply(sell)
    assert book.position(PORTFOLIO, ACCOUNT, INSTRUMENT, "USD") == before
