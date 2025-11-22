"""Streaming ITCH parser."""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass
from typing import BinaryIO, Callable, Dict, Iterable, Iterator, Tuple

from mpid_latency import messages


class ITCHDecodeError(ValueError):
    """Raised when parsing an ITCH stream fails."""


_MessageDecoder = Tuple[int, Callable[[bytes], object]]


def _byte_to_int(block: bytes) -> int:
    return int.from_bytes(block, byteorder="big")


def _byte_to_str(block: bytes) -> str:
    return block.decode("ascii", errors="ignore").rstrip()


def _decode_system_event(body: bytes) -> messages.SystemEvent:
    locate, track_num, ts, event = struct.unpack(">HH6sc", body)
    return messages.SystemEvent(
        timestamp=_byte_to_int(ts),
        event=_byte_to_str(event),
        locate=locate,
        tracking_number=track_num,
    )


def _decode_stock_directory(body: bytes) -> messages.StockDirectory:
    (
        locate,
        track_num,
        ts,
        stock,
        market_category,
        financial_status,
        round_lot_size,
        round_lots_only,
        issue_classification,
        issue_sub_type,
        authenticity,
        short_sale_threshold,
        ipo_flag,
        luld_tier,
        etp_flag,
        etp_leverage_factor,
        inverse_indicator,
    ) = struct.unpack(">HH6s8sssIcc2scccccIc", body)
    return messages.StockDirectory(
        timestamp=_byte_to_int(ts),
        stock=_byte_to_str(stock),
        market_category=_byte_to_str(market_category),
        financial_status=_byte_to_str(financial_status),
        round_lot_size=round_lot_size,
        round_lots_only=_byte_to_str(round_lots_only),
        issue_classification=_byte_to_str(issue_classification),
        issue_sub_type=_byte_to_str(issue_sub_type),
        authenticity=_byte_to_str(authenticity),
        short_sale_threshold=_byte_to_str(short_sale_threshold),
        ipo_flag=_byte_to_str(ipo_flag),
        luld_tier=_byte_to_str(luld_tier),
        etp_flag=_byte_to_str(etp_flag),
        etp_leverage_factor=etp_leverage_factor,
        inverse_indicator=_byte_to_str(inverse_indicator),
        locate=locate,
        tracking_number=track_num,
    )


def _decode_trading_action(body: bytes) -> messages.TradingAction:
    locate, track_num, ts, stock, trading_state, reserved, reason = struct.unpack(
        ">HH6s8scc4s", body
    )
    return messages.TradingAction(
        timestamp=_byte_to_int(ts),
        stock=_byte_to_str(stock),
        trading_state=_byte_to_str(trading_state),
        reason=_byte_to_str(reason),
        locate=locate,
        tracking_number=track_num,
    )


def _decode_add_order(body: bytes) -> messages.AddOrder:
    locate, track_num, ts, order_id, side, shares, stock, price = struct.unpack(
        ">HH6sQcI8sI", body
    )
    return messages.AddOrder(
        timestamp=_byte_to_int(ts),
        order_id=order_id,
        side=_byte_to_str(side),
        shares=shares,
        stock=_byte_to_str(stock),
        price=price,
        locate=locate,
        tracking_number=track_num,
    )


def _decode_add_order_mpid(body: bytes) -> messages.AddOrderMPID:
    (
        locate,
        track_num,
        ts,
        order_id,
        side,
        shares,
        stock,
        price,
        mpid,
    ) = struct.unpack(">HH6sQcI8sI4s", body)
    return messages.AddOrderMPID(
        timestamp=_byte_to_int(ts),
        order_id=order_id,
        side=_byte_to_str(side),
        shares=shares,
        stock=_byte_to_str(stock),
        price=price,
        mpid=_byte_to_str(mpid),
        locate=locate,
        tracking_number=track_num,
    )


def _decode_execute(body: bytes) -> messages.Execute:
    locate, track_num, ts, order_id, shares, match_num = struct.unpack(
        ">HH6sQIQ", body
    )
    return messages.Execute(
        timestamp=_byte_to_int(ts),
        order_id=order_id,
        shares=shares,
        match_number=match_num,
        locate=locate,
        tracking_number=track_num,
    )


def _decode_execute_with_price(body: bytes) -> messages.ExecuteWithPrice:
    locate, track_num, ts, order_id, shares, match_num, printable, price = (
        struct.unpack(">HH6sQIQcI", body)
    )
    return messages.ExecuteWithPrice(
        timestamp=_byte_to_int(ts),
        order_id=order_id,
        shares=shares,
        match_number=match_num,
        printable=_byte_to_str(printable),
        price=price,
        locate=locate,
        tracking_number=track_num,
    )


