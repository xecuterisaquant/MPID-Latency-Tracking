"""
Comprehensive NASDAQ Data Verification

Analyzes all parquet files and provides detailed statistics to verify against teammate's results.
Reports on: rows, MPIDs, symbols, message types, and more.
"""
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from collections import Counter
import numpy as np

data_dir = Path("data/extracted/20250310")
all_files = sorted(data_dir.glob("*.parquet"))

print("=" * 100)
print("COMPREHENSIVE NASDAQ DATA VERIFICATION")
print("=" * 100)
print(f"\n📁 Directory: {data_dir}")
print(f"📁 Total parquet files: {len(all_files)}")
print(f"📁 File list (first 10):")
for f in all_files[:10]:
    size_mb = f.stat().st_size / 1024 / 1024
    print(f"   {f.name:50s} {size_mb:>8.2f} MB")
if len(all_files) > 10:
    print(f"   ... and {len(all_files) - 10} more files")

print("\n" + "=" * 100)
print("STREAMING ANALYSIS (Processing all files...)")
print("=" * 100)

# Initialize counters
total_rows = 0
mpid_counter = Counter()
symbol_counter = Counter()
msgtype_counter = Counter()
side_counter = Counter()

# Track timestamps
min_timestamp = float('inf')
max_timestamp = 0

# Track unique values for verification
all_mpids = set()
all_symbols = set()
all_msgtypes = set()

# Price and size stats
prices = []
sizes = []

# Track target symbols specifically
target_symbols = ['QQQ', 'IWM', 'TSLA', 'AAPL', 'SPY', 'NVDA', 'AMZN', 'MSFT', 'GOOGL', 'META']
target_symbol_counter = Counter()
target_msgtype_counter = Counter()

print("\nProcessing files...")
for i, filepath in enumerate(all_files):
    # Read file
    df = pd.read_parquet(filepath)
    total_rows += len(df)
    
    # Update counters
    mpid_counter.update(df['mpid'].value_counts().to_dict())
    symbol_counter.update(df['symbol'].value_counts().to_dict())
    msgtype_counter.update(df['message_type'].value_counts().to_dict())
    
    if 'side' in df.columns:
        side_counter.update(df['side'].value_counts().to_dict())
    
    # Track unique values
    all_mpids.update(df['mpid'].unique())
    all_symbols.update(df['symbol'].unique())
    all_msgtypes.update(df['message_type'].unique())
    
    # Timestamps
    if len(df) > 0:
        min_timestamp = min(min_timestamp, df['event_time_ns'].min())
        max_timestamp = max(max_timestamp, df['event_time_ns'].max())
    
    # Sample prices and sizes for stats (take samples to avoid memory issues)
    if len(df) > 0:
        sample_size = min(1000, len(df))
        sample_df = df.sample(n=sample_size) if len(df) > sample_size else df
        if 'price' in sample_df.columns:
            prices.extend(sample_df['price'].tolist())
        if 'size' in sample_df.columns:
            sizes.extend(sample_df['size'].tolist())
    
    # Target symbols
    target_df = df[df['symbol'].isin(target_symbols)]
    if len(target_df) > 0:
        target_symbol_counter.update(target_df['symbol'].value_counts().to_dict())
        target_msgtype_counter.update(target_df['message_type'].value_counts().to_dict())
    
    if (i + 1) % 10 == 0:
        print(f"  [{i+1:2d}/{len(all_files):2d}] Processed {total_rows:>12,} rows so far...")

print(f"\n✅ Completed processing all {len(all_files)} files")

# ============================================================================
# RESULTS
# ============================================================================

print("\n" + "=" * 100)
print("OVERALL STATISTICS")
print("=" * 100)

print(f"\n📊 Total Events: {total_rows:,}")
print(f"📊 Unique MPIDs: {len(all_mpids)}")
print(f"📊 Unique Symbols: {len(all_symbols)}")
print(f"📊 Unique Message Types: {len(all_msgtypes)}")

print(f"\n⏰ Timestamp Range:")
print(f"   Min: {min_timestamp:,} ns")
print(f"   Max: {max_timestamp:,} ns")
print(f"   Span: {(max_timestamp - min_timestamp) / 1e9:.2f} seconds ({(max_timestamp - min_timestamp) / 3.6e12:.2f} hours)")

