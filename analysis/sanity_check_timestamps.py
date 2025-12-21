"""
Comprehensive timestamp alignment sanity check.

Investigates the discrepancy where first 100k ES trades had only 1,914 latencies
but subsequent batches had millions.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_timestamp_alignment(
    es_path: str,
    nasdaq_path: str,
    trade_date: str
):
    """Deep analysis of timestamp alignment between ES and NASDAQ data."""
    
    logger.info("=" * 80)
    logger.info("TIMESTAMP ALIGNMENT SANITY CHECK")
    logger.info("=" * 80)
    
    # Load data
    logger.info(f"\n📂 Loading ES trades from {es_path}")
    es_df = pd.read_parquet(es_path)
    logger.info(f"   Loaded {len(es_df):,} ES trades")
    
    logger.info(f"\n📂 Loading NASDAQ events from {nasdaq_path}")
    nasdaq_df = pd.read_parquet(nasdaq_path)
    logger.info(f"   Loaded {len(nasdaq_df):,} NASDAQ events")
    
    # Convert NASDAQ timestamps (apply the /1000 correction)
    trade_date_dt = pd.Timestamp(trade_date)
    eastern_midnight = pd.Timestamp(trade_date_dt.date(), tz='America/New_York')
    
    nasdaq_df['event_time_absolute_ns'] = (
        eastern_midnight.value + (nasdaq_df['event_time_ns'] / 1000)
    )
    nasdaq_df['timestamp'] = pd.to_datetime(nasdaq_df['event_time_absolute_ns'], utc=True)
    
    # ES timestamps are already absolute
    es_df['timestamp'] = pd.to_datetime(es_df['transact_time_ns'], utc=True)
    
    logger.info("\n" + "=" * 80)
    logger.info("1. OVERALL TIME RANGES")
    logger.info("=" * 80)
    
    es_min, es_max = es_df['timestamp'].min(), es_df['timestamp'].max()
    nasdaq_min, nasdaq_max = nasdaq_df['timestamp'].min(), nasdaq_df['timestamp'].max()
    
    logger.info(f"\n📊 ES Trades:")
    logger.info(f"   First trade:  {es_min} UTC")
    logger.info(f"   Last trade:   {es_max} UTC")
    logger.info(f"   Duration:     {(es_max - es_min).total_seconds() / 3600:.2f} hours")
    
    logger.info(f"\n📊 NASDAQ Events:")
    logger.info(f"   First event:  {nasdaq_min} UTC")
    logger.info(f"   Last event:   {nasdaq_max} UTC")
    logger.info(f"   Duration:     {(nasdaq_max - nasdaq_min).total_seconds() / 3600:.2f} hours")
    
    # Check overlap
    overlap_start = max(es_min, nasdaq_min)
    overlap_end = min(es_max, nasdaq_max)
    
    if overlap_start < overlap_end:
        logger.info(f"\n✅ OVERLAP EXISTS:")
        logger.info(f"   Start: {overlap_start} UTC")
        logger.info(f"   End:   {overlap_end} UTC")
        logger.info(f"   Duration: {(overlap_end - overlap_start).total_seconds() / 3600:.2f} hours")
    else:
        logger.info(f"\n❌ NO OVERLAP DETECTED!")
        logger.info(f"   Gap: {(overlap_start - overlap_end).total_seconds() / 3600:.2f} hours")
    
    # Hourly distribution
    logger.info("\n" + "=" * 80)
    logger.info("2. HOURLY DISTRIBUTION")
    logger.info("=" * 80)
    
    es_df['hour'] = es_df['timestamp'].dt.floor('h')
    nasdaq_df['hour'] = nasdaq_df['timestamp'].dt.floor('h')
    
    es_hourly = es_df.groupby('hour').size()
    nasdaq_hourly = nasdaq_df.groupby('hour').size()
    
    # Create combined hourly view
    all_hours = sorted(set(es_hourly.index) | set(nasdaq_hourly.index))
    
    logger.info("\nHour (UTC)              ES Trades    NASDAQ Events    Overlap?")
    logger.info("-" * 70)
    
    for hour in all_hours:
        es_count = es_hourly.get(hour, 0)
        nasdaq_count = nasdaq_hourly.get(hour, 0)
        has_both = "✓" if (es_count > 0 and nasdaq_count > 0) else "✗"
        
        logger.info(
            f"{hour.strftime('%Y-%m-%d %H:00')}    "
            f"{es_count:>10,}    {nasdaq_count:>13,}    {has_both}"
        )
    
    # First 100k analysis
    logger.info("\n" + "=" * 80)
    logger.info("3. FIRST 100K ES TRADES ANALYSIS")
    logger.info("=" * 80)
    
    first_100k = es_df.iloc[:100000].copy()
    
    logger.info(f"\n📊 First 100,000 ES trades:")
    logger.info(f"   Time range: {first_100k['timestamp'].min()} to {first_100k['timestamp'].max()}")
    logger.info(f"   Duration: {(first_100k['timestamp'].max() - first_100k['timestamp'].min()).total_seconds() / 3600:.2f} hours")
    
    # Check if these trades fall within NASDAQ time range
    in_nasdaq_range = (
        (first_100k['timestamp'] >= nasdaq_min) & 
        (first_100k['timestamp'] <= nasdaq_max)
    )
    
    logger.info(f"\n   Trades within NASDAQ time range: {in_nasdaq_range.sum():,} / {len(first_100k):,} ({in_nasdaq_range.sum()/len(first_100k)*100:.2f}%)")
    logger.info(f"   Trades BEFORE NASDAQ starts: {(first_100k['timestamp'] < nasdaq_min).sum():,}")
    logger.info(f"   Trades AFTER NASDAQ ends: {(first_100k['timestamp'] > nasdaq_max).sum():,}")
    
    # Market hours check (9:30 AM - 4:00 PM Eastern)
    logger.info("\n" + "=" * 80)
    logger.info("4. MARKET HOURS ANALYSIS")
    logger.info("=" * 80)
    
    # Convert to Eastern Time
    es_df_et = es_df.copy()
    es_df_et['timestamp_et'] = es_df_et['timestamp'].dt.tz_convert('America/New_York')
    es_df_et['hour_et'] = es_df_et['timestamp_et'].dt.hour
    es_df_et['minute_et'] = es_df_et['timestamp_et'].dt.minute
    
    # Regular market hours: 9:30 AM - 4:00 PM
    es_df_et['market_hours'] = (
        ((es_df_et['hour_et'] == 9) & (es_df_et['minute_et'] >= 30)) |
        ((es_df_et['hour_et'] > 9) & (es_df_et['hour_et'] < 16))
    )
    
    pre_market = es_df_et['hour_et'] < 9
    post_16 = es_df_et['hour_et'] >= 16
    
    logger.info(f"\n📊 ES Trades by market period:")
    logger.info(f"   Pre-market (before 9:00 AM ET): {pre_market.sum():,} ({pre_market.sum()/len(es_df_et)*100:.2f}%)")
    logger.info(f"   9:00-9:30 AM ET: {((es_df_et['hour_et'] == 9) & (es_df_et['minute_et'] < 30)).sum():,}")
    logger.info(f"   Regular hours (9:30 AM - 4:00 PM ET): {es_df_et['market_hours'].sum():,} ({es_df_et['market_hours'].sum()/len(es_df_et)*100:.2f}%)")
    logger.info(f"   After hours (4:00 PM+ ET): {post_16.sum():,} ({post_16.sum()/len(es_df_et)*100:.2f}%)")
    
    # Check first 100k specifically
    first_100k_et = es_df_et.iloc[:100000]
    logger.info(f"\n📊 First 100,000 ES trades:")
    logger.info(f"   In regular market hours: {first_100k_et['market_hours'].sum():,} / 100,000 ({first_100k_et['market_hours'].sum()/1000:.2f}%)")
    logger.info(f"   Pre-market: {(first_100k_et['hour_et'] < 9).sum():,}")
    logger.info(f"   9:00-9:30: {((first_100k_et['hour_et'] == 9) & (first_100k_et['minute_et'] < 30)).sum():,}")
    
    # Sample matching demonstration
    logger.info("\n" + "=" * 80)
    logger.info("5. SAMPLE MATCHING EXAMPLES")
    logger.info("=" * 80)
    
    # Take 5 sample trades from different time periods
    samples = [
        (10000, "Early trades (around #10,000)"),
        (50000, "Mid first-100k (#50,000)"),
        (150000, "Second 100k batch (#150,000)"),
        (300000, "Third 100k batch (#300,000)"),
        (500000, "Fifth 100k batch (#500,000)")
    ]
    
    for idx, desc in samples:
        if idx >= len(es_df):
            continue
            
        trade = es_df.iloc[idx]
        trade_time = trade['timestamp']
        
        # Find NASDAQ events within 10 seconds
        time_window_start = trade_time
        time_window_end = trade_time + pd.Timedelta(seconds=10)
        
        matching_events = nasdaq_df[
            (nasdaq_df['timestamp'] >= time_window_start) &
            (nasdaq_df['timestamp'] <= time_window_end)
        ]
        
        logger.info(f"\n{desc}:")
        logger.info(f"   ES trade time: {trade_time}")
        logger.info(f"   Search window: {time_window_start} to {time_window_end}")
        logger.info(f"   Matching NASDAQ events in 10s window: {len(matching_events):,}")
        
        if len(matching_events) > 0:
            first_match = matching_events.iloc[0]
            latency_ns = first_match['event_time_absolute_ns'] - trade['transact_time_ns']
            latency_us = latency_ns / 1000
            logger.info(f"   First match latency: {latency_us:.2f} μs")
    
    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSIS")
    logger.info("=" * 80)
    
    # Calculate percentage in first 100k vs rest
    first_100k_in_range = in_nasdaq_range.sum()
    rest_df = es_df.iloc[100000:200000]
    rest_in_range = (
        (rest_df['timestamp'] >= nasdaq_min) & 
        (rest_df['timestamp'] <= nasdaq_max)
    ).sum()
    
    logger.info(f"\n📊 Coverage comparison:")
    logger.info(f"   First 100k trades in NASDAQ range: {first_100k_in_range:,} ({first_100k_in_range/1000:.1f}%)")
    logger.info(f"   Next 100k trades in NASDAQ range: {rest_in_range:,} ({rest_in_range/1000:.1f}%)")
    
    if first_100k_in_range < rest_in_range * 0.5:
        logger.info(f"\n⚠️  FINDING: First 100k trades have significantly fewer matches!")
        logger.info(f"   Most likely cause: ES futures trade during pre-market hours")
        logger.info(f"   NASDAQ MPID data only covers regular market hours (9:30-16:00 ET)")
        logger.info(f"   Early ES trades have no NASDAQ counterparts to match against")
    else:
        logger.info(f"\n✓ Coverage appears consistent across batches")
    
    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Timestamp alignment sanity check")
    parser.add_argument("--es-trades", required=True, help="Path to ES trades parquet")
    parser.add_argument("--nasdaq-events", required=True, help="Path to NASDAQ events parquet")
    parser.add_argument("--trade-date", required=True, help="Trade date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    analyze_timestamp_alignment(
        es_path=args.es_trades,
        nasdaq_path=args.nasdaq_events,
        trade_date=args.trade_date
    )
