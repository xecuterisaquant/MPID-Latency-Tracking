"""
Multi-Day, Multi-Contract Latency Pipeline
Optimized for processing 3/10-3/21 data with March and June contracts
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from numba import njit
import sys
import duckdb

sys.path.append(str(Path(__file__).parent.parent))
from config import (
    ALL_DATES, CONTRACTS, EDT_OFFSET_NS, MATCHING_WINDOW_NS,
    CHUNK_SIZE, OUTPUT_DIR, PARQUET_ENGINE, PARQUET_COMPRESSION,
    MIN_OBSERVATIONS_PER_DAY, MAX_OBSERVATIONS_PER_DAY
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@njit(parallel=False, fastmath=True)
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


def load_es_trades_for_date(es_dir: Path, trade_date: date, 
                            contracts: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Load ES trades for a specific date
    """
    # Try different filename patterns
    patterns = [
        f"trade_events_{trade_date:%Y%m%d}.parquet",
        f"es_trades_{trade_date:%Y%m%d}.parquet",
        f"es_{trade_date:%Y-%m-%d}.parquet",
        f"ES_{trade_date:%Y%m%d}.csv"
    ]
    
    for pattern in patterns:
        filepath = es_dir / pattern
        if filepath.exists():
            logger.info(f"  Loading ES trades: {filepath.name}")
            
            if filepath.suffix == '.parquet':
                df = pd.read_parquet(filepath)
            else:
                df = pd.read_csv(filepath)
            
            # Standardize to trade_time_ns column
            if 'transact_time_ns' in df.columns:
                df = df.rename(columns={'transact_time_ns': 'trade_time_ns'})
            
            # Apply EDT offset (critical fix)
            df['trade_time_ns'] = df['trade_time_ns'] + EDT_OFFSET_NS
            
            # Map security_id to contract names
            if 'security_id' in df.columns and 'contract' not in df.columns:
                # Based on actual data: 5002 = ESH25 (March), 4916 = ?
                # You'll need to verify 4916 - might be ESM25 (June) or previous contract
                contract_map = {
                    5002: 'ESH25',  # March 2025
                    5003: 'ESM25',  # June 2025  
                    4916: 'ESH25'   # Assuming this is also March (verify!)
                }
                df['contract'] = df['security_id'].map(contract_map).fillna('UNKNOWN')
            
            # Filter to specific contracts if requested
            if contracts:
                df = df[df['contract'].isin(contracts)]
            
            # Add date column
            df['date'] = trade_date
            
            # We don't have symbol column in ES data - it's all ES futures
            # Add placeholder for matching logic
            df['symbol'] = 'ES'
            
            return df.sort_values('trade_time_ns').reset_index(drop=True)
    
    raise FileNotFoundError(f"No ES trades file found for {trade_date} in {es_dir}")


