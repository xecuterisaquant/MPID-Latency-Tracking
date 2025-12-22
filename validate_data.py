"""
Data Integrity Verification Script
Validates ES and preprocessed NASDAQ data for all 10 days
"""
import pandas as pd
from pathlib import Path
from datetime import date
import sys

sys.path.append(str(Path(__file__).parent))
from config import ALL_DATES, ES_SECURITY_IDS

print("="*70)
print("DATA INTEGRITY VERIFICATION")
print("="*70)

# Paths
es_dir = Path("data/es")
nasdaq_temp_dir = Path("data/nasdaq/temp")

# Check 1: ES Data Integrity
print("\n1. ES DATA VERIFICATION")
print("-"*70)

es_summary = []
for trade_date in ALL_DATES:
    filepath = es_dir / f"trade_events_{trade_date:%Y%m%d}.parquet"
    
    if not filepath.exists():
        print(f"❌ MISSING: {filepath.name}")
        continue
    
    df = pd.read_parquet(filepath)
    
    # Get contract breakdown
    df['contract'] = df['security_id'].map(ES_SECURITY_IDS)
    contract_counts = df['contract'].value_counts().to_dict()
    
    esh25_count = contract_counts.get('ESH25', 0)
    esm25_count = contract_counts.get('ESM25', 0)
    unknown = contract_counts.get('UNKNOWN', 0) + len(df[df['contract'].isna()])
    
    es_summary.append({
        'date': trade_date,
        'total_trades': len(df),
        'ESH25': esh25_count,
        'ESM25': esm25_count,
        'unknown': unknown,
        'file_mb': filepath.stat().st_size / (1024**2)
    })
    
    status = "✓" if unknown == 0 else "⚠"
    print(f"{status} {trade_date}: {len(df):,} trades (ESH25: {esh25_count:,}, ESM25: {esm25_count:,}, Unknown: {unknown})")

es_df = pd.DataFrame(es_summary)
print(f"\nES Summary:")
print(f"  Total trades: {es_df['total_trades'].sum():,}")
print(f"  ESH25 total: {es_df['ESH25'].sum():,}")
print(f"  ESM25 total: {es_df['ESM25'].sum():,}")
print(f"  Rollover ratio: ESH25 starts at {es_df.iloc[0]['ESH25']/(es_df.iloc[0]['ESH25']+es_df.iloc[0]['ESM25'])*100:.1f}%, ends at {es_df.iloc[-1]['ESH25']/(es_df.iloc[-1]['ESH25']+es_df.iloc[-1]['ESM25'])*100:.1f}%")

# Check 2: NASDAQ Preprocessed Data
print("\n2. NASDAQ PREPROCESSED DATA VERIFICATION")
print("-"*70)

nasdaq_summary = []
for trade_date in ALL_DATES:
    temp_files = sorted(nasdaq_temp_dir.glob(f"{trade_date:%Y%m%d}_temp_*.parquet"))
    
    if len(temp_files) == 0:
        print(f"❌ MISSING: No temp files for {trade_date}")
        continue
    
    # Count total rows
    total_rows = 0
    for f in temp_files:
        df = pd.read_parquet(f)
        total_rows += len(df)
    
    total_size_mb = sum(f.stat().st_size for f in temp_files) / (1024**2)
    
    nasdaq_summary.append({
        'date': trade_date,
        'num_files': len(temp_files),
        'total_rows': total_rows,
        'size_mb': total_size_mb
    })
    
    print(f"✓ {trade_date}: {len(temp_files)} files, {total_rows:,} events, {total_size_mb:.1f} MB")

nasdaq_df = pd.DataFrame(nasdaq_summary)
print(f"\nNASDAQ Summary:")
print(f"  Total temp files: {nasdaq_df['num_files'].sum()}")
print(f"  Total MPID events: {nasdaq_df['total_rows'].sum():,}")
print(f"  Total size: {nasdaq_df['size_mb'].sum():.1f} MB")

# Check 3: Data Completeness
print("\n3. COMPLETENESS CHECK")
print("-"*70)

expected_days = len(ALL_DATES)
es_days = len(es_summary)
nasdaq_days = len(nasdaq_summary)

print(f"Expected days: {expected_days}")
print(f"ES days found: {es_days}")
print(f"NASDAQ days preprocessed: {nasdaq_days}")

if es_days == expected_days and nasdaq_days == expected_days:
    print("\n✅ ALL DATA VERIFIED - READY FOR PIPELINE")
    
    # Save summary
    summary_df = pd.merge(es_df[['date', 'total_trades', 'ESH25', 'ESM25']], 
                          nasdaq_df[['date', 'total_rows']], 
                          on='date')
    summary_df.to_csv('data/output/data_integrity_summary.csv', index=False)
    print(f"   Summary saved: data/output/data_integrity_summary.csv")
    
    sys.exit(0)
else:
    print("\n❌ DATA INCOMPLETE")
    if es_days < expected_days:
        print(f"   Missing {expected_days - es_days} ES files")
    if nasdaq_days < expected_days:
        print(f"   Missing {expected_days - nasdaq_days} NASDAQ preprocessed days")
    sys.exit(1)
