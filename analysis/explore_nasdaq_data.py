"""
Explore NASDAQ MPID event data structure
"""
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

# Load one file to check schema
data_dir = Path("data/extracted/20250310")
sample_file = list(data_dir.glob("*.parquet"))[0]

print(f"Analyzing: {sample_file.name}")
print("=" * 80)

# Check schema
table = pq.read_table(sample_file)
print("\n📋 SCHEMA:")
print(table.schema)

# Load as DataFrame
df = table.to_pandas()
print(f"\n📊 SHAPE: {df.shape[0]:,} rows x {df.shape[1]} columns")

print("\n📌 COLUMNS:")
for col in df.columns:
    dtype = df[col].dtype
    non_null = df[col].notna().sum()
    print(f"  {col:20s} | {str(dtype):15s} | {non_null:,} non-null")

print("\n🔍 SAMPLE ROWS:")
print(df.head(10).to_string())

print("\n📈 BASIC STATS:")
print(f"  Unique MPIDs: {df['mpid'].nunique() if 'mpid' in df.columns else 'N/A'}")
print(f"  Unique Symbols: {df['symbol'].nunique() if 'symbol' in df.columns else 'N/A'}")
print(f"  Message Types: {df['message_type'].value_counts().to_dict() if 'message_type' in df.columns else 'N/A'}")

if 'timestamp_ns' in df.columns:
    print(f"\n⏰ TIME RANGE:")
    print(f"  Min: {pd.to_datetime(df['timestamp_ns'].min(), unit='ns')}")
    print(f"  Max: {pd.to_datetime(df['timestamp_ns'].max(), unit='ns')}")
    print(f"  Duration: {(df['timestamp_ns'].max() - df['timestamp_ns'].min()) / 1e9:.2f} seconds")

# Check for target symbols
if 'symbol' in df.columns:
    target_symbols = ['QQQ', 'IWM', 'TSLA', 'AAPL', 'SPY', 'NVDA']
    present = [s for s in target_symbols if s in df['symbol'].values]
    print(f"\n🎯 TARGET SYMBOLS FOUND: {present}")
    
    if present:
        print(f"\n📊 MESSAGE COUNTS FOR TARGET SYMBOLS:")
        for sym in present[:5]:
            count = (df['symbol'] == sym).sum()
            print(f"  {sym}: {count:,} messages")

# Load all files and get total stats
print("\n" + "=" * 80)
print("📦 LOADING ALL FILES...")
all_files = sorted(data_dir.glob("*.parquet"))
print(f"Total files: {len(all_files)}")

total_rows = 0
for f in all_files[:3]:  # Sample first 3
    t = pq.read_table(f)
    total_rows += len(t)
print(f"Estimated total rows (extrapolated): {total_rows * len(all_files) // 3:,}")