# ============================================================================
# MESSAGE TYPE BREAKDOWN
# ============================================================================

print("\n" + "=" * 100)
print("MESSAGE TYPE DISTRIBUTION (ALL EVENTS)")
print("=" * 100)

print(f"\n{'Message Type':>15s} {'Code':>6s} {'Events':>12s} {'Percent':>10s}")
print("-" * 50)
for msg_type in sorted(msgtype_counter.keys()):
    count = msgtype_counter[msg_type]
    pct = 100 * count / total_rows
    # Try to map to code (common mappings)
    code_map = {
        'Replace': 'U',
        'AddOrderMPID': 'F',
        'Delete': 'D',
        'Cancel': 'X',
        'AddOrder': 'A',
        'Execute': 'E',
    }
    code = code_map.get(msg_type, '?')
    print(f"{msg_type:>15s} {code:>6s} {count:>12,} {pct:>9.2f}%")

print(f"\n{'Total':>15s} {' ':>6s} {total_rows:>12,} {100.0:>9.2f}%")

# ============================================================================
# SYMBOL BREAKDOWN
# ============================================================================

print("\n" + "=" * 100)
print("SYMBOL DISTRIBUTION (ALL SYMBOLS)")
print("=" * 100)

print(f"\n{'Symbol':>10s} {'Events':>12s} {'% of Total':>12s}")
print("-" * 40)

# Top 20 symbols
for symbol, count in symbol_counter.most_common(20):
    pct = 100 * count / total_rows
    print(f"{symbol:>10s} {count:>12,} {pct:>11.2f}%")

if len(symbol_counter) > 20:
    print(f"... and {len(symbol_counter) - 20} more symbols")

# ============================================================================
# TARGET SYMBOLS
# ============================================================================

print("\n" + "=" * 100)
print("TARGET SYMBOLS (10 FOCUS SYMBOLS)")
print("=" * 100)

print(f"\n{'Symbol':>10s} {'Events':>12s} {'% of Total':>12s}")
print("-" * 40)

total_target_events = sum(target_symbol_counter.values())
for symbol in target_symbols:
    count = target_symbol_counter.get(symbol, 0)
    pct = 100 * count / total_rows
    print(f"{symbol:>10s} {count:>12,} {pct:>11.2f}%")

print("-" * 40)
print(f"{'TOTAL TARGET':>10s} {total_target_events:>12,} {100*total_target_events/total_rows:>11.2f}%")

# ============================================================================
# MPID BREAKDOWN
# ============================================================================

print("\n" + "=" * 100)
print("MPID DISTRIBUTION (TOP 20)")
print("=" * 100)

print(f"\n{'MPID':>10s} {'Events':>12s} {'% of Total':>12s}")
print("-" * 40)

for mpid, count in mpid_counter.most_common(20):
    pct = 100 * count / total_rows
    print(f"{mpid:>10s} {count:>12,} {pct:>11.2f}%")

if len(mpid_counter) > 20:
    print(f"... and {len(mpid_counter) - 20} more MPIDs")

# ============================================================================
# SIDE DISTRIBUTION
# ============================================================================

if side_counter:
    print("\n" + "=" * 100)
    print("SIDE DISTRIBUTION")
    print("=" * 100)
    
    print(f"\n{'Side':>10s} {'Events':>12s} {'% of Total':>12s}")
    print("-" * 40)
    for side, count in side_counter.most_common():
        pct = 100 * count / total_rows
        print(f"{side:>10s} {count:>12,} {pct:>11.2f}%")

# ============================================================================
# PRICE AND SIZE STATISTICS
# ============================================================================

if prices:
    print("\n" + "=" * 100)
    print("PRICE STATISTICS (SAMPLED)")
    print("=" * 100)
    
    prices_array = np.array(prices)
    print(f"\n  Sample size: {len(prices):,}")
    print(f"  Min:  {prices_array.min():,}")
    print(f"  Max:  {prices_array.max():,}")
    print(f"  Mean: {prices_array.mean():,.2f}")
    print(f"  Median: {np.median(prices_array):,.2f}")

