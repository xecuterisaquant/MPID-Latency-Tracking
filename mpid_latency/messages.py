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


@dataclass
class NOII:
    """Net Order Imbalance Indicator."""
    timestamp: int
    paired_shares: int
    imbalance_shares: int
    imbalance_direction: str
    stock: str
    far_price: int
    near_price: int
    current_reference_price: int
    cross_type: str
    price_variation_indicator: str
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.stock = self.stock.strip()
        self.imbalance_direction = self.imbalance_direction.strip()
        self.cross_type = self.cross_type.strip()
        self.price_variation_indicator = self.price_variation_indicator.strip()


@dataclass
class RegSHORestriction:
    """Reg SHO Short Sale Price Test Restricted Indicator."""
    timestamp: int
    stock: str
    reg_sho_action: str
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.stock = self.stock.strip()
        self.reg_sho_action = self.reg_sho_action.strip()


@dataclass
class MarketParticipantPosition:
    """Market Participant Position."""
    timestamp: int
    mpid: str
    stock: str
    primary_market_maker: str
    market_maker_mode: str
    market_participant_state: str
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.mpid = self.mpid.strip()
        self.stock = self.stock.strip()
        self.primary_market_maker = self.primary_market_maker.strip()
        self.market_maker_mode = self.market_maker_mode.strip()
        self.market_participant_state = self.market_participant_state.strip()


@dataclass
class MWCBDeclineLevel:
    """Market-Wide Circuit Breaker Decline Level Message."""
    timestamp: int
    level1: int
    level2: int
    level3: int
    locate: int = 0
    tracking_number: int = 0


@dataclass
class MWCBStatus:
    """Market-Wide Circuit Breaker Status Message."""
    timestamp: int
    breaker_level: str
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.breaker_level = self.breaker_level.strip()


@dataclass
class IPOQuotingPeriod:
    """IPO Quoting Period Update."""
    timestamp: int
    stock: str
    ipo_quotation_release_time: int
    ipo_quotation_release_qualifier: str
    ipo_price: int
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.stock = self.stock.strip()
        self.ipo_quotation_release_qualifier = self.ipo_quotation_release_qualifier.strip()


@dataclass
class LULDAuctionCollar:
    """LULD Auction Collar."""
    timestamp: int
    stock: str
    auction_collar_reference_price: int
    upper_auction_collar_price: int
    lower_auction_collar_price: int
    auction_collar_extension: int
    locate: int = 0
    tracking_number: int = 0

    def __post_init__(self) -> None:
        self.stock = self.stock.strip()
