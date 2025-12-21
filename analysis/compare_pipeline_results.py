"""
Compare results from different pipeline runs to identify inconsistencies.
"""

import pandas as pd
import numpy as np
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def compare_results(file1: str, file2: str, label1: str = "Version 1", label2: str = "Version 2"):
    """Compare two pipeline output files and report differences."""
    
    logger.info("=" * 80)
    logger.info("PIPELINE RESULTS COMPARISON")
    logger.info("=" * 80)
    
    logger.info(f"\n{label1}: {file1}")
    logger.info(f"{label2}: {file2}")
    
    # Load data
    df1 = pd.read_parquet(file1)
    df2 = pd.read_parquet(file2)
    
    logger.info("\n" + "=" * 80)
    logger.info("BASIC STATISTICS")
    logger.info("=" * 80)
    
    logger.info(f"\n{'Metric':<30} {label1:>20} {label2:>20} {'Difference':>20}")
    logger.info("-" * 95)
    
    # Row counts
    logger.info(f"{'Total measurements':<30} {len(df1):>20,} {len(df2):>20,} {len(df2) - len(df1):>20,}")
    
    # Unique counts
    mpids1, mpids2 = df1['mpid'].nunique(), df2['mpid'].nunique()
    symbols1, symbols2 = df1['symbol'].nunique(), df2['symbol'].nunique()
    
    logger.info(f"{'Unique MPIDs':<30} {mpids1:>20,} {mpids2:>20,} {mpids2 - mpids1:>20,}")
    logger.info(f"{'Unique symbols':<30} {symbols1:>20,} {symbols2:>20,} {symbols2 - symbols1:>20,}")
    
    # Latency statistics
    logger.info("\n" + "=" * 80)
    logger.info("LATENCY DISTRIBUTION (microseconds)")
    logger.info("=" * 80)
    
    stats1 = df1['latency_us'].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
    stats2 = df2['latency_us'].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
    
    logger.info(f"\n{'Statistic':<30} {label1:>20} {label2:>20} {'Diff %':>20}")
    logger.info("-" * 95)
    
    for stat in ['mean', '50%', '10%', '25%', '75%', '90%', '95%', '99%']:
        v1, v2 = stats1[stat], stats2[stat]
        diff_pct = ((v2 - v1) / v1 * 100) if v1 != 0 else (100 if v2 != 0 else 0)
        logger.info(f"{stat:<30} {v1:>20,.2f} {v2:>20,.2f} {diff_pct:>19.1f}%")
    
    # MPID distribution
    logger.info("\n" + "=" * 80)
    logger.info("TOP 10 MPID DISTRIBUTION")
    logger.info("=" * 80)
    
    mpid_counts1 = df1['mpid'].value_counts().head(10)
    mpid_counts2 = df2['mpid'].value_counts().head(10)
    
    all_mpids = sorted(set(mpid_counts1.index) | set(mpid_counts2.index))
    
    logger.info(f"\n{'MPID':<10} {label1 + ' Count':>20} {label1 + ' %':>10} {label2 + ' Count':>20} {label2 + ' %':>10}")
    logger.info("-" * 75)
    
    for mpid in all_mpids[:15]:
        c1 = mpid_counts1.get(mpid, 0)
        c2 = mpid_counts2.get(mpid, 0)
        p1 = c1 / len(df1) * 100 if len(df1) > 0 else 0
        p2 = c2 / len(df2) * 100 if len(df2) > 0 else 0
        
        logger.info(f"{mpid:<10} {c1:>20,} {p1:>9.2f}% {c2:>20,} {p2:>9.2f}%")
    
    # Event type distribution
    logger.info("\n" + "=" * 80)
    logger.info("EVENT TYPE DISTRIBUTION")
    logger.info("=" * 80)
    
    events1 = df1['event_type'].value_counts()
    events2 = df2['event_type'].value_counts()
    
    all_events = sorted(set(events1.index) | set(events2.index))
    
    logger.info(f"\n{'Event Type':<20} {label1 + ' Count':>20} {label1 + ' %':>10} {label2 + ' Count':>20} {label2 + ' %':>10}")
    logger.info("-" * 85)
    
    for event in all_events:
        c1 = events1.get(event, 0)
        c2 = events2.get(event, 0)
        p1 = c1 / len(df1) * 100 if len(df1) > 0 else 0
        p2 = c2 / len(df2) * 100 if len(df2) > 0 else 0
        
        logger.info(f"{event:<20} {c1:>20,} {p1:>9.2f}% {c2:>20,} {p2:>9.2f}%")
    
    # Check for MPIDs present in one but not the other
    logger.info("\n" + "=" * 80)
    logger.info("MPID PRESENCE COMPARISON")
    logger.info("=" * 80)
    
    mpids_set1 = set(df1['mpid'].unique())
    mpids_set2 = set(df2['mpid'].unique())
    
    only_in_1 = mpids_set1 - mpids_set2
    only_in_2 = mpids_set2 - mpids_set1
    
    logger.info(f"\nMPIDs only in {label1}: {len(only_in_1)}")
    if only_in_1:
        logger.info(f"  {', '.join(sorted(only_in_1)[:20])}")
        if len(only_in_1) > 20:
            logger.info(f"  ... and {len(only_in_1) - 20} more")
    
    logger.info(f"\nMPIDs only in {label2}: {len(only_in_2)}")
    if only_in_2:
        logger.info(f"  {', '.join(sorted(only_in_2)[:20])}")
        if len(only_in_2) > 20:
            logger.info(f"  ... and {len(only_in_2) - 20} more")
    
    # Zero latency check
    logger.info("\n" + "=" * 80)
    logger.info("DATA QUALITY CHECKS")
    logger.info("=" * 80)
    
    zero_lat1 = (df1['latency_ns'] == 0).sum()
    zero_lat2 = (df2['latency_ns'] == 0).sum()
    
    logger.info(f"\n{'Check':<40} {label1:>20} {label2:>20}")
    logger.info("-" * 85)
    logger.info(f"{'Zero latencies':<40} {zero_lat1:>20,} {zero_lat2:>20,}")
    logger.info(f"{'Negative latencies':<40} {(df1['latency_ns'] < 0).sum():>20,} {(df2['latency_ns'] < 0).sum():>20,}")
    logger.info(f"{'Latencies > 10s':<40} {(df1['latency_ns'] > 10e9).sum():>20,} {(df2['latency_ns'] > 10e9).sum():>20,}")
    
    # Diagnosis
    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSIS")
    logger.info("=" * 80)
    
    issues = []
    
    if abs(len(df1) - len(df2)) > 100:
        issues.append(f"⚠️  Row count differs by {abs(len(df1) - len(df2)):,}")
    
    if mpids1 != mpids2:
        issues.append(f"⚠️  MPID count differs: {mpids1} vs {mpids2}")
    
    if abs(stats1['50%'] - stats2['50%']) / stats1['50%'] > 0.1:  # >10% difference
        issues.append(f"⚠️  Median latency differs significantly: {stats1['50%']:.2f} vs {stats2['50%']:.2f} μs")
    
    if zero_lat2 > zero_lat1 + 100:
        issues.append(f"⚠️  {label2} has {zero_lat2 - zero_lat1:,} more zero latencies")
    
    if only_in_1:
        issues.append(f"⚠️  {len(only_in_1)} MPIDs missing in {label2}")
    
    if only_in_2:
        issues.append(f"⚠️  {len(only_in_2)} MPIDs appeared in {label2} that weren't in {label1}")
    
    if issues:
        logger.info("\n🚨 INCONSISTENCIES FOUND:")
        for issue in issues:
            logger.info(f"   {issue}")
    else:
        logger.info("\n✅ Results are consistent!")
    
    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare pipeline results")
    parser.add_argument("--file1", required=True, help="First results file")
    parser.add_argument("--file2", required=True, help="Second results file")
    parser.add_argument("--label1", default="Original", help="Label for first file")
    parser.add_argument("--label2", default="Optimized", help="Label for second file")
    
    args = parser.parse_args()
    
    compare_results(args.file1, args.file2, args.label1, args.label2)
