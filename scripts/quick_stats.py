"""Quick statistical summary for 93M observations"""
import pandas as pd
import numpy as np
from pathlib import Path

print("Loading data...")
df = pd.read_parquet('data/output/latencies_multiday_combined.parquet')
print(f"✓ Loaded {len(df):,} rows\n")

print("="*80)
print("OVERALL STATISTICS")
print("="*80)
print(f"Total observations: {len(df):,}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print(f"Contracts: {sorted(df['contract'].unique())}")
print(f"Symbols: {sorted(df['symbol'].unique())}")
print(f"MPIDs: {df['mpid'].nunique()}")
print()

print("Latency (milliseconds):")
print(f"  Mean:   {df['latency_ms'].mean():.3f} ms")
print(f"  Median: {df['latency_ms'].median():.3f} ms")
print(f"  Std:    {df['latency_ms'].std():.3f} ms")
print(f"  Min:    {df['latency_ms'].min():.3f} ms")
print(f"  Max:    {df['latency_ms'].max():.3f} ms")
print()

print("Percentiles:")
for p in [25, 50, 75, 90, 95, 99]:
    val = df['latency_ms'].quantile(p/100)
    print(f"  {p}th: {val:.3f} ms")
print()

print("="*80)
print("BY CONTRACT")
print("="*80)
for contract in sorted(df['contract'].unique()):
    subset = df[df['contract'] == contract]
    print(f"\n{contract}:")
    print(f"  N = {len(subset):,} ({100*len(subset)/len(df):.1f}%)")
    print(f"  Mean:   {subset['latency_ms'].mean():.3f} ms")
    print(f"  Median: {subset['latency_ms'].median():.3f} ms")
    print(f"  Std:    {subset['latency_ms'].std():.3f} ms")

print("\n" + "="*80)
print("BY SYMBOL (Top 5)")
print("="*80)
symbol_stats = df.groupby('symbol')['latency_ms'].agg(['count', 'mean', 'median', 'std'])
symbol_stats = symbol_stats.sort_values('count', ascending=False).head(5)
print(symbol_stats.to_string())

print("\n" + "="*80)
print("BY MPID (Top 10)")
print("="*80)
mpid_stats = df.groupby('mpid')['latency_ms'].agg(['count', 'mean', 'median', 'std'])
mpid_stats = mpid_stats.sort_values('count', ascending=False).head(10)
print(mpid_stats.to_string())

print("\n" + "="*80)
print("BY DATE")
print("="*80)
date_stats = df.groupby('date')['latency_ms'].agg(['count', 'mean', 'median'])
date_stats = date_stats.sort_index()
print(date_stats.to_string())

# Save summary
output_dir = Path('data/output/analytics')
output_dir.mkdir(parents=True, exist_ok=True)

summary_file = output_dir / 'quick_summary.txt'
with open(summary_file, 'w') as f:
    f.write(f"Dataset: {len(df):,} observations\n")
    f.write(f"Date range: {df['date'].min()} to {df['date'].max()}\n")
    f.write(f"Mean latency: {df['latency_ms'].mean():.3f} ms\n")
    f.write(f"Median latency: {df['latency_ms'].median():.3f} ms\n")
    f.write(f"\nBy Contract:\n")
    for contract in sorted(df['contract'].unique()):
        subset = df[df['contract'] == contract]
        f.write(f"{contract}: N={len(subset):,}, Mean={subset['latency_ms'].mean():.3f}ms\n")

print(f"\n✓ Summary saved to: {summary_file}")
print("\n🎉 ANALYSIS COMPLETE!")
