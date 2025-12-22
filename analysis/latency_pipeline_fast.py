"""
Fast Multi-Day Pipeline - Based on Original 48-Second Code
Loads NASDAQ temp files, processes each contract separately
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import date
from typing import List
import logging
from numba import njit
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import EDT_OFFSET_NS, MATCHING_WINDOW_NS, PARQUET_ENGINE, PARQUET_COMPRESSION

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
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
    """Numba-compiled matching from original code"""
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


def load_nasdaq_from_temp(nasdaq_dir: Path, trade_date: date) -> pd.DataFrame:
    """Load NASDAQ from preprocessed combined file"""
    # Try combined file first (from preprocessing)
    combined_file = nasdaq_dir / f"nasdaq_filtered_{trade_date:%Y%m%d}.parquet"
    
    if combined_file.exists():
        logger.info(f"  Loading preprocessed file: {combined_file.name}")
        df = pd.read_parquet(combined_file)
        logger.info(f"  Loaded {len(df):,} events (already sorted and filtered)")
    else:
        # Fallback: try temp files
        temp_dir = nasdaq_dir / "temp"
        temp_files = sorted(temp_dir.glob(f"{trade_date:%Y%m%d}_temp_*.parquet"))
        
        if not temp_files:
            raise FileNotFoundError(f"No preprocessed file or temp files for {trade_date}")
        
        logger.info(f"  Loading {len(temp_files)} temp files in batches...")
        
        # Load in batches of 5, concat incrementally
        all_chunks = []
        for i in range(0, len(temp_files), 5):
            batch = temp_files[i:i+5]
            batch_dfs = [pd.read_parquet(f) for f in batch]
            chunk = pd.concat(batch_dfs, ignore_index=True)
            all_chunks.append(chunk)
            del batch_dfs
            logger.info(f"    Batch {i//5 + 1}: {len(chunk):,} rows")
        
        logger.info(f"  Final concatenation...")
        df = pd.concat(all_chunks, ignore_index=True)
        del all_chunks
        
        logger.info(f"  Sorting {len(df):,} events...")
        df = df.sort_values('event_time_ns').reset_index(drop=True)
    
    # FIX: Divide timestamps by 1000 (extraction bug multiplier)
    logger.info(f"  Fixing timestamp multiplier...")
    df['event_time_ns'] = df['event_time_ns'] // 1000
    
    # Convert from nanoseconds-since-midnight to absolute Unix epoch
    logger.info(f"  Converting to absolute timestamps...")
    trade_datetime = pd.Timestamp(trade_date, tz='America/New_York')
    midnight_ns = trade_datetime.value  # Unix epoch nanoseconds for midnight ET
    df['nasdaq_time_ns'] = midnight_ns + df['event_time_ns']
    
    df = df.rename(columns={'message_type': 'event_type'})
    df = df.drop(columns=['event_time_ns'])
    
    # CRITICAL: Filter to target symbols (major stocks/ETFs)
    logger.info(f"  Filtering to target symbols...")
    from config import TARGET_SYMBOLS
    df = df[df['symbol'].isin(TARGET_SYMBOLS)].reset_index(drop=True)
    
    logger.info(f"  Loaded {len(df):,} NASDAQ events for {len(TARGET_SYMBOLS)} symbols")
    return df


def load_es_trades(es_dir: Path, trade_date: date) -> pd.DataFrame:
    """Load ES trades"""
    filepath = es_dir / f"trade_events_{trade_date:%Y%m%d}.parquet"
    
    if not filepath.exists():
        raise FileNotFoundError(f"No ES file for {trade_date}")
    
    logger.info(f"  Loading ES: {filepath.name}")
    df = pd.read_parquet(filepath)
    
    if 'transact_time_ns' in df.columns:
        df = df.rename(columns={'transact_time_ns': 'trade_time_ns'})
    
    df['trade_time_ns'] = df['trade_time_ns'] + EDT_OFFSET_NS
    
    # Map contracts - use config mapping
    from config import ES_SECURITY_IDS
    df['contract'] = df['security_id'].map(ES_SECURITY_IDS).fillna('UNKNOWN')
    
    return df.sort_values('trade_time_ns').reset_index(drop=True)


def match_contract(es_trades: pd.DataFrame, nasdaq_events: pd.DataFrame,
                   trade_date: date, contract: str) -> pd.DataFrame:
    """Match one contract using Numba"""
    logger.info(f"  Matching {len(es_trades):,} {contract} trades to {len(nasdaq_events):,} NASDAQ events...")
    
    es_timestamps = es_trades['trade_time_ns'].values.astype(np.int64)
    nasdaq_timestamps = nasdaq_events['nasdaq_time_ns'].values.astype(np.int64)
    
    symbol_cats = pd.Categorical(nasdaq_events['symbol'])
    mpid_cats = pd.Categorical(nasdaq_events['mpid'])
    event_cats = pd.Categorical(nasdaq_events['event_type'])
    
    (es_times, mpid_ids, symbol_ids, event_type_ids,
     latencies, nasdaq_times, result_count) = _find_latencies_numba(
        es_timestamps, nasdaq_timestamps,
        symbol_cats.codes.astype(np.int32),
        mpid_cats.codes.astype(np.int32),
        event_cats.codes.astype(np.int32),
        MATCHING_WINDOW_NS
    )
    
    if result_count == 0:
        return pd.DataFrame()
    
    logger.info(f"  Found {result_count:,} matches")
    
    return pd.DataFrame({
        'es_trade_time_ns': es_times,
        'mpid': pd.Categorical.from_codes(mpid_ids, mpid_cats.categories),
        'symbol': pd.Categorical.from_codes(symbol_ids, symbol_cats.categories),
        'event_type': pd.Categorical.from_codes(event_type_ids, event_cats.categories),
        'latency_ns': latencies,
        'nasdaq_time_ns': nasdaq_times,
        'contract': contract,
        'date': trade_date,
        'latency_ms': latencies / 1_000_000
    })


def process_day(es_dir: Path, nasdaq_dir: Path, trade_date: date,
                contracts: List[str], output_dir: Path):
    """Process one day - all contracts"""
    logger.info(f"\nProcessing {trade_date}...")
    
    # Load NASDAQ once for this day
    nasdaq_events = load_nasdaq_from_temp(nasdaq_dir, trade_date)
    
    # Load all ES trades
    es_trades_all = load_es_trades(es_dir, trade_date)
    
    # Process each contract
    for contract in contracts:
        es_contract = es_trades_all[es_trades_all['contract'] == contract]
        
        if len(es_contract) == 0:
            logger.info(f"  No {contract} trades")
            continue
        
        logger.info(f"  Processing {contract}...")
        results = match_contract(es_contract, nasdaq_events, trade_date, contract)
        
        if len(results) > 0:
            output_file = output_dir / f"latencies_{trade_date:%Y%m%d}_{contract}.parquet"
            results.to_parquet(output_file, engine=PARQUET_ENGINE, compression=PARQUET_COMPRESSION)
            logger.info(f"  Saved: {output_file.name} ({len(results):,} rows)")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--es-dir', type=Path, required=True)
    parser.add_argument('--nasdaq-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process all 10 trading days (full dataset)
    from config import ALL_DATES
    dates = ALL_DATES
    contracts = ['ESH25', 'ESM25']
    
    logger.info(f"Processing {len(dates)} days, {len(contracts)} contracts per day")
    
    for trade_date in dates:
        try:
            process_day(args.es_dir, args.nasdaq_dir, trade_date, contracts, args.output_dir)
        except Exception as e:
            logger.error(f"Failed {trade_date}: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info("\nDone!")
