"""Inspect actual ES and NASDAQ data structures"""
import pandas as pd
from pathlib import Path

print("=" * 70)
print("ES DATA STRUCTURE")
print("=" * 70)

# Check ES file
es_file = Path("data/es/trade_events_20250310.parquet")
if es_file.exists():
    df_es = pd.read_parquet(es_file)
    print(f"\nFile: {es_file.name}")
    print(f"Columns: {list(df_es.columns)}")
    print(f"Shape: {df_es.shape}")
    print(f"\nFirst 3 rows:")
    print(df_es.head(3))
    print(f"\nData types:")
    print(df_es.dtypes)
    
    # Check for contract/security info
    if 'security_id' in df_es.columns:
        print(f"\nSecurity IDs:")
        print(df_es['security_id'].value_counts())
    if 'contract' in df_es.columns:
        print(f"\nContracts:")
        print(df_es['contract'].value_counts())
    if 'symbol' in df_es.columns:
        print(f"\nSymbols:")
        print(df_es['symbol'].value_counts())

print("\n" + "=" * 70)
print("NASDAQ DATA STRUCTURE")
print("=" * 70)

# Check NASDAQ file
nasdaq_dir = Path("data/nasdaq/20250310")
files = list(nasdaq_dir.rglob("*.parquet"))
if files:
    df_nasdaq = pd.read_parquet(files[0])
    print(f"\nFile: {files[0].name}")
    print(f"Columns: {list(df_nasdaq.columns)}")
    print(f"Shape: {df_nasdaq.shape}")
    print(f"\nFirst 3 rows:")
    print(df_nasdaq.head(3))
    print(f"\nData types:")
    print(df_nasdaq.dtypes)
