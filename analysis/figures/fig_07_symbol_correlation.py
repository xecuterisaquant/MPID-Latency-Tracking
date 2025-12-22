"""
Figure 07: Symbol/Asset Correlation Matrix
Cross-symbol co-movement in reaction latencies
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from config import FIGURES_DIR, FIGURE_DPI, FIGURE_WIDTH, FIGURE_HEIGHT
from analysis.utils.plotting import setup_figure, save_figure

def generate_figure_07(df: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> None:
    """
    Generate symbol correlation heatmap
    Uses all matching rows: aggregates by 5-minute bins across the full dataset
    """
    print("📊 Generating Figure 07: Symbol/Asset Correlation Matrix...")
    print(f"  Dataset size: {len(df):,} rows")
    
    # Use all data for correlation: bin times and aggregate median latency per symbol
    print("  Using all data for correlation analysis (no sampling)...")
    df_top = df.copy()
    print("  Creating time bins and aggregating median latency per symbol per bin...")
    df_top['time_bin'] = pd.to_datetime(df_top['nasdaq_time_ns'], unit='ns').dt.floor('5min')

    # Group (time_bin, symbol) and compute median latency, then pivot
    grouped = df_top.groupby(['time_bin', 'symbol'])['latency_ms'].median().reset_index()
    pivot_df = grouped.pivot(index='time_bin', columns='symbol', values='latency_ms')
    
    # Drop symbols with insufficient data
    pivot_df = pivot_df.dropna(thresh=int(len(pivot_df) * 0.3), axis=1)
    
    if pivot_df.shape[1] < 2:
        print("  ⚠️  Insufficient data - skipping")
        return
    
    # Spearman correlation
    print("  Computing correlations...")
    corr_matrix = pivot_df.corr(method='spearman')
    
    # Create figure
    fig, ax = setup_figure(figsize=(FIGURE_WIDTH * 1.2, FIGURE_HEIGHT * 1.2))
    
    # Heatmap
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', center=0.5,
                square=True, linewidths=0.5, cbar_kws={'label': 'Spearman ρ'},
                vmin=0, vmax=1, ax=ax)
    
    ax.set_title('Symbol Latency Correlation Matrix\nSpearman ρ of Median Latencies Across Time',
                 fontsize=15, fontweight='bold', pad=20)
    
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=11)
    plt.setp(ax.get_yticklabels(), rotation=0, fontsize=11)
    
    output_path = output_dir / 'fig_07_symbol_correlation.png'
    save_figure(fig, output_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='Path to latencies.parquet')
    parser.add_argument('--output', default=str(FIGURES_DIR), help='Output directory')
    args = parser.parse_args()
    
    df = pd.read_parquet(args.data)
    generate_figure_07(df, Path(args.output))
