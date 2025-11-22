import pytest

from mpid_latency.messages import (
    AddOrder,
    AddOrderMPID,
    BrokenTrade,
    Cancel,
    Cross,
    Delete,
    Execute,
    ExecuteWithPrice,
    Replace,
    Side,
    StockDirectory,
    SystemEvent,
    Trade,
    TradingAction,
)


def test_side_from_value_handles_str_and_bytes():
    assert Side.from_value("B") is Side.BUY
    assert Side.from_value("s") is Side.SELL
    assert Side.from_value(b"B") is Side.BUY
    with pytest.raises(ValueError):
        Side.from_value("X")


def test_system_event_strips_event():
    msg = SystemEvent(timestamp=1, event=" O ", locate=5, tracking_number=7)
    assert msg.event == "O"
    assert msg.locate == 5
    assert msg.tracking_number == 7


def test_stock_directory_strips_strings():
    msg = StockDirectory(
        timestamp=10,
        stock="AAPL ",
        market_category=" Q ",
        financial_status=" N ",
        round_lot_size=100,
        round_lots_only=" Y ",
        issue_classification=" M ",
        issue_sub_type=" AB ",
        authenticity=" P ",
        short_sale_threshold=" E ",
        ipo_flag=" Y ",
        luld_tier=" 1 ",
        etp_flag=" N ",
        etp_leverage_factor=1,
        inverse_indicator=" N ",
    )
    assert msg.stock == "AAPL"
    assert msg.market_category == "Q"
    assert msg.financial_status == "N"
    assert msg.round_lots_only == "Y"
    assert msg.issue_classification == "M"
    assert msg.issue_sub_type == "AB"
    assert msg.authenticity == "P"
    assert msg.short_sale_threshold == "E"
    assert msg.ipo_flag == "Y"
    assert msg.luld_tier == "1"
    assert msg.etp_flag == "N"
    assert msg.inverse_indicator == "N"


def test_trading_action_normalizes_fields():
    msg = TradingAction(
        timestamp=20,
        stock="MSFT ",
        trading_state=" H ",
        reason=" 42 ",
    )
    assert msg.stock == "MSFT"
    assert msg.trading_state == "H"
    assert msg.reason == "42"


def test_add_order_normalizes_stock_and_side():
    msg = AddOrder(
        timestamp=30,
        order_id=123,
        side="b",
        shares=100,
        stock="GOOG ",
        price=1500,
    )
    assert msg.stock == "GOOG"
    assert msg.side is Side.BUY
    assert msg.locate == 0
    assert msg.tracking_number == 0


def test_add_order_mpid_strips_mpid():
    msg = AddOrderMPID(
        timestamp=40,
        order_id=456,
        side="S",
        shares=200,
        stock="AMZN ",
        price=2500,
        mpid="ABCD ",
    )
    assert msg.side is Side.SELL
    assert msg.mpid == "ABCD"
    assert msg.stock == "AMZN"


def test_execute_and_execute_with_price_store_fields():
    exec_msg = Execute(timestamp=50, order_id=789, shares=50, match_number=999)
    assert exec_msg.order_id == 789
    assert exec_msg.shares == 50
    assert exec_msg.match_number == 999

    exec_price_msg = ExecuteWithPrice(
        timestamp=60,
        order_id=790,
        shares=60,
        match_number=1000,
        printable=" N ",
        price=1234,
    )
    assert exec_price_msg.printable == "N"
    assert exec_price_msg.price == 1234


def test_cancel_delete_replace_store_fields():
    cancel_msg = Cancel(timestamp=70, order_id=800, canceled_shares=10)
    assert cancel_msg.canceled_shares == 10

    delete_msg = Delete(timestamp=80, order_id=801)
    assert delete_msg.order_id == 801

    replace_msg = Replace(
        timestamp=90,
        order_id=802,
        new_order_id=900,
        shares=500,
        price=777,
    )
    assert replace_msg.order_id == 802
    assert replace_msg.new_order_id == 900
    assert replace_msg.shares == 500
    assert replace_msg.price == 777


def test_trade_and_cross_normalize_fields():
    trade_msg = Trade(
        timestamp=100,
        order_id=810,
        side=b"s",
        shares=1000,
        stock="NFLX ",
        price=3333,
        match_number=123456,
    )
    assert trade_msg.side is Side.SELL
    assert trade_msg.stock == "NFLX"

    cross_msg = Cross(
        timestamp=110,
        shares=2000,
        stock="TSLA ",
        cross_price=4444,
        match_number=654321,
        cross_type=" O ",
    )
    assert cross_msg.stock == "TSLA"
    assert cross_msg.cross_type == "O"


def test_broken_trade_fields():
    broken = BrokenTrade(timestamp=120, match_number=42, locate=1, tracking_number=2)
    assert broken.match_number == 42
    assert broken.locate == 1
    assert broken.tracking_number == 2
