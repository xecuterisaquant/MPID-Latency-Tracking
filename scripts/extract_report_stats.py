"""
Report statistics extraction.

Computes every table in the report (overall distribution, per-MPID, hour-of-day,
per-symbol, per-event-type, firm categories, contracts, top firms) directly from
the combined latencies parquet.

Runs on Polars with **lazy evaluation** (`scan_parquet`): each table is its own
lazy query, so the optimizer applies projection pushdown -- a table that needs
only `mpid` and `latency_ms` reads just those columns off disk and streams the
group-by, instead of materializing the full ~93M-row frame in memory the way an
eager pandas load would. Quantile interpolation is fixed to 'linear' so the
numbers match the original report exactly.
"""
import argparse
from pathlib import Path
import sys

import polars as pl

sys.path.append(str(Path(__file__).parent.parent))
from mpid_lookup.mpid_to_firm import get_firm_name, get_firm_category

DEFAULT_DATA = 'outputs/latencies/latencies_multiday_combined.parquet'

# Quantile interpolation: 'linear' matches numpy.percentile / pandas defaults,
# so Polars reproduces the original report figures exactly.
Q = 'linear'


def _agg_exprs(percentiles=(), *, std=False, std_ddof=1):
    """Standard latency aggregation expressions reused across every table."""
    exprs = [
        pl.len().alias('N obs'),
        pl.col('latency_ms').median().alias('Median (ms)'),
        pl.col('latency_ms').mean().alias('Mean (ms)'),
    ]
    for p in percentiles:
        exprs.append(
            pl.col('latency_ms').quantile(p / 100, interpolation=Q).alias(f'p{p} (ms)')
        )
    if std:
        exprs.append(pl.col('latency_ms').std(ddof=std_ddof).alias('Std Dev (ms)'))
    return exprs


def _print(df: pl.DataFrame, round_to: int = 3):
    """Pretty-print a Polars summary table, rounding float columns."""
    float_cols = [c for c, t in df.schema.items() if t in (pl.Float64, pl.Float32)]
    if float_cols:
        df = df.with_columns([pl.col(c).round(round_to) for c in float_cols])
    with pl.Config(tbl_rows=50, tbl_cols=-1, tbl_width_chars=200):
        print(df)


