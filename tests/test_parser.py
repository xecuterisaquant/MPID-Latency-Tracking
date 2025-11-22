import io
import struct

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
    StockDirectory,
    SystemEvent,
    Trade,
    TradingAction,
)
from mpid_latency.parser import ITCHDecodeError, ITCHReader


def _pad(text: str, length: int) -> bytes:
    return text.ljust(length, " ").encode("ascii")


def _build(msg_type: str, body: bytes) -> bytes:
    length = len(body) + 3
    return msg_type.encode("ascii") + length.to_bytes(2, "big") + body


def _sample_messages_bytes() -> bytes:
    messages_bytes = []

    messages_bytes.append(
        _build(
            "S",
            struct.pack(">HH6sc", 1, 2, (123).to_bytes(6, "big"), b"O"),
        )
    )

    messages_bytes.append(
        _build(
            "R",
            struct.pack(
                ">HH6s8sssIcc2scccccIc",
                3,
                4,
                (456).to_bytes(6, "big"),
                _pad("AAPL", 8),
                b"Q",
                b"N",
                100,
                b"Y",
                b"M",
                b"AB",
                b"P",
                b"E",
                b"Y",
                b"1",
                b"N",
                1,
                b"N",
            ),
        )
    )

    messages_bytes.append(
        _build(
            "H",
            struct.pack(
                ">HH6s8scc4s",
                5,
                6,
                (789).to_bytes(6, "big"),
                _pad("MSFT", 8),
                b"H",
                b" ",
                b"12  ",
            ),
        )
    )

    messages_bytes.append(
        _build(
            "A",
            struct.pack(
                ">HH6sQcI8sI",
                7,
                8,
                (1000).to_bytes(6, "big"),
                111,
                b"B",
                10,
                _pad("GOOG", 8),
                12345,
            ),
        )
    )

    messages_bytes.append(
        _build(
            "F",
            struct.pack(
                ">HH6sQcI8sI4s",
                9,
                10,
                (1100).to_bytes(6, "big"),
                222,
                b"S",
                20,
                _pad("AMZN", 8),
                23456,
                b"ABCD",
            ),
        )
    )

    messages_bytes.append(
        _build(
            "E",
            struct.pack(
                ">HH6sQIQ",
                11,
                12,
                (1200).to_bytes(6, "big"),
                222,
                5,
                3333,
            ),
        )
    )

    messages_bytes.append(
        _build(
            "C",
            struct.pack(
                ">HH6sQIQcI",
                13,
                14,
                (1300).to_bytes(6, "big"),
                111,
                3,
                4444,
                b"N",
                12346,
            ),
        )
    )

    messages_bytes.append(
        _build(
            "X",
            struct.pack(">HH6sQI", 15, 16, (1400).to_bytes(6, "big"), 111, 2),
        )
    )

    messages_bytes.append(
        _build(
            "D",
            struct.pack(">HH6sQ", 17, 18, (1500).to_bytes(6, "big"), 222),
        )
    )

    messages_bytes.append(
        _build(
            "U",
            struct.pack(
                ">HH6sQQII",
                19,
                20,
                (1600).to_bytes(6, "big"),
                111,
                333,
                50,
                55555,
            ),
        )
    )

    messages_bytes.append(
        _build(
            "P",
            struct.pack(
                ">HH6sQcI8sIQ",
                21,
                22,
                (1700).to_bytes(6, "big"),
                444,
                b"S",
                60,
                _pad("NFLX", 8),
                66666,
                7777,
            ),
        )
    )

    messages_bytes.append(
        _build(
            "Q",
            struct.pack(
                ">HH6sQ8sIQc",
                23,
                24,
                (1800).to_bytes(6, "big"),
                70,
                _pad("TSLA", 8),
                77777,
                8888,
                b"O",
            ),
        )
    )

    messages_bytes.append(
        _build(
            "B",
            struct.pack(
                ">HH6sQ",
                25,
                26,
                (1900).to_bytes(6, "big"),
                9999,
            ),
        )
    )

    return b"".join(messages_bytes)


def test_reader_parses_supported_messages_sequence():
    stream = io.BytesIO(_sample_messages_bytes())
    msgs = list(ITCHReader(stream))

    assert isinstance(msgs[0], SystemEvent)
    assert msgs[0].event == "O"

    assert isinstance(msgs[1], StockDirectory)
    assert msgs[1].stock == "AAPL"
    assert msgs[1].round_lot_size == 100

    assert isinstance(msgs[2], TradingAction)
    assert msgs[2].trading_state == "H"
    assert msgs[2].reason.strip() == "12"

    assert isinstance(msgs[3], AddOrder)
    assert msgs[3].order_id == 111
    assert msgs[3].side.value == "B"
    assert msgs[3].price == 12345

    assert isinstance(msgs[4], AddOrderMPID)
    assert msgs[4].mpid == "ABCD"

    assert isinstance(msgs[5], Execute)
    assert msgs[5].match_number == 3333

    assert isinstance(msgs[6], ExecuteWithPrice)
    assert msgs[6].price == 12346

    assert isinstance(msgs[7], Cancel)
    assert msgs[7].canceled_shares == 2

    assert isinstance(msgs[8], Delete)
    assert msgs[8].order_id == 222

    assert isinstance(msgs[9], Replace)
    assert msgs[9].new_order_id == 333

    assert isinstance(msgs[10], Trade)
    assert msgs[10].stock == "NFLX"
    assert msgs[10].side.value == "S"

    assert isinstance(msgs[11], Cross)
    assert msgs[11].cross_type == "O"

    assert isinstance(msgs[12], BrokenTrade)
    assert msgs[12].match_number == 9999


def test_truncated_message_raises():
    valid = _sample_messages_bytes()
    truncated = valid[:-1]
    with pytest.raises(ITCHDecodeError):
        list(ITCHReader(io.BytesIO(truncated)))


def test_unknown_message_type_raises():
    body = b"\x00" * 11
    unknown = b"Z" + (len(body) + 3).to_bytes(2, "big") + body
    with pytest.raises(ITCHDecodeError):
        list(ITCHReader(io.BytesIO(unknown)))
