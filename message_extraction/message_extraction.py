from pathlib import Path
from collections import Counter
import io
import pyarrow as pa
import pyarrow.parquet as pq
from mpid_latency.ingest import iter_filtered_itch_messages_from_pcap
from mpid_latency.parser import ITCHReader
from mpid_latency import messages

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
    Parse pcap and filter by message types at byte level (fast pre-filtering).
    
    Args:
        pcap_path: Path to input pcap file
        output_path: Path to output parquet file
        message_type_codes: List of ITCH spec letter codes (e.g., ['F', 'L'])
    
    Returns:
        tuple of (message_counts_dict, total_count)
        where message_counts_dict is {message_type_name: count}
    """
    pcap_path = Path(pcap_path)
    output_path = Path(output_path)
    
    # Convert codes to message types
    message_types = get_message_types_from_codes(message_type_codes)
    
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    extracted_messages = []
    message_counts = Counter()
    total_messages = 0
    
    # Use filtered iterator - only extracts requested message types at byte level (FAST!)
    # This skips parsing/unpacking all other message types
    itch_buffer = io.BytesIO()
    for msg_bytes in iter_filtered_itch_messages_from_pcap(pcap_path, set(message_type_codes)):
        itch_buffer.write(msg_bytes)
    
    # Reset buffer position to start
    itch_buffer.seek(0)
    
    # Get field names once (avoid repeated introspection)
    fields_cache = {}
    
    # Now ITCHReader only parses the pre-filtered messages
    for msg in ITCHReader(itch_buffer):
        total_messages += 1
        
        # Messages are already filtered at byte level, so all should match
        msg_type = type(msg)
        msg_type_name = msg_type.__name__
        message_counts[msg_type_name] += 1
        
        # Cache field names per message type
        if msg_type not in fields_cache:
            fields_cache[msg_type] = tuple(msg.__dataclass_fields__.keys())
        
        # Extract fields and convert enums to strings
        msg_dict = {}
        for field in fields_cache[msg_type]:
            value = getattr(msg, field)
            # Convert enums to their string values
            if hasattr(value, 'value'):
                value = value.value
            msg_dict[field] = value
        extracted_messages.append(msg_dict)
    
    # Check if we found any messages
    if not extracted_messages:
        # Return empty counts for all requested types
        empty_counts = {ITCH_MESSAGE_MAP[code].__name__: 0 for code in message_type_codes}
        return empty_counts, total_messages
    
    # Save to compressed Parquet (compression level 3 for speed)
    table = pa.Table.from_pylist(extracted_messages)
    pq.write_table(table, output_path, compression='zstd', compression_level=3)
    
    return dict(message_counts), total_messages