def _decode_cancel(body: bytes) -> messages.Cancel:
    locate, track_num, ts, order_id, canceled_shares = struct.unpack(
        ">HH6sQI", body
    )
    return messages.Cancel(
        timestamp=_byte_to_int(ts),
        order_id=order_id,
        canceled_shares=canceled_shares,
        locate=locate,
        tracking_number=track_num,
    )


def _decode_delete(body: bytes) -> messages.Delete:
    locate, track_num, ts, order_id = struct.unpack(">HH6sQ", body)
    return messages.Delete(
        timestamp=_byte_to_int(ts),
        order_id=order_id,
        locate=locate,
        tracking_number=track_num,
    )


def _decode_replace(body: bytes) -> messages.Replace:
    locate, track_num, ts, order_id, new_order_id, shares, price = struct.unpack(
        ">HH6sQQII", body
    )
    return messages.Replace(
        timestamp=_byte_to_int(ts),
        order_id=order_id,
        new_order_id=new_order_id,
        shares=shares,
        price=price,
        locate=locate,
        tracking_number=track_num,
    )


def _decode_trade(body: bytes) -> messages.Trade:
    locate, track_num, ts, order_id, side, shares, stock, price, match_num = (
        struct.unpack(">HH6sQcI8sIQ", body)
    )
    return messages.Trade(
        timestamp=_byte_to_int(ts),
        order_id=order_id,
        side=_byte_to_str(side),
        shares=shares,
        stock=_byte_to_str(stock),
        price=price,
        match_number=match_num,
        locate=locate,
        tracking_number=track_num,
    )


def _decode_cross(body: bytes) -> messages.Cross:
    locate, track_num, ts, shares, stock, cross_price, match_num, cross_type = (
        struct.unpack(">HH6sQ8sIQc", body)
    )
    return messages.Cross(
        timestamp=_byte_to_int(ts),
        shares=shares,
        stock=_byte_to_str(stock),
        cross_price=cross_price,
        match_number=match_num,
        cross_type=_byte_to_str(cross_type),
        locate=locate,
        tracking_number=track_num,
    )


def _decode_broken_trade(body: bytes) -> messages.BrokenTrade:
    locate, track_num, ts, match_num = struct.unpack(">HH6sQ", body)
    return messages.BrokenTrade(
        timestamp=_byte_to_int(ts),
        match_number=match_num,
        locate=locate,
        tracking_number=track_num,
    )


_DECODERS: Dict[bytes, _MessageDecoder] = {
    b"S": (14, _decode_system_event),
    b"R": (41, _decode_stock_directory),
    b"H": (27, _decode_trading_action),
    b"A": (38, _decode_add_order),
    b"F": (42, _decode_add_order_mpid),
    b"E": (33, _decode_execute),
    b"C": (38, _decode_execute_with_price),
    b"X": (25, _decode_cancel),
    b"D": (21, _decode_delete),
    b"U": (37, _decode_replace),
    b"P": (46, _decode_trade),
    b"Q": (42, _decode_cross),
    b"B": (21, _decode_broken_trade),
}


@dataclass
class ITCHReader:
    source: BinaryIO | str | bytes | io.BytesIO

    def __post_init__(self) -> None:
        if isinstance(self.source, bytes):
            self._fh = io.BytesIO(self.source)
            self._close = True
        elif isinstance(self.source, str):
            self._fh = open(self.source, "rb")
            self._close = True
        else:
            self._fh = self.source
            self._close = False

    def __iter__(self) -> Iterator[object]:
        try:
            for msg in self._iterate_messages(self._fh):
                yield msg
        finally:
            if self._close:
                self._fh.close()

    @staticmethod
    def _iterate_messages(fh: BinaryIO) -> Iterable[object]:
        while True:
            msg_type = fh.read(1)
            if not msg_type:
                break

            length_bytes = fh.read(2)
            if len(length_bytes) != 2:
                raise ITCHDecodeError("Truncated message length.")

            msg_length = int.from_bytes(length_bytes, byteorder="big")
            if msg_length < 3:
                raise ITCHDecodeError(f"Invalid message length: {msg_length}")

            body_length = msg_length - 3
            body = fh.read(body_length)
            if len(body) != body_length:
                raise ITCHDecodeError(
                    f"Truncated message body for type {msg_type!r}, expected {body_length} bytes."
                )

            expected = _DECODERS.get(msg_type)
            if expected is None:
                raise ITCHDecodeError(f"Unknown message type: {msg_type!r}")

            expected_length, decoder = expected
            if expected_length != msg_length:
                raise ITCHDecodeError(
                    f"Unexpected length for type {msg_type!r}: got {msg_length}, expected {expected_length}"
                )

            yield decoder(body)
