#!/usr/bin/env python3
"""
Batch Latency Pipeline Runner for VM Deployment

Processes multiple days of ES and NASDAQ data in parallel.
Optimized for high-performance computing environments.

Usage:
    python run_batch_latency.py --start-date 20250201 --end-date 20250228 --workers 32

Features:
    - Parallel processing across multiple days
    - Automatic file discovery
    - Progress tracking
    - Error recovery
    - Memory-efficient streaming
"""

import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Tuple
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    ES_DATA_DIR, NASDAQ_DATA_DIR, RESULTS_DIR,
    TARGET_SYMBOLS, MAX_LATENCY_SECONDS, NUM_WORKERS,
    LOG_DIR, LOG_LEVEL
)
from analysis.latency_join_pipeline import LatencyJoinPipeline

# Configure logging
log_file = LOG_DIR / f"batch_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def find_data_files(date_str: str, es_dir: Path, nasdaq_dir: Path) -> Tuple[Path, Path]:
    """
    Find ES and NASDAQ data files for a given date.
    
    Args:
        date_str: Date in YYYYMMDD format
        es_dir: ES data directory
        nasdaq_dir: NASDAQ data directory
    
    Returns:
        Tuple of (es_file, nasdaq_file) paths
    
    Raises:
        FileNotFoundError if files don't exist
    """
    # ES files are named: trade_events_YYYYMMDD_es_mes.parquet2
    es_pattern = f"trade_events_{date_str}_es_mes.parquet*"
    es_files = list(es_dir.glob(es_pattern))
    
    if not es_files:
        raise FileNotFoundError(f"No ES trades found for {date_str} (pattern: {es_pattern})")
    
    es_file = es_files[0]
    
    # NASDAQ files: look for directory with date, then find targets parquet
    nasdaq_date_dir = nasdaq_dir / date_str
    
    if not nasdaq_date_dir.exists():
        raise FileNotFoundError(f"NASDAQ directory not found: {nasdaq_date_dir}")
    
    # Look for pre-filtered targets file
    nasdaq_target_file = nasdaq_date_dir / f"nasdaq_mpid_events_{date_str}_targets.parquet"
    
    if nasdaq_target_file.exists():
        nasdaq_file = nasdaq_target_file
    else:
        # Look for any parquet file in the directory
        nasdaq_files = list(nasdaq_date_dir.glob("*.parquet"))
        if not nasdaq_files:
            raise FileNotFoundError(f"No NASDAQ parquet files in {nasdaq_date_dir}")
        nasdaq_file = nasdaq_files[0]
        logger.warning(f"  Using {nasdaq_file.name} (targets file not found)")
    
    return es_file, nasdaq_file


def process_single_date(date_str: str) -> dict:
    """
    Process latency join for a single date.
    
    Args:
        date_str: Date in YYYYMMDD format
    
    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"{'='*80}")
        logger.info(f"Processing date: {date_str}")
        logger.info(f"{'='*80}")
        
        # Find data files
        es_file, nasdaq_file = find_data_files(date_str, ES_DATA_DIR, NASDAQ_DATA_DIR)
        
        logger.info(f"  ES trades: {es_file}")
        logger.info(f"  NASDAQ events: {nasdaq_file}")
        
        # Output file
        output_file = RESULTS_DIR / f"latency_results_{date_str}.parquet"
        logger.info(f"  Output: {output_file}")
        
        # Convert date string to YYYY-MM-DD format
        trade_date = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        
        # Run pipeline
        pipeline = LatencyJoinPipeline(trade_date=trade_date)
        
        results = pipeline.run(
            es_trades_path=es_file,
            nasdaq_events_path=nasdaq_file,
            output_path=output_file,
            target_symbols=TARGET_SYMBOLS,
            max_latency_seconds=MAX_LATENCY_SECONDS
        )
        
        return {
            'date': date_str,
            'status': 'SUCCESS',
            'rows': len(results),
            'output': str(output_file),
            'error': None
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to process {date_str}: {e}")
        return {
            'date': date_str,
            'status': 'FAILED',
            'rows': 0,
            'output': None,
            'error': str(e)
        }


def generate_date_range(start_date: str, end_date: str) -> List[str]:
    """
    Generate list of dates between start and end (inclusive).
    
    Args:
        start_date: Start date in YYYYMMDD format
        end_date: End date in YYYYMMDD format
    
    Returns:
        List of date strings in YYYYMMDD format
    """
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y%m%d'))
        current += timedelta(days=1)
    
    return dates


def main():
    parser = argparse.ArgumentParser(
        description='Batch process ES → NASDAQ latency joins',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single month with auto-detected worker count
  python run_batch_latency.py --start-date 20250201 --end-date 20250228
  
  # Process with explicit worker count for VM
  python run_batch_latency.py --start-date 20250201 --end-date 20250228 --workers 64
  
  # Process single day
  python run_batch_latency.py --start-date 20250310 --end-date 20250310
        """
    )
    
    parser.add_argument('--start-date', required=True, 
                       help='Start date (YYYYMMDD)')
    parser.add_argument('--end-date', required=True,
                       help='End date (YYYYMMDD)')
    parser.add_argument('--workers', type=int, default=NUM_WORKERS,
                       help=f'Number of parallel workers (default: {NUM_WORKERS})')
    parser.add_argument('--sequential', action='store_true',
                       help='Process dates sequentially instead of parallel')
    
    args = parser.parse_args()
    
    # Generate date list
    dates = generate_date_range(args.start_date, args.end_date)
    
    logger.info(f"{'='*80}")
    logger.info(f"BATCH LATENCY JOIN PIPELINE")
    logger.info(f"{'='*80}")
    logger.info(f"Date range: {args.start_date} to {args.end_date}")
    logger.info(f"Total dates: {len(dates)}")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"Mode: {'Sequential' if args.sequential else 'Parallel'}")
    logger.info(f"ES data dir: {ES_DATA_DIR}")
    logger.info(f"NASDAQ data dir: {NASDAQ_DATA_DIR}")
    logger.info(f"Output dir: {RESULTS_DIR}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"{'='*80}")
    
    # Process dates
    results = []
    
    if args.sequential:
        # Sequential processing
        for date in dates:
            result = process_single_date(date)
            results.append(result)
    else:
        # Parallel processing
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            # Submit all jobs
            future_to_date = {
                executor.submit(process_single_date, date): date 
                for date in dates
            }
            
            # Collect results as they complete
            for i, future in enumerate(as_completed(future_to_date), 1):
                date = future_to_date[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Progress: {i}/{len(dates)} dates completed")
                except Exception as e:
                    logger.error(f"Unexpected error processing {date}: {e}")
                    results.append({
                        'date': date,
                        'status': 'FAILED',
                        'rows': 0,
                        'output': None,
                        'error': str(e)
                    })
    
    # Summary
    logger.info(f"\n{'='*80}")
    logger.info(f"BATCH PROCESSING SUMMARY")
    logger.info(f"{'='*80}")
    
    successful = [r for r in results if r['status'] == 'SUCCESS']
    failed = [r for r in results if r['status'] == 'FAILED']
    
    logger.info(f"Total dates: {len(results)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")
    
    if successful:
        total_rows = sum(r['rows'] for r in successful)
        logger.info(f"Total latency measurements: {total_rows:,}")
    
    if failed:
        logger.warning(f"\n⚠️  Failed dates:")
        for r in failed:
            logger.warning(f"  {r['date']}: {r['error']}")
    
    logger.info(f"\n📝 Full log: {log_file}")
    logger.info(f"{'='*80}")
    
    # Exit with error code if any failures
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
