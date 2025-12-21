"""
Deep dive into NASDAQ data - check multiple files and aggregations
"""
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from collections import Counter

data_dir = Path("data/extracted/20250310")
all_files = sorted(data_dir.glob("*.parquet"))

print(f"📁 Total files: {len(all_files)}")
print(f"Time range: {all_files[0].stem.split('_')[0][-15:]} to {all_files[-1].stem.split('_')[0][-15:]}")
print("=" * 80)

# Load all data
print("\n📥 Loading all parquet files...")
dfs = []
for i, f in enumerate(all_files):
    df = pq.read_table(f).to_pandas()
    dfs.append(df)
    if (i + 1) % 10 == 0:
        print(f"  Loaded {i+1}/{len(all_files)} files...")

full_df = pd.concat(dfs, ignore_index=True)
print(f"\n✅ Loaded {len(full_df):,} total rows")

# Detailed analysis
print("\n" + "=" * 80)
print("📊 COMPREHENSIVE DATA ANALYSIS")
print("=" * 80)

print(f"\n🔢 Total Events: {len(full_df):,}")
print(f"📅 Date: 2025-03-10")

if 'event_time_ns' in full_df.columns:
    full_df['datetime'] = pd.to_datetime(full_df['event_time_ns'], unit='ns')
    print(f"⏰ Time Range:")
    print(f"   Start: {full_df['datetime'].min()}")
    print(f"   End:   {full_df['datetime'].max()}")
    
    # Convert to ET
    full_df['datetime_et'] = full_df['datetime'].dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    full_df['hour_et'] = full_df['datetime_et'].dt.hour
    print(f"\n⏰ Market Hours (ET):")
    print(f"   Start: {full_df['datetime_et'].min()}")
    print(f"   End:   {full_df['datetime_et'].max()}")

print(f"\n📍 MPIDs:")
mpid_counts = full_df['mpid'].value_counts()
print(f"   Unique: {len(mpid_counts)}")
print(f"   Top 10:")
for mpid, count in mpid_counts.head(10).items():
    print(f"      {mpid}: {count:,} events")

print(f"\n🏷️  Symbols:")
symbol_counts = full_df['symbol'].value_counts()
print(f"   Unique: {len(symbol_counts)}")
print(f"   Top 20:")
for sym, count in symbol_counts.head(20).items():
    print(f"      {sym}: {count:,} events")

# Check for target symbols
target_symbols = ['QQQ', 'IWM', 'TSLA', 'AAPL', 'SPY', 'NVDA', 'AMZN', 'MSFT', 'GOOGL', 'META']
present_targets = [s for s in target_symbols if s in symbol_counts.index]
print(f"\n🎯 Target Symbols Found: {len(present_targets)}/{len(target_symbols)}")
for sym in present_targets:
    print(f"   {sym}: {symbol_counts[sym]:,} events")

print(f"\n📝 Message Types:")
for msg_type, count in full_df['message_type'].value_counts().items():
    pct = 100 * count / len(full_df)
    print(f"   {msg_type}: {count:,} ({pct:.1f}%)")

if 'hour_et' in full_df.columns:
    print(f"\n🕐 Events by Hour (ET):")
    hourly = full_df.groupby('hour_et').size().sort_index()
    for hour, count in hourly.items():
        print(f"   {hour:02d}:00 - {count:,} events")

# Save summary
summary = {
    'total_events': len(full_df),
    'unique_mpids': len(mpid_counts),
    'unique_symbols': len(symbol_counts),
    'target_symbols_found': present_targets,
    'date': '2025-03-10',
    'time_range_utc': (str(full_df['datetime'].min()), str(full_df['datetime'].max())),
}

print(f"\n💾 Saving clean dataset...")
output_path = Path("data/nasdaq_mpid_events_20250310.parquet")
full_df.to_parquet(output_path, index=False)
print(f"✅ Saved to: {output_path}")
print(f"   Size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")

# Create a filtered version with only target symbols
if present_targets:
    filtered_df = full_df[full_df['symbol'].isin(target_symbols)].copy()
    filtered_path = Path("data/nasdaq_mpid_events_20250310_filtered.parquet")
    filtered_df.to_parquet(filtered_path, index=False)
    print(f"\n📌 Filtered dataset (target symbols only):")
    print(f"   Events: {len(filtered_df):,}")
    print(f"   Saved to: {filtered_path}")
    print(f"   Size: {filtered_path.stat().st_size / 1024 / 1024:.2f} MB")
