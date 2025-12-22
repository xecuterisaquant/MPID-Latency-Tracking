"""
Quick stats extraction for report placeholders
No bootstrap, just direct calculations
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from mpid_lookup.mpid_to_firm import get_firm_name, get_firm_category

print("Loading data...")
df = pd.read_parquet('outputs/latencies/latencies_multiday_combined.parquet')
print(f"✓ Loaded {len(df):,} observations\n")

# Add firm info
print("Adding firm mappings...")
df['firm_name'] = df['mpid'].map({
    mpid: get_firm_name(mpid) for mpid in df['mpid'].unique()
})
df['firm_category'] = df['mpid'].map({
    mpid: get_firm_category(mpid) for mpid in df['mpid'].unique()
})
df['hour'] = pd.to_datetime(df['es_trade_time_ns'], unit='ns').dt.hour
print("✓ Mappings added\n")

# ============================================================================
# 1. Overall Statistics (Table 1)
# ============================================================================
print("="*80)
print("TABLE 1: OVERALL LATENCY STATISTICS")
print("="*80)
latency = df['latency_ms'].values

stats = {
    'N observations': len(latency),
    'Mean (ms)': np.mean(latency),
    'Median (ms)': np.median(latency),
    'p10 (ms)': np.percentile(latency, 10),
    'p25 (ms)': np.percentile(latency, 25),
    'p75 (ms)': np.percentile(latency, 75),
    'p90 (ms)': np.percentile(latency, 90),
    'p95 (ms)': np.percentile(latency, 95),
    'p99 (ms)': np.percentile(latency, 99),
    'Std Dev (ms)': np.std(latency),
    'Min (ms)': np.min(latency),
    'Max (ms)': np.max(latency)
}

for key, val in stats.items():
    if key == 'N observations':
        print(f"{key:20s}: {val:,}")
    else:
        print(f"{key:20s}: {val:,.3f}")

# ============================================================================
# 2. Top MPIDs (Table 2)
# ============================================================================
print("\n" + "="*80)
print("TABLE 2: TOP 15 MPIDS")
print("="*80)
mpid_stats = df.groupby('mpid').agg({
    'latency_ms': ['count', 'median', 'mean', lambda x: np.percentile(x, 10), 
                   lambda x: np.percentile(x, 90), 'std']
}).round(3)
mpid_stats.columns = ['N obs', 'Median (ms)', 'Mean (ms)', 'p10 (ms)', 'p90 (ms)', 'Std Dev (ms)']
mpid_stats = mpid_stats.sort_values('N obs', ascending=False).head(15)
print(mpid_stats.to_string())

# ============================================================================
# 3. Hour of Day (Table 3)
# ============================================================================
print("\n" + "="*80)
print("TABLE 3: LATENCY BY HOUR OF DAY")
print("="*80)
hourly = df.groupby('hour').agg({
    'latency_ms': ['count', 'median', 'mean', lambda x: np.percentile(x, 25), 
                   lambda x: np.percentile(x, 75)]
}).round(3)
hourly.columns = ['N obs', 'Median (ms)', 'Mean (ms)', 'p25 (ms)', 'p75 (ms)']
print(hourly.to_string())

# ============================================================================
# 4. Symbols (Table 4)
# ============================================================================
print("\n" + "="*80)
print("TABLE 4: LATENCY BY SYMBOL")
print("="*80)
symbol_stats = df.groupby('symbol').agg({
    'latency_ms': ['count', 'median', 'mean', lambda x: np.percentile(x, 10), 
                   lambda x: np.percentile(x, 90)]
}).round(3)
symbol_stats.columns = ['N obs', 'Median (ms)', 'Mean (ms)', 'p10 (ms)', 'p90 (ms)']
symbol_stats = symbol_stats.sort_values('Median (ms)')
print(symbol_stats.to_string())

# ============================================================================
# 5. Event Types (Table 5)
# ============================================================================
print("\n" + "="*80)
print("TABLE 5: LATENCY BY EVENT TYPE")
print("="*80)
event_stats = df.groupby('event_type').agg({
    'latency_ms': ['count', 'median', 'mean', lambda x: np.percentile(x, 10), 
                   lambda x: np.percentile(x, 90)]
}).round(3)
event_stats.columns = ['N obs', 'Median (ms)', 'Mean (ms)', 'p10 (ms)', 'p90 (ms)']
print(event_stats.to_string())

# ============================================================================
# 6. Firm Categories
# ============================================================================
print("\n" + "="*80)
print("FIRM CATEGORIES")
print("="*80)
category_stats = df.groupby('firm_category').agg({
    'latency_ms': ['count', 'median', 'mean']
}).round(3)
category_stats.columns = ['N obs', 'Median (ms)', 'Mean (ms)']
print(category_stats.to_string())

# ============================================================================
# 7. Contracts
# ============================================================================
if 'contract' in df.columns:
    print("\n" + "="*80)
    print("CONTRACTS")
    print("="*80)
    contract_stats = df.groupby('contract').agg({
        'latency_ms': ['count', 'median', 'mean']
    }).round(3)
    contract_stats.columns = ['N obs', 'Median (ms)', 'Mean (ms)']
    print(contract_stats.to_string())

# ============================================================================
# 8. Top Firms with Names
# ============================================================================
print("\n" + "="*80)
print("TOP 15 FIRMS (WITH NAMES)")
print("="*80)
firm_stats = df.groupby(['mpid', 'firm_name']).agg({
    'latency_ms': ['count', 'median', 'mean']
}).round(3)
firm_stats.columns = ['N obs', 'Median (ms)', 'Mean (ms)']
firm_stats = firm_stats.sort_values('N obs', ascending=False).head(15)
print(firm_stats.to_string())

print("\n✓ Statistics extraction complete!")
