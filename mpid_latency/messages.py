"""Typed message models for Nasdaq ITCH 5.0."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Side(Enum):
    BUY = "B"
    SELL = "S"

    @classmethod
    def from_value(cls, value: str | bytes | "Side") -> "Side":
        if isinstance(value, cls):
            return value
        if isinstance(value, bytes):
            value = value.decode("ascii", errors="ignore")
        normalized = value.strip().upper()
        if normalized == cls.BUY.value:
            return cls.BUY
        if normalized == cls.SELL.value:
            return cls.SELL
        raise ValueError(f"Unknown side value: {value!r}")


@dataclass
class SystemEvent:
    timestamp: int
    event: str
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.event = self.event.strip()


@dataclass
class StockDirectory:
    timestamp: int
    stock: str
    market_category: str
    financial_status: str
    round_lot_size: int
    round_lots_only: str
    issue_classification: str
    issue_sub_type: str
    authenticity: str
    short_sale_threshold: str
    ipo_flag: str
    luld_tier: str
    etp_flag: str
    etp_leverage_factor: int
    inverse_indicator: str
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.stock = self.stock.strip()
        self.market_category = self.market_category.strip()
        self.financial_status = self.financial_status.strip()
        self.round_lots_only = self.round_lots_only.strip()
        self.issue_classification = self.issue_classification.strip()
        self.issue_sub_type = self.issue_sub_type.strip()
        self.authenticity = self.authenticity.strip()
        self.short_sale_threshold = self.short_sale_threshold.strip()
        self.ipo_flag = self.ipo_flag.strip()
        self.luld_tier = self.luld_tier.strip()
        self.etp_flag = self.etp_flag.strip()
        self.inverse_indicator = self.inverse_indicator.strip()


@dataclass
class TradingAction:
    timestamp: int
    stock: str
    trading_state: str
    reason: str
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.stock = self.stock.strip()
        self.trading_state = self.trading_state.strip()
        self.reason = self.reason.strip()


@dataclass
class AddOrder:
    timestamp: int
    order_id: int
    side: Side
    shares: int
    stock: str
    price: int
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.stock = self.stock.strip()
        self.side = Side.from_value(self.side)


@dataclass
class AddOrderMPID:
    timestamp: int
    order_id: int
    side: Side
    shares: int
    stock: str
    price: int
    mpid: Optional[str]
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.stock = self.stock.strip()
        self.side = Side.from_value(self.side)
        self.mpid = self.mpid.strip() if self.mpid is not None else None


@dataclass
class Execute:
    timestamp: int
    order_id: int
    shares: int
    match_number: int
    locate: int = 0
    tracking_number: int = 0


@dataclass
class ExecuteWithPrice:
    timestamp: int
    order_id: int
    shares: int
    match_number: int
    printable: str
    price: int
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.printable = self.printable.strip()


@dataclass
class Cancel:
    timestamp: int
    order_id: int
    canceled_shares: int
    locate: int = 0
    tracking_number: int = 0


@dataclass
class Delete:
    timestamp: int
    order_id: int
    locate: int = 0
    tracking_number: int = 0


@dataclass
class Replace:
    timestamp: int
    order_id: int
    new_order_id: int
    shares: int
    price: int
    locate: int = 0
    tracking_number: int = 0


@dataclass
class Trade:
    timestamp: int
    order_id: int
    side: Side
    shares: int
    stock: str
    price: int
    match_number: int
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.stock = self.stock.strip()
        self.side = Side.from_value(self.side)


@dataclass
class Cross:
    timestamp: int
    shares: int
    stock: str
    cross_price: int
    match_number: int
    cross_type: str
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.stock = self.stock.strip()
        self.cross_type = self.cross_type.strip()


@dataclass
class BrokenTrade:
    timestamp: int
    match_number: int
    locate: int = 0
    tracking_number: int = 0
