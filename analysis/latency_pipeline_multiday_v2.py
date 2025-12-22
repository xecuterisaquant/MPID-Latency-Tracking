"""
Multi-Day, Multi-Contract Latency Pipeline - MEMORY SAFE VERSION
Uses temp preprocessed files from preprocess_nasdaq.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Optional
import logging
from numba import njit
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import (
    ALL_DATES, EDT_OFFSET_NS, MATCHING_WINDOW_NS,
    OUTPUT_DIR, PARQUET_ENGINE, PARQUET_COMPRESSION,
    MIN_OBSERVATIONS_PER_DAY, MAX_OBSERVATIONS_PER_DAY
)

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
    """Numba-compiled matching (from original fast code)"""
    n_es = len(es_timestamps)
    max_results = n_es * 100
    
    es_times = np.empty(max_results, dtype=np.int64)
    mpid_ids = np.empty(max_results, dtype=np.int32)
    symbol_ids = np.empty(max_results, dtype=np.int32)
    event_type_ids = np.empty(max_results, dtype=np.int32)
    latencies = np.empty(max_results, dtype=np.int64)
    nasdaq_times = np.empty(max_results, dtype=np.int64)
    
    result_count = 0
    
    for i in range(n_es):
        es_time = es_timestamps[i]
        search_idx = np.searchsorted(nasdaq_timestamps, es_time)
        end_time = es_time + max_latency_ns
        end_idx = np.searchsorted(nasdaq_timestamps, end_time)
        
        if search_idx >= len(nasdaq_timestamps):
            continue
        
        seen_pairs = np.empty((1000, 2), dtype=np.int32)
        n_seen = 0
        
        for j in range(search_idx, end_idx):
            mpid_id = nasdaq_mpid_ids[j]
            symbol_id = nasdaq_symbol_ids[j]
            
            is_new = True
            for k in range(n_seen):
                if seen_pairs[k, 0] == mpid_id and seen_pairs[k, 1] == symbol_id:
                    is_new = False
                    break
            
            if is_new:
                if n_seen < 1000:
                    seen_pairs[n_seen, 0] = mpid_id
                    seen_pairs[n_seen, 1] = symbol_id
                    n_seen += 1
                
                if result_count < max_results:
                    es_times[result_count] = es_time
                    mpid_ids[result_count] = mpid_id
                    symbol_ids[result_count] = symbol_id
                    event_type_ids[result_count] = nasdaq_event_type_ids[j]
                    latencies[result_count] = nasdaq_timestamps[j] - es_time
                    nasdaq_times[result_count] = nasdaq_timestamps[j]
                    result_count += 1
    
    return (
        es_times[:result_count],
        mpid_ids[:result_count],
        symbol_ids[:result_count],
        event_type_ids[:result_count],
        latencies[:result_count],
        nasdaq_times[:result_count],
        result_count
    )


def load_es_trades_for_date(es_dir: Path, trade_date: date) -> pd.DataFrame:
    """Load ES trades for a date"""
    patterns = [f"trade_events_{trade_date:%Y%m%d}.parquet"]
    
    for pattern in patterns:
        filepath = es_dir / pattern
        if filepath.exists():
            logger.info(f"  Loading ES trades: {filepath.name}")
            df = pd.read_parquet(filepath)
            
            if 'transact_time_ns' in df.columns:
                df = df.rename(columns={'transact_time_ns': 'trade_time_ns'})
            
            df['trade_time_ns'] = df['trade_time_ns'] + EDT_OFFSET_NS
            
            if 'security_id' in df.columns:
                contract_map = {5002: 'ESH25', 5003: 'ESM25', 4916: 'ESH25'}
                df['contract'] = df['security_id'].map(contract_map).fillna('UNKNOWN')
            
            df['date'] = trade_date
            return df.sort_values('trade_time_ns').reset_index(drop=True)
    
    raise FileNotFoundError(f"No ES trades found for {trade_date}")


def load_nasdaq_events_for_date(nasdaq_dir: Path, trade_date: date) -> pd.DataFrame:
    """Load from temp preprocessed files - simple approach from aggregate_nasdaq_data.py"""
    temp_dir = nasdaq_dir / "temp"
    temp_pattern = f"{trade_date:%Y%m%d}_temp_*.parquet"
    temp_files = sorted(temp_dir.glob(temp_pattern))
    
    if not temp_files:
        raise FileNotFoundError(f"No temp files for {trade_date}. Run preprocess_nasdaq.py first!")
    
    logger.info(f"  Loading {len(temp_files)} preprocessed files...")
    
    # Simple approach: load one by one, append to list, concat once
    dfs = []
    for i, f in enumerate(temp_files, 1):
        df = pd.read_parquet(f)
        dfs.append(df)
        if i % 10 == 0:
            logger.info(f"    Loaded {i}/{len(temp_files)} files...")
    
    logger.info(f"  Concatenating...")
    full_df = pd.concat(dfs, ignore_index=True)
    
    logger.info(f"  Sorting...")
    full_df = full_df.sort_values('event_time_ns').reset_index(drop=True)
    full_df = full_df.rename(columns={'event_time_ns': 'nasdaq_time_ns', 'message_type': 'event_type'})
    
    logger.info(f"  Loaded {len(full_df):,} NASDAQ events")
    return full_df


def match_single_day(es_trades: pd.DataFrame, nasdaq_events: pd.DataFrame,
                     trade_date: date, contract: str) -> pd.DataFrame:
    """Match using Numba-compiled function"""
    logger.info(f"  Matching {len(es_trades):,} ES trades ({contract}) to {len(nasdaq_events):,} NASDAQ events...")
    
    es_timestamps = es_trades['trade_time_ns'].values.astype(np.int64)
    nasdaq_timestamps = nasdaq_events['nasdaq_time_ns'].values.astype(np.int64)
    
    symbol_categories = pd.Categorical(nasdaq_events['symbol'])
    mpid_categories = pd.Categorical(nasdaq_events['mpid'])
    event_type_categories = pd.Categorical(nasdaq_events['event_type'])
    
    nasdaq_symbol_ids = symbol_categories.codes.astype(np.int32)
    nasdaq_mpid_ids = mpid_categories.codes.astype(np.int32)
    nasdaq_event_type_ids = event_type_categories.codes.astype(np.int32)
    
    (es_times, mpid_ids, symbol_ids, event_type_ids,
     latencies, nasdaq_times, result_count) = _find_latencies_numba(
        es_timestamps, nasdaq_timestamps,
        nasdaq_symbol_ids, nasdaq_mpid_ids, nasdaq_event_type_ids,
        MATCHING_WINDOW_NS
    )
    
    if result_count == 0:
        logger.warning(f"  No matches found")
        return pd.DataFrame()
    
    logger.info(f"  Found {result_count:,} matches")
    
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


def process_multi_day(es_dir: Path, nasdaq_dir: Path, dates: List[date],
                     contracts: List[str], output_file: Path) -> pd.DataFrame:
    """Process multiple days with multiple contracts"""
    logger.info(f"Processing {len(dates)} days, {len(contracts)} contracts")
    
    all_results = []
    
    for i, trade_date in enumerate(dates, 1):
        logger.info(f"\n[{i}/{len(dates)}] Processing {trade_date}...")
        
        try:
            nasdaq_events = load_nasdaq_events_for_date(nasdaq_dir, trade_date)
            es_trades_all = load_es_trades_for_date(es_dir, trade_date)
            
            for contract in contracts:
                es_trades_contract = es_trades_all[es_trades_all['contract'] == contract]
                
                if len(es_trades_contract) == 0:
                    logger.info(f"  No {contract} trades")
                    continue
                
                logger.info(f"  Processing {contract}...")
                results = match_single_day(es_trades_contract, nasdaq_events, trade_date, contract)
                
                if len(results) > 0:
                    all_results.append(results)
                    
                    day_file = output_file.parent / f"latencies_{trade_date:%Y%m%d}_{contract}.parquet"
                    results.to_parquet(day_file, engine=PARQUET_ENGINE, compression=PARQUET_COMPRESSION)
                    logger.info(f"  Saved: {day_file.name}")
        
        except Exception as e:
            logger.error(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if not all_results:
        logger.error("No data processed!")
        return pd.DataFrame()
    
    logger.info(f"\nCombining {len(all_results)} results...")
    combined = pd.concat(all_results, ignore_index=True)
    
    combined['hour'] = pd.to_datetime(combined['nasdaq_time_ns'], unit='ns').dt.hour
    
    logger.info(f"Total: {len(combined):,} observations")
    
    combined.to_parquet(output_file, engine=PARQUET_ENGINE, compression=PARQUET_COMPRESSION)
    logger.info(f"Saved: {output_file}")
    
    return combined


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--es-dir', type=Path, required=True)
    parser.add_argument('--nasdaq-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    
    # Test with 2 days
    dates = [date(2025, 3, 10), date(2025, 3, 11)]
    contracts = ['ESH25', 'ESM25']
    
    logger.info(f"Processing {len(dates)} days (testing)")
    
    process_multi_day(
        es_dir=args.es_dir,
        nasdaq_dir=args.nasdaq_dir,
        dates=dates,
        contracts=contracts,
        output_file=args.output
    )
