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

sys.path.append(str(Path(__file__).parent.parent))
from config import (
    ALL_DATES, CONTRACTS, EDT_OFFSET_NS, MATCHING_WINDOW_NS,
    CHUNK_SIZE, OUTPUT_DIR, PARQUET_ENGINE, PARQUET_COMPRESSION,
    MIN_OBSERVATIONS_PER_DAY, MAX_OBSERVATIONS_PER_DAY
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@njit(cache=True)
def binary_search_first_after(timestamps: np.ndarray, target: int, max_offset: int) -> int:
    """
    Numba-optimized binary search for first timestamp after target within window
    Returns index or -1 if not found
    """
    if len(timestamps) == 0:
        return -1
    
    # Binary search for insertion point
    left, right = 0, len(timestamps)
    while left < right:
        mid = (left + right) // 2
        if timestamps[mid] <= target:
            left = mid + 1
        else:
            right = mid
    
    # Check if within window
    if left < len(timestamps) and timestamps[left] - target <= max_offset:
        return left
    return -1


def load_es_trades_for_date(es_dir: Path, trade_date: date, 
                            contracts: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Load ES trades for a specific date
    """
    # Try different filename patterns
    patterns = [
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
            
            # Standardize columns
            if 'transact_time_ns' in df.columns:
                df = df.rename(columns={'transact_time_ns': 'trade_time_ns'})
            
            # Apply EDT offset (critical fix)
            df['trade_time_ns'] = df['trade_time_ns'] + EDT_OFFSET_NS
            
            # Add contract column if not present
            if 'contract' not in df.columns and 'security_id' in df.columns:
                contract_map = {5002: 'ESH25', 5003: 'ESM25'}  # March and June
                df['contract'] = df['security_id'].map(contract_map).fillna('UNKNOWN')
            
            # Filter to specific contracts if requested
            if contracts:
                df = df[df['contract'].isin(contracts)]
            
            # Add date column
            df['date'] = trade_date
            
            return df.sort_values('trade_time_ns').reset_index(drop=True)
    
    raise FileNotFoundError(f"No ES trades file found for {trade_date} in {es_dir}")


def load_nasdaq_events_for_date(nasdaq_dir: Path, trade_date: date,
                                symbols: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Load NASDAQ MPID events for a specific date
    """
    # Try different patterns
    patterns = [
        f"nasdaq_events_{trade_date:%Y%m%d}.parquet",
        f"nasdaq_{trade_date:%Y-%m-%d}.parquet",
        f"extracted_{trade_date:%Y%m%d}.parquet"
    ]
    
    for pattern in patterns:
        filepath = nasdaq_dir / pattern
        if filepath.exists():
            logger.info(f"  Loading NASDAQ events: {filepath.name}")
            
            df = pd.read_parquet(filepath)
            
            # Standardize columns
            if 'timestamp_ns' in df.columns:
                df = df.rename(columns={'timestamp_ns': 'nasdaq_time_ns'})
            elif 'time_ns' in df.columns:
                df = df.rename(columns={'time_ns': 'nasdaq_time_ns'})
            
            # Filter to symbols if specified
            if symbols and 'symbol' in df.columns:
                df = df[df['symbol'].isin(symbols)]
            
            # Filter to MPID events only
            if 'event_type' in df.columns:
                df = df[df['event_type'].isin(['AddOrderMPID', 'Replace', 'Delete'])]
            
            return df.sort_values('nasdaq_time_ns').reset_index(drop=True)
    
    raise FileNotFoundError(f"No NASDAQ events file found for {trade_date} in {nasdaq_dir}")


def match_single_day(es_trades: pd.DataFrame, nasdaq_events: pd.DataFrame,
                     trade_date: date) -> pd.DataFrame:
    """
    Match ES trades to NASDAQ events for a single day
    Uses binary search with numba optimization
    """
    logger.info(f"  Matching {len(es_trades):,} ES trades to {len(nasdaq_events):,} NASDAQ events...")
    
    matches = []
    
    # Group by symbol for faster matching
    for symbol in es_trades['symbol'].unique() if 'symbol' in es_trades.columns else nasdaq_events['symbol'].unique():
        
        # Get ES trades for this symbol (all trades can trigger reactions in any symbol)
        es_symbol = es_trades  # Don't filter ES by symbol - ES impacts all symbols
        
        # Get NASDAQ events for this symbol
        nasdaq_symbol = nasdaq_events[nasdaq_events['symbol'] == symbol].copy()
        
        if len(nasdaq_symbol) == 0:
            continue
        
        nasdaq_times = nasdaq_symbol['nasdaq_time_ns'].values
        nasdaq_mpids = nasdaq_symbol['mpid'].values if 'mpid' in nasdaq_symbol.columns else np.array(['UNKNOWN'] * len(nasdaq_symbol))
        nasdaq_event_types = nasdaq_symbol['event_type'].values if 'event_type' in nasdaq_symbol.columns else np.array(['UNKNOWN'] * len(nasdaq_symbol))
        
        # Track matched (es_trade_idx, mpid) pairs to avoid duplicates
        matched_pairs = set()
        
        # For each ES trade
        for es_idx, es_row in es_symbol.iterrows():
            es_time = es_row['trade_time_ns']
            contract = es_row.get('contract', 'UNKNOWN')
            
            # Find first NASDAQ event after ES trade
            nasdaq_idx = binary_search_first_after(nasdaq_times, es_time, MATCHING_WINDOW_NS)
            
            if nasdaq_idx == -1:
                continue
            
            # For each matching NASDAQ event within window
            for offset in range(nasdaq_idx, len(nasdaq_times)):
                nasdaq_time = nasdaq_times[offset]
                
                # Check if within window
                if nasdaq_time - es_time > MATCHING_WINDOW_NS:
                    break
                
                mpid = nasdaq_mpids[offset]
                event_type = nasdaq_event_types[offset]
                
                # Check if we've already matched this (ES trade, MPID) pair
                pair_key = (es_idx, mpid)
                if pair_key in matched_pairs:
                    continue
                
                matched_pairs.add(pair_key)
                
                # Calculate latency
                latency_ns = nasdaq_time - es_time
                
                matches.append({
                    'es_trade_time_ns': es_time,
                    'nasdaq_time_ns': nasdaq_time,
                    'mpid': mpid,
                    'symbol': symbol,
                    'contract': contract,
                    'event_type': event_type,
                    'latency_ns': latency_ns,
                    'latency_us': latency_ns / 1_000,
                    'latency_ms': latency_ns / 1_000_000,
                    'date': trade_date
                })
    
    if len(matches) == 0:
        logger.warning(f"  ⚠️  No matches found for {trade_date}")
        return pd.DataFrame()
    
    result_df = pd.DataFrame(matches)
    logger.info(f"  ✓ Matched {len(result_df):,} latency observations")
    
    return result_df


def process_multi_day(es_dir: Path, nasdaq_dir: Path, 
                     dates: List[date],
                     contracts: Optional[List[str]] = None,
                     symbols: Optional[List[str]] = None,
                     output_file: Optional[Path] = None,
                     save_incremental: bool = True) -> pd.DataFrame:
    """
    Process multiple days of data
    Saves incrementally to manage memory
    """
    logger.info(f"🚀 Starting multi-day processing: {len(dates)} dates")
    logger.info(f"  Date range: {min(dates)} to {max(dates)}")
    if contracts:
        logger.info(f"  Contracts: {', '.join(contracts)}")
    if symbols:
        logger.info(f"  Symbols: {', '.join(symbols)}")
    
    all_results = []
    
    for i, trade_date in enumerate(dates, 1):
        logger.info(f"\n[{i}/{len(dates)}] Processing {trade_date}...")
        
        try:
            # Load data for this date
            es_trades = load_es_trades_for_date(es_dir, trade_date, contracts=contracts)
            nasdaq_events = load_nasdaq_events_for_date(nasdaq_dir, trade_date, symbols=symbols)
            
            # Match
            day_results = match_single_day(es_trades, nasdaq_events, trade_date)
            
            if len(day_results) == 0:
                logger.warning(f"  ⚠️  Skipping {trade_date} - no matches")
                continue
            
            # Validate
            n_obs = len(day_results)
            if n_obs < MIN_OBSERVATIONS_PER_DAY:
                logger.warning(f"  ⚠️  Only {n_obs:,} observations - expected >{MIN_OBSERVATIONS_PER_DAY:,}")
            elif n_obs > MAX_OBSERVATIONS_PER_DAY:
                logger.warning(f"  ⚠️  {n_obs:,} observations - expected <{MAX_OBSERVATIONS_PER_DAY:,} (possible duplication)")
            
            all_results.append(day_results)
            
            # Save incremental
            if save_incremental and output_file:
                day_file = output_file.parent / f"latencies_{trade_date:%Y%m%d}.parquet"
                day_results.to_parquet(day_file, engine=PARQUET_ENGINE, compression=PARQUET_COMPRESSION)
                logger.info(f"  💾 Saved daily results: {day_file.name}")
        
        except FileNotFoundError as e:
            logger.error(f"  ❌ Missing data for {trade_date}: {e}")
            continue
        except Exception as e:
            logger.error(f"  ❌ Error processing {trade_date}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Combine all results
    if len(all_results) == 0:
        logger.error("❌ No data processed successfully")
        return pd.DataFrame()
    
    logger.info(f"\n📊 Combining {len(all_results)} days of results...")
    combined_df = pd.concat(all_results, ignore_index=True)
    
    # Add enrichments
    combined_df['hour'] = pd.to_datetime(combined_df['nasdaq_time_ns'], unit='ns').dt.hour
    combined_df['day_of_week'] = pd.to_datetime(combined_df['nasdaq_time_ns'], unit='ns').dt.day_name()
    
    logger.info(f"✅ Total: {len(combined_df):,} latency observations across {len(dates)} days")
    
    # Save final combined file
    if output_file:
        logger.info(f"💾 Saving combined results to {output_file}...")
        combined_df.to_parquet(output_file, engine=PARQUET_ENGINE, compression=PARQUET_COMPRESSION)
        logger.info(f"✓ Saved: {output_file}")
    
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
