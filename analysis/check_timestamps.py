import pandas as pd
from datetime import datetime

# Load ES data
es = pd.read_parquet('data/es/trade_events_20250310.parquet')
print('ES Timestamps:')
print(f'  Min: {es["transact_time_ns"].min():,}')
print(f'  Max: {es["transact_time_ns"].max():,}')
print(f'  As datetime min: {pd.to_datetime(es["transact_time_ns"].min(), unit="ns", utc=True)}')
print(f'  As datetime max: {pd.to_datetime(es["transact_time_ns"].max(), unit="ns", utc=True)}')

# Load NASDAQ data
nq = pd.read_parquet('data/nasdaq_mpid_events_20250310_targets.parquet')
print(f'\nNASDAQ Timestamps (raw event_time_ns):')
print(f'  Min: {nq["event_time_ns"].min():,}')
print(f'  Max: {nq["event_time_ns"].max():,}')

# Check March 10, 2025 midnight
march_10_midnight_utc = int(pd.Timestamp('2025-03-10 00:00:00', tz='UTC').value)
print(f'\nMarch 10, 2025 midnight UTC in ns: {march_10_midnight_utc:,}')

# What do NASDAQ timestamps look like when added to March 10 midnight?
nq_converted_min = march_10_midnight_utc + nq["event_time_ns"].min()
nq_converted_max = march_10_midnight_utc + nq["event_time_ns"].max()
print(f'\nNASDAQ converted (midnight + event_time_ns):')
print(f'  Min: {nq_converted_min:,}')
print(f'  Max: {nq_converted_max:,}')
print(f'  As datetime min: {pd.to_datetime(nq_converted_min, unit="ns", utc=True)}')
print(f'  As datetime max: {pd.to_datetime(nq_converted_max, unit="ns", utc=True)}')

# Check overlap
print(f'\nOverlap check:')
print(f'  ES range:     {es["transact_time_ns"].min():,} to {es["transact_time_ns"].max():,}')
print(f'  NASDAQ range: {nq_converted_min:,} to {nq_converted_max:,}')
print(f'  Overlap: {"YES" if nq_converted_max >= es["transact_time_ns"].min() and nq_converted_min <= es["transact_time_ns"].max() else "NO"}')
