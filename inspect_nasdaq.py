"""Quick inspection of NASDAQ file structure"""
import pandas as pd
from pathlib import Path

# Get first file from 3/10
nasdaq_dir = Path("data/nasdaq/20250310")
files = list(nasdaq_dir.rglob("*.parquet"))

if files:
    print(f"Found {len(files)} files")
    print(f"\nInspecting first file: {files[0].name}")
    
    df = pd.read_parquet(files[0])
    
    print(f"\nColumns: {list(df.columns)}")
    print(f"Shape: {df.shape}")
    print(f"Memory: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    print(f"\nFirst 3 rows:")
    print(df.head(3))
    print(f"\nData types:")
    print(df.dtypes)
    
    # Check for event types
    if 'event_type' in df.columns:
        print(f"\nEvent types:")
        print(df['event_type'].value_counts())
    
    # Check for MPID
    if 'mpid' in df.columns:
        print(f"\nMPID count: {df['mpid'].nunique()}")
