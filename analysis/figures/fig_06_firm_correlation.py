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
    """
    print(f"📊 Generating Figure 06: Firm Correlation Matrix (Top {top_n})...")
    
    # Add firm name
    if 'firm_name' not in df.columns:
        df['firm_name'] = df['mpid'].apply(get_firm_name)
    
    # Get top firms
    top_firms = df['firm_name'].value_counts().head(top_n).index.tolist()
    
    # Pivot to create firm x time matrix (using minute-level timestamps)
    df['minute'] = pd.to_datetime(df['nasdaq_time_ns'], unit='ns').dt.floor('1min')
    
    # Sample for performance (1 in every 10 minutes)
    sample_minutes = df['minute'].unique()[::10]
    df_sample = df[df['minute'].isin(sample_minutes)]
    
    # Pivot table: rows=minutes, columns=firms, values=median latency
    pivot_df = df_sample[df_sample['firm_name'].isin(top_firms)].pivot_table(
        index='minute',
        columns='firm_name',
        values='latency_ms',
        aggfunc='median'
    )
    
    # Calculate Spearman correlation
    corr_matrix = pivot_df.corr(method='spearman')
    
    # Create figure
    fig, ax = setup_figure(figsize=(FIGURE_WIDTH * 1.3, FIGURE_HEIGHT * 1.3))
    
    # Heatmap
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='RdYlGn', center=0,
                square=True, linewidths=0.5, cbar_kws={'label': 'Spearman ρ'},
                vmin=-1, vmax=1, ax=ax)
    
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