if sizes:
    print("\n" + "=" * 100)
    print("SIZE STATISTICS (SAMPLED)")
    print("=" * 100)
    
    sizes_array = np.array(sizes)
    print(f"\n  Sample size: {len(sizes):,}")
    print(f"  Min:  {sizes_array.min():,}")
    print(f"  Max:  {sizes_array.max():,}")
    print(f"  Mean: {sizes_array.mean():,.2f}")
    print(f"  Median: {np.median(sizes_array):,.2f}")

# ============================================================================
# TARGET SYMBOLS MESSAGE TYPE BREAKDOWN
# ============================================================================

print("\n" + "=" * 100)
print("MESSAGE TYPE DISTRIBUTION (TARGET SYMBOLS ONLY)")
print("=" * 100)

print(f"\n{'Message Type':>15s} {'Code':>6s} {'Events':>12s} {'Percent':>10s}")
print("-" * 50)

code_map = {
    'Replace': 'U',
    'AddOrderMPID': 'F',
    'Delete': 'D',
    'Cancel': 'X',
}

for msg_type in sorted(target_msgtype_counter.keys()):
    count = target_msgtype_counter[msg_type]
    pct = 100 * count / total_target_events
    code = code_map.get(msg_type, '?')
    print(f"{msg_type:>15s} {code:>6s} {count:>12,} {pct:>9.2f}%")

print(f"\n{'Total':>15s} {' ':>6s} {total_target_events:>12,} {100.0:>9.2f}%")

# ============================================================================
# COMPARISON WITH TEAMMATE'S RESULTS
# ============================================================================

print("\n" + "=" * 100)
print("VERIFICATION AGAINST TEAMMATE'S RESULTS")
print("=" * 100)

teammate_results = {
    'total_events': 144413922,
    'unique_mpids': 87,
    'unique_symbols': 11235,
    'message_types': {
        'Replace': (140667372, 97.41),
        'AddOrderMPID': (2640990, 1.83),
        'Delete': (1105129, 0.77),
        'Cancel': (431, 0.00),
    },
    'top_symbols': {
        'QQQ': 8849113,
        'SPY': 4985063,
        'NVDA': 3368530,
        'AAPL': 3041194,
        'AMZN': 2553778,
        'IWM': 2279501,
        'TSLA': 2092845,
        'GOOGL': 2009516,
        'MSFT': 1199117,
        'META': 297748,
    }
}

print("\n📋 Total Events:")
print(f"   Teammate: {teammate_results['total_events']:,}")
print(f"   Our calc: {total_rows:,}")
print(f"   Match: {'✅' if total_rows == teammate_results['total_events'] else '❌ MISMATCH'}")

print("\n📋 Unique MPIDs:")
print(f"   Teammate: {teammate_results['unique_mpids']}")
print(f"   Our calc: {len(all_mpids)}")
print(f"   Match: {'✅' if len(all_mpids) == teammate_results['unique_mpids'] else '❌ MISMATCH'}")

print("\n📋 Unique Symbols:")
print(f"   Teammate: {teammate_results['unique_symbols']}")
print(f"   Our calc: {len(all_symbols)}")
print(f"   Match: {'✅' if len(all_symbols) == teammate_results['unique_symbols'] else '❌ MISMATCH'}")

print("\n📋 Message Type Counts:")
for msg_type, (expected_count, expected_pct) in teammate_results['message_types'].items():
    our_count = msgtype_counter.get(msg_type, 0)
    our_pct = 100 * our_count / total_rows if total_rows > 0 else 0
    match = '✅' if our_count == expected_count else '❌ MISMATCH'
    print(f"   {msg_type:>15s}: Expected {expected_count:>10,} ({expected_pct:>5.2f}%) | Got {our_count:>10,} ({our_pct:>5.2f}%) | {match}")

print("\n📋 Target Symbol Counts:")
for symbol, expected_count in teammate_results['top_symbols'].items():
    our_count = symbol_counter.get(symbol, 0)
    match = '✅' if our_count == expected_count else '❌ MISMATCH'
    diff = our_count - expected_count
    print(f"   {symbol:>6s}: Expected {expected_count:>9,} | Got {our_count:>9,} | Diff: {diff:>+9,} | {match}")

print("\n" + "=" * 100)
print("VERIFICATION COMPLETE")
print("=" * 100)
