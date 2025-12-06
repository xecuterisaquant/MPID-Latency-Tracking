from pathlib import Path
from collections import Counter
import pyarrow as pa
import pyarrow.parquet as pq
from mpid_latency.ingest import write_itch_stream_from_pcap
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
    Create temporary ITCH file, parse it, filter by message types, then delete temp file.
    
    Args:
        pcap_path: Path to input pcap file
        output_path: Path to output parquet file
        message_type_codes: List of ITCH spec letter codes (e.g., ['F', 'L', 'E'])
    
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
    
    # Temporary ITCH file (will be deleted)
    itch_temp = pcap_path.parent / f".temp_{pcap_path.stem}.bin"
    
    try:
        # Extract ITCH from pcap (happens once)
        write_itch_stream_from_pcap(pcap_path, itch_temp)
        
        # Parse and filter (happens once)
        extracted_messages = []
        message_counts = Counter()
        total_messages = 0
        
        for msg in ITCHReader(str(itch_temp)):
            total_messages += 1
            
            # Check if message is one of the requested types
            if isinstance(msg, message_types):
                msg_type_name = type(msg).__name__
                message_counts[msg_type_name] += 1
                
                # Build dict with common fields
                msg_dict = {
                    'message_type': msg_type_name,
                    'locate': msg.locate,
                    'tracking_number': msg.tracking_number,
                    'timestamp': msg.timestamp,
                }
                
                # Add all remaining fields from the message
                for field in msg.__dataclass_fields__:
                    if field not in msg_dict:
                        value = getattr(msg, field)
                        # Convert enums to string values
                        if hasattr(value, 'value'):
                            value = value.value
                        msg_dict[field] = value
                
                extracted_messages.append(msg_dict)
        
        # Check if we found any messages
        if not extracted_messages:
            # Return empty counts for all requested types
            empty_counts = {ITCH_MESSAGE_MAP[code].__name__: 0 for code in message_type_codes}
            return empty_counts, total_messages
        
        # Save to compressed Parquet
        table = pa.Table.from_pylist(extracted_messages)
        pq.write_table(table, output_path, compression='zstd', compression_level=9)
        
        return dict(message_counts), total_messages
        
    finally:
        # Always clean up temp file
        itch_temp.unlink(missing_ok=True)

