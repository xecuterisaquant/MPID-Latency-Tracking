import pandas as pd

# ES data - already in Unix epoch nanoseconds
es = pd.read_parquet('data/es/trade_events_20250310.parquet')
es_min = es['transact_time_ns'].min()
es_max = es['transact_time_ns'].max()

print('ES Data:')
print(f'  Min: {es_min:,}')
print(f'  Max: {es_max:,}')
es_min_dt = pd.to_datetime(es_min, unit='ns', utc=True)
es_max_dt = pd.to_datetime(es_max, unit='ns', utc=True)
print(f'  As datetime: {es_min_dt} to {es_max_dt}')

# NASDAQ data - nanoseconds since midnight Eastern
nq = pd.read_parquet('data/nasdaq_mpid_events_20250310_targets.parquet')
nq_min = nq['event_time_ns'].min()
nq_max = nq['event_time_ns'].max()

print(f'\nNASDAQ Data (raw):')
print(f'  Min: {nq_min:,}')
print(f'  Max: {nq_max:,}')
print(f'  Hours since midnight: {nq_min/1e9/3600:.2f} to {nq_max/1e9/3600:.2f}')

# Convert NASDAQ to absolute using Eastern Time midnight
eastern_midnight = pd.Timestamp('2025-03-10', tz='America/New_York')
print(f'\nEastern midnight: {eastern_midnight}')
print(f'  As ns: {eastern_midnight.value:,}')

nq_abs_min = eastern_midnight.value + nq_min
nq_abs_max = eastern_midnight.value + nq_max

print(f'\nNASDAQ Data (converted to absolute):')
print(f'  Min: {nq_abs_min:,}')
print(f'  Max: {nq_abs_max:,}')
nq_abs_min_dt = pd.to_datetime(nq_abs_min, unit='ns', utc=True)
nq_abs_max_dt = pd.to_datetime(nq_abs_max, unit='ns', utc=True)
print(f'  As datetime: {nq_abs_min_dt} to {nq_abs_max_dt}')

print(f'\nOverlap check:')
print(f'  ES:     {es_min:,} to {es_max:,}')
print(f'  NASDAQ: {nq_abs_min:,} to {nq_abs_max:,}')
overlap = nq_abs_max >= es_min and nq_abs_min <= es_max
print(f'  Overlap: {"YES" if overlap else "NO"}')

if not overlap:
    diff = es_min - nq_abs_max if es_min > nq_abs_max else nq_abs_min - es_max
    print(f'  Gap: {diff/1e9:.2f} seconds = {diff/3.6e12:.2f} hours')
