"""
Latency Join Pipeline: CME ES Trades → NASDAQ MPID Events

This pipeline computes the latency from ES trade events to the first subsequent
MPID action (add/cancel/replace) for each (MPID, symbol) pair.

Algorithm:
1. Load ES trades (stimulus events)
2. Load NASDAQ MPID events (response events)  
3. For each ES trade:
   - Find first NASDAQ event after ES timestamp
   - Group by (MPID, symbol) to avoid double-counting
4. Compute latency in nanoseconds
5. Enrich with time-of-day features

Output schema:
    es_trade_time_ns | mpid | symbol | event_type | latency_ns | hour_of_day | date

VM-Optimized: Memory-efficient chunking, parallel processing support
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Optional, Tuple, List
import logging
import sys

# Add project root to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    TARGET_SYMBOLS, MAX_LATENCY_SECONDS, CHUNK_SIZE,
    ES_SECURITY_IDS, PARQUET_COMPRESSION, PARQUET_COMPRESSION_LEVEL,
    NUM_WORKERS
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LatencyJoinPipeline:
    """
    Efficient pipeline for computing ES → NASDAQ latencies.
    Uses chunking and binary search for memory-efficient processing.
    """
    
    def __init__(self, trade_date: str = "2025-03-10"):
        """
        Initialize pipeline with trade date for timestamp conversion.
        
        Args:
            trade_date: Date string in YYYY-MM-DD format
        """
        self.trade_date = pd.Timestamp(trade_date, tz='UTC')
        logger.info(f"Initialized LatencyJoinPipeline for {trade_date}")
    
    def load_es_trades(self, filepath: Path, min_trade_size: int = 1) -> pd.DataFrame:
        """
        Load CME ES trade events.
        
        Actual schema (from exploration):
            - transact_time_ns: Trade timestamp (Unix epoch nanoseconds)
            - trade_px: Trade price (float)
            - trade_sz: Trade size (int)
            - security_id: CME security ID (5002=ES, 42005347=MES)
            - aggressor_side: Buy/Sell/Unknown
            - ts_pcap: Packet capture timestamp
        
        Returns:
            DataFrame with standardized columns and sorted by timestamp
        """
        logger.info(f"Loading ES trades from {filepath}")
        
        df = pd.read_parquet(filepath)
        logger.info(f"  Loaded {len(df):,} ES trades")
        
        # Standardize column names to match pipeline expectations
        df = df.rename(columns={
            'transact_time_ns': 'trade_time_ns',
            'trade_px': 'price',
            'trade_sz': 'size',
        })
        
        # Add contract name from security_id
        df['contract'] = df['security_id'].map(ES_SECURITY_IDS).fillna('UNKNOWN')
        
        # Filter by minimum trade size
        if min_trade_size > 1:
            orig_len = len(df)
            df = df[df['size'] >= min_trade_size].copy()
            logger.info(f"  Filtered to {len(df):,} trades (>= {min_trade_size} contracts, removed {orig_len - len(df):,})")
        
        # Sort by timestamp for efficient processing
        df = df.sort_values('trade_time_ns').reset_index(drop=True)
        
        logger.info(f"  Time range: {df['trade_time_ns'].min():,} to {df['trade_time_ns'].max():,}")
        logger.info(f"  Span: {(df['trade_time_ns'].max() - df['trade_time_ns'].min()) / 1e9:.2f} seconds")
        
        # Contract breakdown
        logger.info(f"  Contract distribution:")
        for contract, count in df['contract'].value_counts().items():
            logger.info(f"    {contract}: {count:,} trades")
        
        return df
    
    def load_nasdaq_events(self, filepath: Path, target_symbols: Optional[list] = None) -> pd.DataFrame:
        """
        Load NASDAQ MPID events.
        
        Expected columns:
            - event_time_ns: Event timestamp (nanoseconds since midnight)
            - mpid: Market participant ID
            - symbol: Stock ticker
            - message_type: AddOrderMPID, Replace, Cancel, Delete
            - side: B/S
            - price: Price in 1/10000 units
            - size: Share quantity
        
        Args:
            filepath: Path to parquet file
            target_symbols: Optional list to filter symbols
        
        Returns:
            DataFrame sorted by timestamp
        """
        logger.info(f"Loading NASDAQ events from {filepath}")
        
        df = pd.read_parquet(filepath)
        logger.info(f"  Loaded {len(df):,} NASDAQ events")
        
        # Filter to target symbols if specified
        if target_symbols:
            df = df[df['symbol'].isin(target_symbols)].copy()
            logger.info(f"  Filtered to {len(df):,} events for target symbols: {target_symbols}")
        
        # Convert event_time_ns (ns since midnight) to absolute timestamp
        # Assume NASDAQ timestamps are nanoseconds since midnight of trade_date
        df['event_time_absolute_ns'] = (
            self.trade_date.value +  # Unix epoch ns for midnight of trade_date
            df['event_time_ns']      # ns since midnight
        )
        
        # Sort by timestamp for efficient searching
        df = df.sort_values('event_time_absolute_ns').reset_index(drop=True)
        
        logger.info(f"  Timestamp conversion:")
        logger.info(f"    Original range: {df['event_time_ns'].min():,} to {df['event_time_ns'].max():,}")
        logger.info(f"    Absolute range: {df['event_time_absolute_ns'].min():,} to {df['event_time_absolute_ns'].max():,}")
        
        return df
    
    def compute_latencies(
        self,
        es_trades: pd.DataFrame,
        nasdaq_events: pd.DataFrame,
        max_latency_seconds: float = 10.0,
        chunk_size: int = 10000
    ) -> pd.DataFrame:
        """
        Compute latencies from ES trades to first NASDAQ MPID events.
        
        For each ES trade, finds the first NASDAQ event that:
        1. Occurs AFTER the ES trade
        2. Matches the symbol (if ES has symbol info)
        3. Is within max_latency_seconds
        
        Uses chunking to avoid memory issues with large datasets.
        
        Args:
            es_trades: ES trade DataFrame
            nasdaq_events: NASDAQ event DataFrame (already sorted)
            max_latency_seconds: Maximum latency window to search
            chunk_size: Number of ES trades to process per chunk
        
        Returns:
            DataFrame with latency measurements
        """
        logger.info("Computing latencies...")
        logger.info(f"  ES trades: {len(es_trades):,}")
        logger.info(f"  NASDAQ events: {len(nasdaq_events):,}")
        logger.info(f"  Max latency window: {max_latency_seconds}s")
        
        max_latency_ns = int(max_latency_seconds * 1e9)
        
        # Pre-compute for efficiency
        nasdaq_timestamps = nasdaq_events['event_time_absolute_ns'].values
        nasdaq_symbols = nasdaq_events['symbol'].values
        nasdaq_mpids = nasdaq_events['mpid'].values
        nasdaq_types = nasdaq_events['message_type'].values
        
        results = []
        num_chunks = (len(es_trades) + chunk_size - 1) // chunk_size
        
        for chunk_idx in range(num_chunks):
            start_idx = chunk_idx * chunk_size
            end_idx = min((chunk_idx + 1) * chunk_size, len(es_trades))
            chunk = es_trades.iloc[start_idx:end_idx]
            
            for idx, trade in chunk.iterrows():
                es_time = trade['trade_time_ns']
                
                # Binary search for first event after ES trade
                search_idx = np.searchsorted(nasdaq_timestamps, es_time, side='right')
                
                # Search within latency window
                end_search_idx = np.searchsorted(
                    nasdaq_timestamps,
                    es_time + max_latency_ns,
                    side='right'
                )
                
                if search_idx >= len(nasdaq_timestamps):
                    continue  # No events after this trade
                
                # Get all events in window
                window_events = nasdaq_events.iloc[search_idx:end_search_idx]
                
                if len(window_events) == 0:
                    continue
                
                # Group by (MPID, symbol) and take first event for each
                # This ensures we measure first reaction per MPID per symbol
                for (mpid, symbol), group in window_events.groupby(['mpid', 'symbol']):
                    first_event = group.iloc[0]
                    latency_ns = first_event['event_time_absolute_ns'] - es_time
                    
                    results.append({
                        'es_trade_time_ns': es_time,
                        'mpid': mpid,
                        'symbol': symbol,
                        'event_type': first_event['message_type'],
                        'latency_ns': latency_ns,
                        'nasdaq_event_time_ns': first_event['event_time_absolute_ns'],
                        'side': first_event.get('side', None),
                    })
            
            if (chunk_idx + 1) % 10 == 0:
                logger.info(f"  Processed {end_idx:,}/{len(es_trades):,} trades ({len(results):,} latencies so far)")
        
        logger.info(f"✓ Computed {len(results):,} latencies")
        
        return pd.DataFrame(results)
    
    def enrich_with_features(self, latencies: pd.DataFrame) -> pd.DataFrame:
        """
        Add time-of-day and other derived features.
        
        Args:
            latencies: Raw latency DataFrame
        
        Returns:
            Enriched DataFrame with additional columns
        """
        logger.info("Enriching with features...")
        
        df = latencies.copy()
        
        # Convert to datetime for feature extraction
        df['es_trade_datetime'] = pd.to_datetime(df['es_trade_time_ns'], unit='ns', utc=True)
        df['es_trade_datetime_et'] = df['es_trade_datetime'].dt.tz_convert('America/New_York')
        
        # Time-of-day features
        df['hour_of_day'] = df['es_trade_datetime_et'].dt.hour
        df['minute_of_hour'] = df['es_trade_datetime_et'].dt.minute
        df['date'] = df['es_trade_datetime_et'].dt.date
        
        # Convert latency to microseconds for readability
        df['latency_us'] = df['latency_ns'] / 1000
        df['latency_ms'] = df['latency_ns'] / 1e6
        
        # Log-scale latency for visualization
        df['latency_log10_ns'] = np.log10(df['latency_ns'].clip(lower=1))
        
        logger.info("  Added features: hour_of_day, latency_us, latency_ms, latency_log10_ns")
        
        return df
    
    def run(
        self,
        es_trades_path: Path,
        nasdaq_events_path: Path,
        output_path: Path,
        target_symbols: Optional[list] = None,
        max_latency_seconds: float = 10.0
    ) -> pd.DataFrame:
        """
        Execute full pipeline.
        
        Args:
            es_trades_path: Path to ES trades parquet
            nasdaq_events_path: Path to NASDAQ events parquet
            output_path: Where to save results
            target_symbols: Optional symbol filter
            max_latency_seconds: Max latency window
        
        Returns:
            Final enriched latency DataFrame
        """
        logger.info("=" * 80)
        logger.info("LATENCY JOIN PIPELINE")
        logger.info("=" * 80)
        
        # Load data
        es_trades = self.load_es_trades(es_trades_path)
        nasdaq_events = self.load_nasdaq_events(nasdaq_events_path, target_symbols)
        
        # Compute latencies
        latencies = self.compute_latencies(
            es_trades,
            nasdaq_events,
            max_latency_seconds=max_latency_seconds
        )
        
        if len(latencies) == 0:
            logger.warning("⚠️  No latencies computed! Check timestamp alignment.")
            return pd.DataFrame()
        
        # Enrich with features
        latencies_enriched = self.enrich_with_features(latencies)
        
        # Save results
        logger.info(f"Saving results to {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        latencies_enriched.to_parquet(
            output_path, 
            index=False, 
            compression=PARQUET_COMPRESSION,
            compression_level=PARQUET_COMPRESSION_LEVEL
        )
        logger.info(f"  ✓ Saved {len(latencies_enriched):,} rows")
        logger.info(f"  💿 {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        logger.info(f"  🗜️  Compression: {PARQUET_COMPRESSION}")
        
        # Print summary statistics
        self._print_summary(latencies_enriched)
        
        logger.info("=" * 80)
        logger.info("✓ PIPELINE COMPLETE")
        logger.info("=" * 80)
        
        return latencies_enriched
    
    def _print_summary(self, df: pd.DataFrame):
        """Print summary statistics."""
        logger.info("\n" + "=" * 80)
        logger.info("LATENCY SUMMARY STATISTICS")
        logger.info("=" * 80)
        
        logger.info(f"\n📊 Overall:")
        logger.info(f"  Total measurements: {len(df):,}")
        logger.info(f"  Unique MPIDs: {df['mpid'].nunique()}")
        logger.info(f"  Unique symbols: {df['symbol'].nunique()}")
        
        logger.info(f"\n⏱️  Latency Distribution (microseconds):")
        percentiles = df['latency_us'].quantile([0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
        logger.info(f"  Mean:   {df['latency_us'].mean():>12,.2f} μs")
        logger.info(f"  Median: {percentiles[0.5]:>12,.2f} μs")
        logger.info(f"  p10:    {percentiles[0.1]:>12,.2f} μs")
        logger.info(f"  p25:    {percentiles[0.25]:>12,.2f} μs")
        logger.info(f"  p75:    {percentiles[0.75]:>12,.2f} μs")
        logger.info(f"  p90:    {percentiles[0.9]:>12,.2f} μs")
        logger.info(f"  p95:    {percentiles[0.95]:>12,.2f} μs")
        logger.info(f"  p99:    {percentiles[0.99]:>12,.2f} μs")
        
        logger.info(f"\n🏷️  Top MPIDs by latency count:")
        for mpid, count in df['mpid'].value_counts().head(10).items():
            pct = 100 * count / len(df)
            median_lat = df[df['mpid'] == mpid]['latency_us'].median()
            logger.info(f"  {mpid:8s}: {count:>8,} measurements ({pct:>5.2f}%) | median: {median_lat:>10,.2f} μs")
        
        logger.info(f"\n📝 Event Types:")
        for evt_type, count in df['event_type'].value_counts().items():
            pct = 100 * count / len(df)
            logger.info(f"  {evt_type:15s}: {count:>8,} ({pct:>5.2f}%)")


def main():
    """Example usage - update paths as needed"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run ES → NASDAQ latency join pipeline')
    parser.add_argument('--es-trades', type=Path, required=True, help='ES trades parquet file')
    parser.add_argument('--nasdaq-events', type=Path, required=True, help='NASDAQ events parquet file')
    parser.add_argument('--output', type=Path, required=True, help='Output parquet file')
    parser.add_argument('--trade-date', type=str, default='2025-03-10', help='Trade date (YYYY-MM-DD)')
    parser.add_argument('--min-trade-size', type=int, default=5, help='Minimum ES trade size')
    
    args = parser.parse_args()
    
    # Initialize and run pipeline
    pipeline = LatencyJoinPipeline(trade_date=args.trade_date)
    
    try:
        logger.info(f"\n🚀 Starting latency join pipeline")
        logger.info(f"  ES trades: {args.es_trades}")
        logger.info(f"  NASDAQ events: {args.nasdaq_events}")
        logger.info(f"  Output: {args.output}")
        logger.info(f"  Trade date: {args.trade_date}")
        logger.info(f"  Workers: {NUM_WORKERS}")
        
        results = pipeline.run(
            es_trades_path=args.es_trades,
            nasdaq_events_path=args.nasdaq_events,
            output_path=args.output,
            target_symbols=TARGET_SYMBOLS,
            max_latency_seconds=MAX_LATENCY_SECONDS
        )
        
        logger.info(f"\n✅ Success! Results saved to {args.output}")
        
    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        logger.error("📝 Check input file paths")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()
