"""
Explore ES Trade Data Structure

Quick script to understand the schema and characteristics of ES trade data.
"""

import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

def explore_es_data():
    """Explore ES trade and book data files"""
    
    es_dir = Path("data/es")
    
    print("=" * 80)
    print("ES DATA EXPLORATION")
    print("=" * 80)
    
    # Find all parquet files
    parquet_files = list(es_dir.glob("*.parquet*"))
    
    for filepath in sorted(parquet_files):
        print(f"\n{'=' * 80}")
        print(f"FILE: {filepath.name}")
        print(f"{'=' * 80}")
        
        # Get file size
        size_mb = filepath.stat().st_size / 1024 / 1024
        print(f"\n💾 Size: {size_mb:.2f} MB")
        
        # Read schema without loading data
        parquet_file = pq.ParquetFile(filepath)
        print(f"\n📋 Schema:")
        print(parquet_file.schema)
        
        # Read first 10 rows to inspect data
        df_sample = pd.read_parquet(filepath, engine='pyarrow')
        
        print(f"\n📊 Shape: {df_sample.shape}")
        print(f"   Rows: {len(df_sample):,}")
        print(f"   Columns: {len(df_sample.columns)}")
        
        print(f"\n🔍 Column Info:")
        for col in df_sample.columns:
            dtype = df_sample[col].dtype
            null_count = df_sample[col].isnull().sum()
            unique_count = df_sample[col].nunique()
            print(f"   {col:25s} | {str(dtype):15s} | nulls: {null_count:>6,} | unique: {unique_count:>8,}")
        
        print(f"\n📈 First 5 rows:")
        print(df_sample.head())
        
        print(f"\n📉 Last 5 rows:")
        print(df_sample.tail())
        
        # Check for timestamp columns
        timestamp_cols = [col for col in df_sample.columns if 'time' in col.lower() or 'timestamp' in col.lower()]
        if timestamp_cols:
            print(f"\n⏰ Timestamp Analysis:")
            for col in timestamp_cols:
                print(f"\n   {col}:")
                print(f"      Min: {df_sample[col].min()}")
                print(f"      Max: {df_sample[col].max()}")
                print(f"      Range: {df_sample[col].max() - df_sample[col].min():,}")
                
                # Try to interpret as datetime
                try:
                    if df_sample[col].dtype in ['int64', 'int32']:
                        # Try as nanoseconds
                        dt = pd.to_datetime(df_sample[col], unit='ns', utc=True, errors='coerce')
                        if dt.notna().any():
                            print(f"      As datetime (ns): {dt.min()} to {dt.max()}")
                except:
                    pass
        
        # Check for symbol/instrument columns
        symbol_cols = [col for col in df_sample.columns if any(x in col.lower() for x in ['symbol', 'instrument', 'ticker'])]
        if symbol_cols:
            print(f"\n🏷️  Symbols/Instruments:")
            for col in symbol_cols:
                unique_vals = df_sample[col].unique()
                print(f"   {col}: {list(unique_vals[:10])}")
        
        # Summary statistics for numeric columns
        numeric_cols = df_sample.select_dtypes(include=['int64', 'float64']).columns
        if len(numeric_cols) > 0:
            print(f"\n📊 Numeric Column Stats:")
            print(df_sample[numeric_cols].describe())

if __name__ == "__main__":
    explore_es_data()