def load_nasdaq_events_for_date(nasdaq_dir: Path, trade_date: date,
                                symbols: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Load NASDAQ MPID events for a specific date
    BLAZING FAST: Uses DuckDB to query parquet files with SQL filtering
    """
    date_folder = nasdaq_dir / f"{trade_date:%Y%m%d}"
    
    if date_folder.exists():
        parquet_files = list(date_folder.rglob("*.parquet"))
        
        if parquet_files:
            logger.info(f"  Loading NASDAQ events from {len(parquet_files)} files...")
            
            # Use DuckDB to query parquet files with SQL filtering
            con = duckdb.connect(database=':memory:')
            
            # Build file pattern for DuckDB
            pattern = str(date_folder / "**" / "*.parquet").replace('\\', '/')
            
            # SQL query to filter at source
            if symbols:
                symbol_list = "', '".join(symbols)
                symbol_filter = f"AND symbol IN ('{symbol_list}')"
            else:
                symbol_filter = ""
            
            query = f"""
                SELECT 
                    event_time_ns as nasdaq_time_ns,
                    message_type as event_type,
                    mpid,
                    symbol
                FROM read_parquet('{pattern}')
                WHERE message_type IN ('AddOrderMPID', 'Replace', 'Delete')
                {symbol_filter}
                ORDER BY event_time_ns
            """
            
            logger.info(f"  Querying with DuckDB (filtering MPID events)...")
            df = con.execute(query).df()
            con.close()
            
            logger.info(f"  Loaded {len(df):,} NASDAQ events (sorted by DuckDB)")
            return df
    
    raise FileNotFoundError(f"No NASDAQ events file found for {trade_date} in {nasdaq_dir}")


def match_single_day(es_trades: pd.DataFrame, nasdaq_events: pd.DataFrame,
                     trade_date: date, contract: str) -> pd.DataFrame:
    """
    Match ES trades to NASDAQ events for a single day using Numba-compiled matching
    FAST: Uses integer encoding and Numba JIT compilation for near-C performance
    """
    logger.info(f"  Matching {len(es_trades):,} ES trades ({contract}) to {len(nasdaq_events):,} NASDAQ events...")
    
    # Convert to numpy arrays
    es_timestamps = es_trades['trade_time_ns'].values.astype(np.int64)
    nasdaq_timestamps = nasdaq_events['nasdaq_time_ns'].values.astype(np.int64)
    
    # Encode symbols, MPIDs, and event types as integer IDs for Numba
    symbol_categories = pd.Categorical(nasdaq_events['symbol'])
    mpid_categories = pd.Categorical(nasdaq_events['mpid'])
    event_type_categories = pd.Categorical(nasdaq_events['event_type'])
    
    nasdaq_symbol_ids = symbol_categories.codes.astype(np.int32)
    nasdaq_mpid_ids = mpid_categories.codes.astype(np.int32)
    nasdaq_event_type_ids = event_type_categories.codes.astype(np.int32)
    
    # Call Numba-compiled function
    (es_times, mpid_ids, symbol_ids, event_type_ids, 
     latencies, nasdaq_times, result_count) = _find_latencies_numba(
        es_timestamps,
        nasdaq_timestamps,
        nasdaq_symbol_ids,
        nasdaq_mpid_ids,
        nasdaq_event_type_ids,
        MATCHING_WINDOW_NS
    )
    
    if result_count == 0:
        logger.warning(f"  No matches found for {trade_date}")
        return pd.DataFrame()
    
    logger.info(f"  Found {result_count:,} matches")
    
    # Decode categorical IDs back to strings
    df = pd.DataFrame({
        'es_trade_time_ns': es_times,
        'mpid': pd.Categorical.from_codes(mpid_ids, mpid_categories.categories),
        'symbol': pd.Categorical.from_codes(symbol_ids, symbol_categories.categories),
        'event_type': pd.Categorical.from_codes(event_type_ids, event_type_categories.categories),
        'latency_ns': latencies,
        'nasdaq_time_ns': nasdaq_times,
        'contract': contract,
        'date': trade_date,
        'latency_ms': latencies / 1_000_000
    })
    
    return df


def process_multi_day(es_dir: Path, nasdaq_dir: Path, 
                     dates: List[date],
                     contracts: Optional[List[str]] = None,
                     symbols: Optional[List[str]] = None,
                     output_file: Optional[Path] = None,
                     save_incremental: bool = True) -> pd.DataFrame:
    """
    Process multiple days of data with multiple contracts per day
    OPTIMIZED: Loads NASDAQ once per day, matches against each contract separately
    """
    logger.info(f"Starting multi-day processing: {len(dates)} dates")
    logger.info(f"  Date range: {min(dates)} to {max(dates)}")
    if contracts:
        logger.info(f"  Contracts: {', '.join(contracts)}")
    if symbols:
        logger.info(f"  Symbols: {', '.join(symbols)}")
    
    all_results = []
    
    for i, trade_date in enumerate(dates, 1):
        logger.info(f"\n[{i}/{len(dates)}] Processing {trade_date}...")
        
        try:
            # Load NASDAQ data ONCE per day (shared across all contracts)
            nasdaq_events = load_nasdaq_events_for_date(nasdaq_dir, trade_date, symbols=symbols)
            
            # Load ALL ES trades for this date (all contracts)
            es_trades_all = load_es_trades_for_date(es_dir, trade_date, contracts=contracts)
            
            # Process each contract separately
            for contract in (contracts or ['ESH25', 'ESM25']):
                # Filter to this contract
                es_trades_contract = es_trades_all[es_trades_all['contract'] == contract]
                
                if len(es_trades_contract) == 0:
                    logger.info(f"  No {contract} trades found")
                    continue
                
                logger.info(f"  Processing {contract}...")
                
                # Match using Numba-compiled function
                contract_results = match_single_day(es_trades_contract, nasdaq_events, trade_date, contract)
                
                if len(contract_results) == 0:
                    logger.warning(f"  No matches for {contract}")
                    continue
                
                # Validate
                n_obs = len(contract_results)
                if n_obs < MIN_OBSERVATIONS_PER_DAY:
                    logger.warning(f"  Only {n_obs:,} observations - expected >{MIN_OBSERVATIONS_PER_DAY:,}")
                elif n_obs > MAX_OBSERVATIONS_PER_DAY:
                    logger.warning(f"  {n_obs:,} observations - expected <{MAX_OBSERVATIONS_PER_DAY:,}")
                
                all_results.append(contract_results)
                
                # Save incremental per contract
                if save_incremental and output_file:
                    day_file = output_file.parent / f"latencies_{trade_date:%Y%m%d}_{contract}.parquet"
                    contract_results.to_parquet(day_file, engine=PARQUET_ENGINE, compression=PARQUET_COMPRESSION)
                    logger.info(f"  Saved {contract} results: {day_file.name}")
        
        except FileNotFoundError as e:
            logger.error(f"  Missing data for {trade_date}: {e}")
            continue
        except Exception as e:
            logger.error(f"  Error processing {trade_date}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Combine all results
    if len(all_results) == 0:
        logger.error("No data processed successfully")
        return pd.DataFrame()
    
    logger.info(f"\nCombining {len(all_results)} days of results...")
    combined_df = pd.concat(all_results, ignore_index=True)
    
    # Add enrichments
    combined_df['hour'] = pd.to_datetime(combined_df['nasdaq_time_ns'], unit='ns').dt.hour
    combined_df['day_of_week'] = pd.to_datetime(combined_df['nasdaq_time_ns'], unit='ns').dt.day_name()
    
    logger.info(f"Total: {len(combined_df):,} latency observations across {len(dates)} days")
    
    # Save final combined file
    if output_file:
        logger.info(f"Saving combined results to {output_file}...")
        combined_df.to_parquet(output_file, engine=PARQUET_ENGINE, compression=PARQUET_COMPRESSION)
        logger.info(f"Saved: {output_file}")
    
    return combined_df


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-day, multi-contract latency pipeline')
    parser.add_argument('--es-dir', type=Path, required=True, help='Directory with ES trade files')
    parser.add_argument('--nasdaq-dir', type=Path, required=True, help='Directory with NASDAQ event files')
    parser.add_argument('--start-date', type=str, default='2025-03-10', help='Start date YYYY-MM-DD')
    parser.add_argument('--end-date', type=str, default='2025-03-21', help='End date YYYY-MM-DD')
    parser.add_argument('--contracts', nargs='+', help='Contracts to process (e.g., ESH25 ESM25)')
    parser.add_argument('--symbols', nargs='+', help='Symbols to process (e.g., SPY QQQ)')
    parser.add_argument('--output', type=Path, default=OUTPUT_DIR / 'latencies_combined.parquet',
                       help='Output file path')
    args = parser.parse_args()
    
    # Generate date range
    start = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    end = datetime.strptime(args.end_date, '%Y-%m-%d').date()
    
    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # Weekdays only
            dates.append(current)
        current += timedelta(days=1)
    
    # TESTING: Limit to first 2 days for faster debugging
    # Remove this line when ready for full run
    dates = dates[:2]
    
    logger.info(f"Processing {len(dates)} days (limited for testing)")
    
    # Process
    process_multi_day(
        es_dir=args.es_dir,
        nasdaq_dir=args.nasdaq_dir,
        dates=dates,
        contracts=args.contracts,
        symbols=args.symbols,
        output_file=args.output,
        save_incremental=True
    )
