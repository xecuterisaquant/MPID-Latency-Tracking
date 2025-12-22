import pandas as pd
from pathlib import Path

print('='*70)
print('DUAL-CONTRACT LATENCY ANALYSIS - March 10, 2025')
print('='*70)

# Load both contract results
output_dir = Path('data/output')
files = {
    'ESH25': output_dir / 'latencies_20250310_ESH25.parquet',
    'ESM25': output_dir / 'latencies_20250310_ESM25.parquet'
}

results = {}
for contract, filepath in files.items():
    if filepath.exists():
        results[contract] = pd.read_parquet(filepath)
        print(f'\n✅ Loaded {contract}: {len(results[contract]):,} matches')
    else:
        print(f'\n❌ Missing {contract}: {filepath.name}')

if not results:
    print('\nNo results files found!')
    exit()

print('\n' + '='*70)
print('CONTRACT COMPARISON')
print('='*70)

for contract, df in results.items():
    print(f'\n{contract} ({"Expiring" if contract == "ESH25" else "Next"} Contract):')
    print(f'  Total matches: {len(df):,}')
    print(f'  Unique MPIDs: {df["mpid"].nunique()}')
    print(f'  Unique symbols: {df["symbol"].nunique()}')
    
    print(f'\n  Latency Distribution (milliseconds):')
    latency_ms = df['latency_ns'] / 1_000_000
    print(f'    Min:    {latency_ms.min():.3f} ms')
    print(f'    25th:   {latency_ms.quantile(0.25):.3f} ms')
    print(f'    Median: {latency_ms.median():.3f} ms')
    print(f'    75th:   {latency_ms.quantile(0.75):.3f} ms')
    print(f'    95th:   {latency_ms.quantile(0.95):.3f} ms')
    print(f'    Max:    {latency_ms.max():.3f} ms')
    print(f'    Mean:   {latency_ms.mean():.3f} ms')
    
    print(f'\n  Top 5 Symbols:')
    for symbol, count in df['symbol'].value_counts().head(5).items():
        print(f'    {symbol}: {count:,} matches')
    
    print(f'\n  Top 5 MPIDs:')
    for mpid, count in df['mpid'].value_counts().head(5).items():
        print(f'    {mpid}: {count:,} matches')

# If we have both contracts, compare them
if len(results) == 2:
    print('\n' + '='*70)
    print('CROSS-CONTRACT INSIGHTS')
    print('='*70)
    
    esh_df = results['ESH25']
    esm_df = results['ESM25']
    
    print(f'\nMatch Count Difference:')
    diff = len(esh_df) - len(esm_df)
    pct = (diff / len(esh_df)) * 100
    print(f'  ESH25 has {abs(diff):,} {"more" if diff > 0 else "fewer"} matches ({abs(pct):.1f}%)')
    
    print(f'\nLatency Comparison:')
    esh_median = (esh_df['latency_ns'] / 1_000_000).median()
    esm_median = (esm_df['latency_ns'] / 1_000_000).median()
    print(f'  ESH25 median: {esh_median:.3f} ms')
    print(f'  ESM25 median: {esm_median:.3f} ms')
    print(f'  Difference: {esm_median - esh_median:.3f} ms ({"ESM25 slower" if esm_median > esh_median else "ESM25 faster"})')
    
    # Check which MPIDs react to both vs only one
    esh_mpids = set(esh_df['mpid'].unique())
    esm_mpids = set(esm_df['mpid'].unique())
    
    both = esh_mpids & esm_mpids
    esh_only = esh_mpids - esm_mpids
    esm_only = esm_mpids - esh_mpids
    
    print(f'\nMPID Activity:')
    print(f'  Active in both contracts: {len(both)} MPIDs')
    print(f'  ESH25 only: {len(esh_only)} MPIDs {list(esh_only) if esh_only else ""}')
    print(f'  ESM25 only: {len(esm_only)} MPIDs {list(esm_only) if esm_only else ""}')
    
    # Trading volume comparison from ES source
    print(f'\n' + '='*70)
    print('ES TRADING VOLUME (from source data)')
    print('='*70)
    es_df = pd.read_parquet('data/es/trade_events_20250310.parquet')
    from config import ES_SECURITY_IDS
    es_df['contract'] = es_df['security_id'].map(ES_SECURITY_IDS)
    
    for contract in ['ESH25', 'ESM25']:
        contract_trades = es_df[es_df['contract'] == contract]
        if len(contract_trades) > 0:
            print(f'\n{contract}:')
            print(f'  ES Trades: {len(contract_trades):,}')
            print(f'  NASDAQ Matches: {len(results[contract]):,} (ratio: {len(results[contract])/len(contract_trades):.1f}x)')
            print(f'  Match percentage: {(len(results[contract])/len(contract_trades))*100:.1f}% of ES trades triggered NASDAQ response')

print('\n' + '='*70)
print('ANALYSIS COMPLETE')
print('='*70)
