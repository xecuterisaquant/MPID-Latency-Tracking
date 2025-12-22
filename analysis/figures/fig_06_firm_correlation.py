"""
Figure 06: Firm Correlation Matrix
Spearman correlation of reaction latencies across firms
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from config import FIGURES_DIR, FIGURE_DPI, FIGURE_WIDTH, FIGURE_HEIGHT, TOP_N_FIRMS
from analysis.utils.plotting import setup_figure, save_figure
from analysis.utils.stats import correlation_matrix
from mpid_lookup.mpid_to_firm import get_firm_name

def generate_figure_06(df: pd.DataFrame, output_dir: Path = FIGURES_DIR, top_n: int = TOP_N_FIRMS) -> None:
    """
    Generate firm correlation heatmap
    Uses all matching rows: aggregates by 5-minute bins across the full dataset
    """
    print(f"📊 Generating Figure 06: Firm Correlation Matrix (Top {top_n})...")
    print(f"  Dataset size: {len(df):,} rows")
    
    # Add firm name
    if 'firm_name' not in df.columns:
        print("  Adding firm names...")
        df['firm_name'] = df['mpid'].apply(get_firm_name)
    
    # Get top firms
    top_firms = df['firm_name'].value_counts().head(top_n).index.tolist()
    print(f"  Top {top_n} firms: {', '.join(top_firms[:3])}...")
    
    # Use all data for correlation: filter to top firms, bin times, then aggregate
    print("  Using all data for correlation analysis (no sampling)...")
    df_top = df[df['firm_name'].isin(top_firms)].copy()
    print("  Creating time bins and aggregating median latency per firm per bin...")
    df_top['time_bin'] = pd.to_datetime(df_top['nasdaq_time_ns'], unit='ns').dt.floor('5min')

    # Group (time_bin, firm) and compute median latency, then pivot
    grouped = df_top.groupby(['time_bin', 'firm_name'])['latency_ms'].median().reset_index()
    pivot_df = grouped.pivot(index='time_bin', columns='firm_name', values='latency_ms')
    
    # Drop columns with too many NaNs (need at least 30% coverage)
    min_coverage = 0.3
    pivot_df = pivot_df.dropna(thresh=int(len(pivot_df) * min_coverage), axis=1)
    
    if pivot_df.shape[1] < 2:
        print("  ⚠️  Insufficient data for correlation - skipping")
        return
    
    # Calculate Spearman correlation
    print("  Computing correlations...")
    corr_matrix = pivot_df.corr(method='spearman')
    
    # Create figure
    fig, ax = setup_figure(figsize=(FIGURE_WIDTH * 1.3, FIGURE_HEIGHT * 1.3))
    
    # Heatmap
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='RdYlGn', center=0.5,
                square=True, linewidths=0.5, cbar_kws={'label': 'Spearman ρ'},
                vmin=0, vmax=1, ax=ax)
    
    ax.set_title(f'Firm Latency Correlation Matrix (Top {top_n} Firms)\nSpearman ρ of Median Latencies',
                 fontsize=15, fontweight='bold', pad=20)
    
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=9)
    plt.setp(ax.get_yticklabels(), rotation=0, fontsize=9)
    
    output_path = output_dir / 'fig_06_firm_correlation.png'
    save_figure(fig, output_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='Path to latencies.parquet')
    parser.add_argument('--output', default=str(FIGURES_DIR), help='Output directory')
    parser.add_argument('--top-n', type=int, default=TOP_N_FIRMS, help='Number of top firms')
    args = parser.parse_args()
    
    df = pd.read_parquet(args.data)
    generate_figure_06(df, Path(args.output), args.top_n)
