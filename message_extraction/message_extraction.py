from pathlib import Path
from collections import Counter
import io
import pyarrow as pa
import pyarrow.parquet as pq
from mpid_latency.ingest import iter_filtered_itch_messages_from_pcap
from mpid_latency.parser import ITCHReader
from mpid_latency import messages


def _to_str(value) -> str:
    """Convert raw bytes or strings to a stripped ASCII string."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode('ascii', errors='ignore')
    return str(value).rstrip()


def _to_side(value) -> str:
    """Normalize Side (enum/str/bytes/int) to its single-character representation."""
    if value is None:
        return ""
    if hasattr(value, 'value'):
        return str(value.value)
    if isinstance(value, bytes):
        return value.decode('ascii', errors='ignore').strip()
    if isinstance(value, int):
        try:
            return chr(value)
        except ValueError:
            return str(value)
    return str(value).strip()

# Mapping from ITCH spec letter codes to message classes
ITCH_MESSAGE_MAP = {
    'S': messages.SystemEvent,
    'R': messages.StockDirectory,
    'H': messages.TradingAction,
    'A': messages.AddOrder,
    'F': messages.AddOrderMPID,
    'E': messages.Execute,
    'C': messages.ExecuteWithPrice,
    'X': messages.Cancel,
    'D': messages.Delete,
    'U': messages.Replace,
    'P': messages.Trade,
    'Q': messages.Cross,
    'B': messages.BrokenTrade,
    'I': messages.NOII,
    'Y': messages.RegSHORestriction,
    'L': messages.MarketParticipantPosition,
    'V': messages.MWCBDeclineLevel,
    'W': messages.MWCBStatus,
    'K': messages.IPOQuotingPeriod,
    'J': messages.LULDAuctionCollar,
}

def get_message_types_from_codes(codes):
    """Convert ITCH letter codes to message type classes."""
    return tuple(ITCH_MESSAGE_MAP[code] for code in codes)

def process_pcap_to_parquet(pcap_path, output_path, message_type_codes):
    """
    Parse a pcap, track AddOrderMPID orders, and emit enriched events with schema:
    event_time_ns | mpid | symbol | side | price | size | message_type

    Cancel/Delete/Replace rows are only emitted when a matching AddOrderMPID has
    already been observed, ensuring MPID/symbol/side/price context is preserved.
    """
    pcap_path = Path(pcap_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Track Add orders for enrichment: order_id -> (mpid, symbol, side, price, size)
    order_book = {}
    extracted_events = []
    extracted_counts = Counter()
    total_messages = 0

    # Pre-filter to requested message types (byte-level for speed)
    itch_buffer = io.BytesIO()
    for msg_bytes in iter_filtered_itch_messages_from_pcap(pcap_path, set(message_type_codes)):
        itch_buffer.write(msg_bytes)
    itch_buffer.seek(0)

    for msg in ITCHReader(itch_buffer):
        total_messages += 1
        msg_type = type(msg)
        msg_type_name = msg_type.__name__

        # Helper to append a normalized event row
        def _append_event(mpid: str, symbol: str, side: str, price: int, size: int, ts: int):
            extracted_events.append({
                'event_time_ns': ts * 1000,
                'mpid': mpid,
                'symbol': symbol,
                'side': side,
                'price': price,
                'size': size,
                'message_type': msg_type_name,
            })
            extracted_counts[msg_type_name] += 1

        if isinstance(msg, messages.AddOrderMPID):
            mpid = _to_str(msg.mpid)
            symbol = _to_str(msg.stock)
            side = _to_side(msg.side)
            order_book[msg.order_id] = (mpid, symbol, side, msg.price, msg.shares)
            _append_event(mpid, symbol, side, msg.price, msg.shares, msg.timestamp)

        elif isinstance(msg, messages.Cancel):
            existing = order_book.get(msg.order_id)
            if existing:
                mpid, symbol, side, price, _ = existing
                _append_event(mpid, symbol, side, price, msg.canceled_shares, msg.timestamp)

        elif isinstance(msg, messages.Delete):
            existing = order_book.pop(msg.order_id, None)
            if existing:
                mpid, symbol, side, price, size = existing
                _append_event(mpid, symbol, side, price, size, msg.timestamp)

        elif isinstance(msg, messages.Replace):
            existing = order_book.pop(msg.order_id, None)
            if existing:
                mpid, symbol, side, _, _ = existing
                _append_event(mpid, symbol, side, msg.price, msg.shares, msg.timestamp)
                order_book[msg.new_order_id] = (mpid, symbol, side, msg.price, msg.shares)

    if extracted_events:
        table = pa.Table.from_pylist(extracted_events)
        pq.write_table(table, output_path, compression='zstd', compression_level=3)

    return dict(extracted_counts), len(extracted_events), total_messages