def main():
    parser = argparse.ArgumentParser(description='Extract report statistics with Polars (lazy)')
    parser.add_argument('--data', default=DEFAULT_DATA, help='Path to latencies parquet')
    args = parser.parse_args()

    print('Scanning data with Polars (lazy)...')
    scan = pl.scan_parquet(args.data)

    # Distinct MPIDs to size the firm lookup. Projection pushdown means this
    # collect only reads the `mpid` column off disk, not the whole frame.
    mpids = scan.select('mpid').unique().collect().get_column('mpid').to_list()
    print(f'OK Scanned {len(mpids)} distinct MPIDs\n')

    # Small firm lookup joined lazily; the join + hour derivation stay in the
    # lazy plan so every table below benefits from column/row pushdown.
    firm_map = pl.LazyFrame({
        'mpid': mpids,
        'firm_name': [get_firm_name(m) for m in mpids],
        'firm_category': [get_firm_category(get_firm_name(m)) for m in mpids],
    })
    base = (
        scan.join(firm_map, on='mpid', how='left')
        .with_columns(
            pl.from_epoch(pl.col('es_trade_time_ns'), time_unit='ns').dt.hour().alias('hour')
        )
    )
    schema_names = base.collect_schema().names()

    # ------------------------------------------------------------------
    # 1. Overall Statistics (Table 1) -- population std (ddof=0) like np.std
    # ------------------------------------------------------------------
    print('=' * 80)
    print('TABLE 1: OVERALL LATENCY STATISTICS')
    print('=' * 80)
    overall = base.select(
        pl.len().alias('N observations'),
        pl.col('latency_ms').mean().alias('Mean (ms)'),
        pl.col('latency_ms').median().alias('Median (ms)'),
        *[pl.col('latency_ms').quantile(p / 100, interpolation=Q).alias(f'p{p} (ms)')
          for p in (10, 25, 75, 90, 95, 99)],
        pl.col('latency_ms').std(ddof=0).alias('Std Dev (ms)'),
        pl.col('latency_ms').min().alias('Min (ms)'),
        pl.col('latency_ms').max().alias('Max (ms)'),
    ).collect()
    row = overall.row(0, named=True)
    for key, val in row.items():
        if key == 'N observations':
            print(f'{key:20s}: {val:,}')
        else:
            print(f'{key:20s}: {val:,.3f}')

    # ------------------------------------------------------------------
    # 2. Top MPIDs (Table 2)
    # ------------------------------------------------------------------
    print('\n' + '=' * 80)
    print('TABLE 2: TOP 15 MPIDS')
    print('=' * 80)
    mpid_stats = (
        base.group_by('mpid')
        .agg(_agg_exprs(percentiles=(10, 90), std=True))
        .select('mpid', 'N obs', 'Median (ms)', 'Mean (ms)', 'p10 (ms)', 'p90 (ms)', 'Std Dev (ms)')
        .sort('N obs', descending=True)
        .head(15)
        .collect()
    )
    _print(mpid_stats)

    # ------------------------------------------------------------------
    # 3. Hour of Day (Table 3)
    # ------------------------------------------------------------------
    print('\n' + '=' * 80)
    print('TABLE 3: LATENCY BY HOUR OF DAY')
    print('=' * 80)
    hourly = (
        base.group_by('hour')
        .agg(_agg_exprs(percentiles=(25, 75)))
        .select('hour', 'N obs', 'Median (ms)', 'Mean (ms)', 'p25 (ms)', 'p75 (ms)')
        .sort('hour')
        .collect()
    )
    _print(hourly)

    # ------------------------------------------------------------------
    # 4. Symbols (Table 4)
    # ------------------------------------------------------------------
    print('\n' + '=' * 80)
    print('TABLE 4: LATENCY BY SYMBOL')
    print('=' * 80)
    symbol_stats = (
        base.group_by('symbol')
        .agg(_agg_exprs(percentiles=(10, 90)))
        .select('symbol', 'N obs', 'Median (ms)', 'Mean (ms)', 'p10 (ms)', 'p90 (ms)')
        .sort('Median (ms)')
        .collect()
    )
    _print(symbol_stats)

    # ------------------------------------------------------------------
    # 5. Event Types (Table 5)
    # ------------------------------------------------------------------
    print('\n' + '=' * 80)
    print('TABLE 5: LATENCY BY EVENT TYPE')
    print('=' * 80)
    event_stats = (
        base.group_by('event_type')
        .agg(_agg_exprs(percentiles=(10, 90)))
        .select('event_type', 'N obs', 'Median (ms)', 'Mean (ms)', 'p10 (ms)', 'p90 (ms)')
        .collect()
    )
    _print(event_stats)

    # ------------------------------------------------------------------
    # 6. Firm Categories
    # ------------------------------------------------------------------
    print('\n' + '=' * 80)
    print('FIRM CATEGORIES')
    print('=' * 80)
    category_stats = (
        base.group_by('firm_category')
        .agg(_agg_exprs())
        .select('firm_category', 'N obs', 'Median (ms)', 'Mean (ms)')
        .collect()
    )
    _print(category_stats)

    # ------------------------------------------------------------------
    # 7. Contracts
    # ------------------------------------------------------------------
    if 'contract' in schema_names:
        print('\n' + '=' * 80)
        print('CONTRACTS')
        print('=' * 80)
        contract_stats = (
            base.group_by('contract')
            .agg(_agg_exprs())
            .select('contract', 'N obs', 'Median (ms)', 'Mean (ms)')
            .collect()
        )
        _print(contract_stats)

    # ------------------------------------------------------------------
    # 8. Top Firms with Names
    # ------------------------------------------------------------------
    print('\n' + '=' * 80)
    print('TOP 15 FIRMS (WITH NAMES)')
    print('=' * 80)
    firm_stats = (
        base.group_by('mpid', 'firm_name')
        .agg(_agg_exprs())
        .select('mpid', 'firm_name', 'N obs', 'Median (ms)', 'Mean (ms)')
        .sort('N obs', descending=True)
        .head(15)
        .collect()
    )
    _print(firm_stats)

    print('\nOK Statistics extraction complete!')


if __name__ == '__main__':
    main()
