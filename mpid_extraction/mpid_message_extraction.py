from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from mpid_latency.ingest import write_itch_stream_from_pcap
from mpid_latency.parser import ITCHReader
from mpid_latency.messages import AddOrderMPID

def process_pcap_to_parquet(pcap_path, output_path):
    """
    Create temporary ITCH file, parse it, then delete.
    """
    pcap_path = Path(pcap_path)
    output_path = Path(output_path)
    
    # Temporary ITCH file (will be deleted)
    itch_temp = pcap_path.parent / f".temp_{pcap_path.stem}.bin"
    
    try:
        # Extract ITCH from pcap (happens once)
        write_itch_stream_from_pcap(pcap_path, itch_temp)
        
        # Parse and filter (happens once)
        messages = []
        for msg in ITCHReader(str(itch_temp)):
            if isinstance(msg, AddOrderMPID):
                messages.append({
                    'locate': msg.locate,
                    'tracking_number': msg.tracking_number,
                    'timestamp': msg.timestamp,
                    'order_id': msg.order_id,
                    'side': msg.side.value,
                    'shares': msg.shares,
                    'stock': msg.stock,
                    'price': msg.price,
                    'mpid': msg.mpid,
                })
        
        #Save to compressed Parquet
        table = pa.Table.from_pylist(messages)
        pq.write_table(table, output_path, compression='zstd', compression_level=9)
        
        print(f"Saved {len(messages)} AddOrderMPID messages to {output_path.name}")
        return len(messages)
        
    finally:
        # Always clean up temp file
        itch_temp.unlink(missing_ok=True)

