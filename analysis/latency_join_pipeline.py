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
from numba import njit, prange

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
        
        # Convert event_time_ns to absolute timestamp
        # NOTE: The NASDAQ parquet files have timestamps multiplied by 1000 (extraction bug)
        # ITCH timestamps are nanoseconds since midnight, but were multiplied by 1000
        # So we divide by 1000 first, then add to Eastern midnight
        eastern_midnight = pd.Timestamp(self.trade_date.date(), tz='America/New_York')
        df['event_time_absolute_ns'] = (
            eastern_midnight.value +      # Unix epoch ns for midnight Eastern Time
            (df['event_time_ns'] / 1000)  # Correct the 1000x multiplier, then add
        )
        
        # Sort by timestamp for efficient searching
        df = df.sort_values('event_time_absolute_ns').reset_index(drop=True)
        
        logger.info(f"  Timestamp conversion:")
        logger.info(f"    Original range: {df['event_time_ns'].min():,} to {df['event_time_ns'].max():,}")
        logger.info(f"    Absolute range: {df['event_time_absolute_ns'].min():,} to {df['event_time_absolute_ns'].max():,}")
        
        return df
    
    @staticmethod
    @njit(parallel=False, fastmath=True)  # Disable parallel due to result_count race condition
    def _find_latencies_numba(
        es_timestamps: np.ndarray,
        nasdaq_timestamps: np.ndarray,
        nasdaq_symbol_ids: np.ndarray,
        nasdaq_mpid_ids: np.ndarray,
        nasdaq_event_type_ids: np.ndarray,
        max_latency_ns: int
    ):
        """
        Numba-compiled function for fast latency computation.
        Uses near-C performance for the hot loop.
        
        Returns parallel arrays of results.
        """
        n_es = len(es_timestamps)
        
        # Pre-allocate result arrays (max size estimate)
        max_results = n_es * 100  # Assume avg 100 MPIDs per trade
        
        es_times = np.empty(max_results, dtype=np.int64)
        mpid_ids = np.empty(max_results, dtype=np.int32)
        symbol_ids = np.empty(max_results, dtype=np.int32)
        event_type_ids = np.empty(max_results, dtype=np.int32)
        latencies = np.empty(max_results, dtype=np.int64)
        nasdaq_times = np.empty(max_results, dtype=np.int64)
        
        result_count = 0
        
        # Process trades sequentially (still much faster than pure Python)
        for i in range(n_es):
            es_time = es_timestamps[i]
            
            # Binary search for first event after ES trade
            search_idx = np.searchsorted(nasdaq_timestamps, es_time)
            
            # Find end of search window
            end_time = es_time + max_latency_ns
            end_idx = np.searchsorted(nasdaq_timestamps, end_time)
            
            if search_idx >= len(nasdaq_timestamps):
                continue
            
            # Track first occurrence of each (MPID, symbol) pair
            seen_pairs = np.empty((1000, 2), dtype=np.int32)  # Max 1000 unique pairs per trade
            n_seen = 0
            
            # Iterate through window
            for j in range(search_idx, end_idx):
                mpid_id = nasdaq_mpid_ids[j]
                symbol_id = nasdaq_symbol_ids[j]
                
                # Check if we've seen this (MPID, symbol) pair
                is_new = True
                for k in range(n_seen):
                    if seen_pairs[k, 0] == mpid_id and seen_pairs[k, 1] == symbol_id:
                        is_new = False
                        break
                
                if is_new:
                    # First occurrence of this (MPID, symbol)
                    if n_seen < 1000:
                        seen_pairs[n_seen, 0] = mpid_id
                        seen_pairs[n_seen, 1] = symbol_id
                        n_seen += 1
                    
                    # Record this latency
                    if result_count < max_results:
                        es_times[result_count] = es_time
                        mpid_ids[result_count] = mpid_id
                        symbol_ids[result_count] = symbol_id
                        event_type_ids[result_count] = nasdaq_event_type_ids[j]
                        latencies[result_count] = nasdaq_timestamps[j] - es_time
                        nasdaq_times[result_count] = nasdaq_timestamps[j]
                        result_count += 1
        
        # Trim to actual size
        return (
            es_times[:result_count],
            mpid_ids[:result_count],
            symbol_ids[:result_count],
            event_type_ids[:result_count],
            latencies[:result_count],
            nasdaq_times[:result_count],
            result_count
        )
    
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
        logger.info("  Using Numba JIT compilation for near-C performance...")
        
        max_latency_ns = int(max_latency_seconds * 1e9)
        
        # Pre-compute arrays and encode categorical data as integers
        es_timestamps = es_trades['trade_time_ns'].values.astype(np.int64)
        nasdaq_timestamps = nasdaq_events['event_time_absolute_ns'].values.astype(np.int64)
        
        # Encode symbols, MPIDs, and event types as integer IDs
        symbol_categories = pd.Categorical(nasdaq_events['symbol'])
        mpid_categories = pd.Categorical(nasdaq_events['mpid'])
        event_type_categories = pd.Categorical(nasdaq_events['message_type'])
        
        nasdaq_symbol_ids = symbol_categories.codes.astype(np.int32)
        nasdaq_mpid_ids = mpid_categories.codes.astype(np.int32)
        nasdaq_event_type_ids = event_type_categories.codes.astype(np.int32)
        
        # Call Numba-compiled function
        (es_times, mpid_ids, symbol_ids, event_type_ids, 
         latencies, nasdaq_times, result_count) = self._find_latencies_numba(
            es_timestamps,
            nasdaq_timestamps,
            nasdaq_symbol_ids,
            nasdaq_mpid_ids,
            nasdaq_event_type_ids,
            max_latency_ns
        )
        
        logger.info(f"✓ Computed {result_count:,} latencies")
        
        # Decode categorical IDs back to strings
        df = pd.DataFrame({
            'es_trade_time_ns': es_times,
            'mpid': pd.Categorical.from_codes(mpid_ids, mpid_categories.categories),
            'symbol': pd.Categorical.from_codes(symbol_ids, symbol_categories.categories),
            'event_type': pd.Categorical.from_codes(event_type_ids, event_type_categories.categories),
            'latency_ns': latencies,
            'nasdaq_event_time_ns': nasdaq_times,
        })
        
        return df
    
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
