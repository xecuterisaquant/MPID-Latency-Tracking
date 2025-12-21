"""
Memory-efficient NASDAQ data analysis with chunking
"""
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from collections import Counter, defaultdict

data_dir = Path("data/extracted/20250310")
all_files = sorted(data_dir.glob("*.parquet"))

print(f"📁 Total files: {len(all_files)}")
print("=" * 80)

# Streaming aggregation to avoid memory issues
print("\n📊 Analyzing data in chunks...")

total_rows = 0
mpid_counter = Counter()
symbol_counter = Counter()
msgtype_counter = Counter()
target_symbols = ['QQQ', 'IWM', 'TSLA', 'AAPL', 'SPY', 'NVDA', 'AMZN', 'MSFT', 'GOOGL', 'META']
target_symbol_data = []

min_timestamp = float('inf')
max_timestamp = 0

for i, f in enumerate(all_files):
    df = pq.read_table(f).to_pandas()
    total_rows += len(df)
    
    # Aggregate counters
    mpid_counter.update(df['mpid'].value_counts().to_dict())
    symbol_counter.update(df['symbol'].value_counts().to_dict())
    msgtype_counter.update(df['message_type'].value_counts().to_dict())
    
    # Track timestamps
    if len(df) > 0:
        min_timestamp = min(min_timestamp, df['event_time_ns'].min())
        max_timestamp = max(max_timestamp, df['event_time_ns'].max())
    
    # Collect target symbol data
    target_df = df[df['symbol'].isin(target_symbols)]
    if len(target_df) > 0:
        target_symbol_data.append(target_df)
    
    if (i + 1) % 10 == 0:
        print(f"  Processed {i+1}/{len(all_files)} files... ({total_rows:,} rows)")

print(f"\n✅ Total rows analyzed: {total_rows:,}")

# Print statistics
print("\n" + "=" * 80)
print("📊 SUMMARY STATISTICS")
print("=" * 80)

print(f"\n⏰ Timestamp Range:")
print(f"   Min: {min_timestamp:,}")
print(f"   Max: {max_timestamp:,}")
print(f"   Span: {(max_timestamp - min_timestamp) / 1e9:.2f} seconds ({(max_timestamp - min_timestamp) / 1e9 / 3600:.2f} hours)")

# Decode timestamps - try different interpretations
print(f"\n🔍 Timestamp Interpretation:")
print(f"   Raw min: {min_timestamp}")
print(f"   As Unix epoch ns: {pd.to_datetime(min_timestamp, unit='ns')}")
print(f"   As ns since midnight (2025-03-10): {pd.Timestamp('2025-03-10') + pd.Timedelta(min_timestamp, unit='ns')}")

print(f"\n📍 MPIDs ({len(mpid_counter)} unique):")
for mpid, count in sorted(mpid_counter.items(), key=lambda x: x[1], reverse=True)[:15]:
    pct = 100 * count / total_rows
    print(f"   {mpid:8s}: {count:>12,} events ({pct:>5.2f}%)")

print(f"\n🏷️  Symbols ({len(symbol_counter)} unique):")
for symbol, count in sorted(symbol_counter.items(), key=lambda x: x[1], reverse=True)[:25]:
    pct = 100 * count / total_rows
    print(f"   {symbol:8s}: {count:>12,} events ({pct:>5.2f}%)")

print(f"\n📝 Message Types:")
for msgtype, count in sorted(msgtype_counter.items(), key=lambda x: x[1], reverse=True):
    pct = 100 * count / total_rows
    print(f"   {msgtype:15s}: {count:>12,} events ({pct:>5.2f}%)")

# Target symbols analysis
present_targets = [s for s in target_symbols if s in symbol_counter]
print(f"\n🎯 Target Symbols ({len(present_targets)}/{len(target_symbols)} found):")
for sym in target_symbols:
    if sym in symbol_counter:
        count = symbol_counter[sym]
        pct = 100 * count / total_rows
        print(f"   ✓ {sym:8s}: {count:>12,} events ({pct:>5.2f}%)")
    else:
        print(f"   ✗ {sym:8s}: Not found")

# Save target symbol data
if target_symbol_data:
    print(f"\n💾 Saving filtered data (target symbols only)...")
    combined_targets = pd.concat(target_symbol_data, ignore_index=True)
    
    output_path = Path("data/nasdaq_mpid_events_20250310_targets.parquet")
    # Save directly without sorting to avoid memory issues - will sort during join
    combined_targets.to_parquet(output_path, index=False, compression='snappy')
    
    print(f"   ✅ Saved {len(combined_targets):,} events")
    print(f"   📁 {output_path}")
    print(f"   💿 {output_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    print(f"\n📋 Target Symbol Dataset:")
    print(f"   Symbols: {sorted(combined_targets['symbol'].unique())}")
    print(f"   MPIDs: {len(combined_targets['mpid'].unique())} unique")
    print(f"   Message types: {combined_targets['message_type'].value_counts().to_dict()}")

print(f"\n{'=' * 80}")
print("✅ ANALYSIS COMPLETE")
print("=" * 80)
