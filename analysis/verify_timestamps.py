"""
Detailed timestamp analysis for NASDAQ data
"""
import pandas as pd
import pyarrow.parquet as pq
from datetime import datetime, timezone

# Read one of the original hourly parquet files to check schema
hourly_file = "data/extracted/20250310/ny4-xnas-tvitch-a-20250310T130000_D-F-U-X.parquet"
print("=" * 80)
print("CHECKING ORIGINAL HOURLY FILE")
print("=" * 80)
print(f"File: {hourly_file}\n")

# Get schema
schema = pq.read_schema(hourly_file)
print("Schema:")
print(schema)
print()

# Read sample data
df_sample = pd.read_parquet(hourly_file)
print(f"Sample size: {len(df_sample):,} rows")
print(f"\nFirst 5 rows:")
print(df_sample.head())
print(f"\nColumn dtypes:")
print(df_sample.dtypes)
print()

# Analyze event_time_ns
print("=" * 80)
print("EVENT_TIME_NS ANALYSIS")
print("=" * 80)

ts_values = df_sample['event_time_ns'].values
print(f"\nRaw values (first 10):")
for i, val in enumerate(ts_values[:10]):
    print(f"  {i}: {val:,}")

print(f"\nStatistics:")
print(f"  Min: {ts_values.min():,}")
print(f"  Max: {ts_values.max():,}")
print(f"  Range: {ts_values.max() - ts_values.min():,}")

# Try different interpretations
print("\n" + "=" * 80)
print("TIMESTAMP INTERPRETATION TESTS")
print("=" * 80)

sample_ts = ts_values[0]
print(f"\nSample timestamp: {sample_ts:,}")

# Test 1: Nanoseconds since Unix epoch
print("\n1. As nanoseconds since Unix epoch:")
try:
    dt = pd.to_datetime(sample_ts, unit='ns', utc=True)
    print(f"   Result: {dt}")
    print(f"   Makes sense: {'NO - year is way off' if dt.year != 2025 else 'YES'}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 2: Microseconds since Unix epoch  
print("\n2. As microseconds since Unix epoch:")
try:
    dt = pd.to_datetime(sample_ts, unit='us', utc=True)
    print(f"   Result: {dt}")
    print(f"   Makes sense: {'NO - year is way off' if dt.year != 2025 else 'YES'}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 3: Nanoseconds since midnight March 10, 2025 UTC
march10_midnight_utc_ns = int(pd.Timestamp('2025-03-10 00:00:00', tz='UTC').value)
print(f"\n3. As nanoseconds since March 10, 2025 midnight UTC:")
print(f"   March 10 midnight UTC in ns: {march10_midnight_utc_ns:,}")
try:
    absolute_ns = march10_midnight_utc_ns + sample_ts
    dt = pd.to_datetime(absolute_ns, unit='ns', utc=True)
    print(f"   Result: {dt}")
    hours_since_midnight = (absolute_ns - march10_midnight_utc_ns) / 1e9 / 3600
    print(f"   Hours since midnight: {hours_since_midnight:.2f}")
    print(f"   Makes sense: {'YES - during trading hours' if 0 <= hours_since_midnight <= 24 else 'NO'}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 4: Check if it's actually picoseconds or something else
print(f"\n4. Checking magnitude:")
seconds_if_ns = sample_ts / 1e9
hours_if_ns = seconds_if_ns / 3600
print(f"   If nanoseconds: {seconds_if_ns:,.2f} seconds = {hours_if_ns:,.2f} hours")
print(f"   If microseconds: {sample_ts / 1e6:,.2f} seconds = {sample_ts / 1e6 / 3600:,.2f} hours")

# Test with actual market hours
print("\n" + "=" * 80)
print("MARKET HOURS CHECK")
print("=" * 80)

# Market opens at 9:30 AM ET = 2:30 PM UTC on March 10
market_open_utc = pd.Timestamp('2025-03-10 14:30:00', tz='UTC')
market_open_ns = market_open_utc.value
print(f"\nMarket open (9:30 AM ET / 14:30 UTC):")
print(f"  Timestamp: {market_open_utc}")
print(f"  In nanoseconds: {market_open_ns:,}")
print(f"  Nanoseconds since midnight: {market_open_ns - march10_midnight_utc_ns:,}")

market_close_utc = pd.Timestamp('2025-03-10 21:00:00', tz='UTC')  # 4 PM ET
market_close_ns = market_close_utc.value
print(f"\nMarket close (4:00 PM ET / 21:00 UTC):")
print(f"  Timestamp: {market_close_utc}")
print(f"  In nanoseconds: {market_close_ns:,}")
print(f"  Nanoseconds since midnight: {market_close_ns - march10_midnight_utc_ns:,}")

print(f"\nNASDAQ data range:")
print(f"  Min timestamp: {ts_values.min():,}")
print(f"  Max timestamp: {ts_values.max():,}")
print(f"  Expected range (ns since midnight): {market_open_ns - march10_midnight_utc_ns:,} to {market_close_ns - march10_midnight_utc_ns:,}")

# Check if they match
expected_min_ns = market_open_ns - march10_midnight_utc_ns
expected_max_ns = market_close_ns - march10_midnight_utc_ns
print(f"\nComparison:")
print(f"  Data min vs expected market open: {ts_values.min():,} vs {expected_min_ns:,}")
print(f"  Match: {abs(ts_values.min() - expected_min_ns) < 1e12}")

# Load the filtered targets file and check
print("\n" + "=" * 80)
print("CHECKING FILTERED TARGETS FILE")
print("=" * 80)

nq_targets = pd.read_parquet("data/nasdaq_mpid_events_20250310_targets.parquet")
print(f"Rows: {len(nq_targets):,}")
print(f"Timestamp range:")
print(f"  Min: {nq_targets['event_time_ns'].min():,}")
print(f"  Max: {nq_targets['event_time_ns'].max():,}")
print(f"\nFirst few timestamps:")
print(nq_targets[['event_time_ns', 'symbol', 'mpid']].head(10))
