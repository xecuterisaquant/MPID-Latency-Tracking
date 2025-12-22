"""
Combine Multi-Day, Multi-Contract Outputs
Merges all latencies_YYYYMMDD_CONTRACT.parquet files into single dataset
"""
import pandas as pd
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))
from config import OUTPUT_DIR, ALL_DATES

print("="*70)
print("COMBINING MULTI-DAY OUTPUTS")
print("="*70)

output_dir = Path(OUTPUT_DIR)
contracts = ['ESH25', 'ESM25']

# Find all output files
all_files = []
for trade_date in ALL_DATES:
    for contract in contracts:
        filename = f"latencies_{trade_date:%Y%m%d}_{contract}.parquet"
        filepath = output_dir / filename
        if filepath.exists():
            all_files.append(filepath)
            print(f"✓ Found: {filename}")
        else:
            print(f"⚠ Missing: {filename}")

print(f"\nTotal files to combine: {len(all_files)}")

if len(all_files) == 0:
    print("❌ No files found!")
    sys.exit(1)

# Load and combine
print("\nLoading files...")
dfs = []
for filepath in all_files:
    df = pd.read_parquet(filepath)
    print(f"  {filepath.name}: {len(df):,} rows")
    dfs.append(df)

print("\nCombining...")
combined = pd.concat(dfs, ignore_index=True)

print(f"\n✓ Combined shape: {len(combined):,} rows × {len(combined.columns)} columns")
print(f"  Date range: {combined['date'].min()} to {combined['date'].max()}")
print(f"  Contracts: {combined['contract'].unique()}")
print(f"  Symbols: {combined['symbol'].nunique()}")
print(f"  MPIDs: {combined['mpid'].nunique()}")

# Save
output_file = output_dir / "latencies_multiday_combined.parquet"
print(f"\nSaving to: {output_file.name}...")
combined.to_parquet(output_file, engine='pyarrow', compression='snappy')

file_size_mb = output_file.stat().st_size / (1024 * 1024)
print(f"✓ Saved: {file_size_mb:.2f} MB")

print("\n" + "="*70)
print("COMBINATION COMPLETE")
print("="*70)
print(f"\nReady for analytics: {output_file}")
