# 🚀 Polars Turbo Mode (OPTIONAL)

If analytics are still too slow on 144M rows, install Polars for **10-100x speedup** on data operations.

## Quick Install

```bash
pip install polars
```

## Why Polars?

- **Rust-based**: Compiled, not interpreted like pandas
- **Lazy evaluation**: Optimizes query plans automatically  
- **Memory efficient**: 3-5x less RAM than pandas
- **Parallel by default**: Uses all CPU cores
- **10-100x faster** on groupby, filter, aggregation operations

## Minimal Code Changes

### Before (pandas):
```python
import pandas as pd

df = pd.read_parquet('data/output/latencies_combined.parquet')
firm_stats = df.groupby('firm_name')['latency_ms'].agg(['median', 'mean', 'std'])
top_firms = df[df['firm_name'].isin(top_10)]
```

### After (Polars):
```python
import polars as pl

df = pl.read_parquet('data/output/latencies_combined.parquet')
firm_stats = df.group_by('firm_name').agg([
    pl.col('latency_ms').median().alias('median'),
    pl.col('latency_ms').mean().alias('mean'),
    pl.col('latency_ms').std().alias('std')
])
top_firms = df.filter(pl.col('firm_name').is_in(top_10))

# Convert to pandas only when plotting:
firm_stats_pd = firm_stats.to_pandas()
```

## Where to Apply

### High Impact (Do These First):

1. **run_all_analytics.py** - Initial data load:
```python
# Line ~25
df = pl.read_parquet(data_path)  # Instead of pd.read_parquet
```

2. **fig_05_time_of_day.py** - Hourly groupby:
```python
df_pl = pl.from_pandas(df)
hourly = df_pl.group_by('hour').agg([
    pl.col('latency_ms').median().alias('median'),
    pl.col('latency_ms').quantile(0.25).alias('q25'),
    pl.col('latency_ms').quantile(0.75).alias('q75'),
    pl.len().alias('count')
]).sort('hour').to_pandas()
```

3. **comprehensive_stats.py** - Group summaries:
```python
# Convert once at the start
df_pl = pl.from_pandas(df)

# All groupby operations use Polars, convert to pandas at end
summary = df_pl.group_by('firm_category').agg([...]).to_pandas()
```

### Medium Impact:

- Filtering operations (e.g., `df[df['firm_name'].isin(top_firms)]`)
- Large sorts
- Time-based operations (`pd.to_datetime` → `pl.col().dt`)

### Low Impact (Keep as pandas):

- Plotting (convert to pandas right before)
- Small datasets (<1M rows)
- Correlation matrices (already sampling to 50K-100K)

## Expected Speedup

| Operation | Pandas | Polars | Speedup |
|-----------|--------|--------|---------|
| Load 144M parquet | 60 sec | 10 sec | 6x |
| Groupby median (all firms) | 45 sec | 3 sec | 15x |
| Filter to top firms | 20 sec | 2 sec | 10x |
| Hourly aggregation | 30 sec | 2 sec | 15x |
| **Total analytics** | **3-4 min** | **<2 min** | **2-3x** |

## Lazy Evaluation (Advanced)

For maximum speed, use lazy mode:

```python
df = pl.scan_parquet('data/output/latencies_combined.parquet')  # Lazy
result = (df
    .filter(pl.col('latency_ms') < 1000)
    .group_by('firm_name')
    .agg(pl.col('latency_ms').median())
    .sort('latency_ms')
    .collect()  # Execute optimized query plan
)
```

Polars automatically:
- Pushes filters down
- Eliminates unnecessary columns
- Parallelizes operations
- Minimizes memory allocations

## Gotchas

1. **Different syntax**: `group_by` not `groupby`, `filter` not boolean indexing
2. **Return types**: Polars returns Polars DataFrames, use `.to_pandas()` for plotting
3. **Column selection**: Use `pl.col('name')` not string indexing
4. **Null handling**: `None` vs `NaN` - Polars is stricter

## Is It Worth It?

- **For 144M rows**: YES - Could save 2-3 minutes on analytics
- **For 12M rows**: Maybe - Pandas is fine, but Polars is still 10x faster
- **For debugging**: No - Stick with pandas for quick iteration

## Bottom Line

**Current setup with aggressive sampling: Analytics in 3-4 min**  
**With Polars: Analytics in <2 min**

If analytics are already fast enough, don't bother. But if you're waiting around, this is the easiest 2-3x speedup you'll get.
