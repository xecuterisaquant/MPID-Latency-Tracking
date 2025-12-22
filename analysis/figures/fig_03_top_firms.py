"""
Figure 03: Top Firms Comparison
Detailed breakdown of top 12 firms by volume
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from config import FIGURES_DIR, FIGURE_DPI, FIGURE_WIDTH, FIGURE_HEIGHT, TOP_N_FIRMS
from analysis.utils.plotting import setup_figure, save_figure, smart_sample
from mpid_lookup.mpid_to_firm import get_firm_name, get_firm_category

def generate_figure_03(df: pd.DataFrame, output_dir: Path = FIGURES_DIR, top_n: int = TOP_N_FIRMS) -> None:
    """
    Generate top firms comparison plot
    """
    print(f"📊 Generating Figure 03: Top {top_n} Firms Comparison...")
    
    # Add firm name column
    if 'firm_name' not in df.columns:
        df['firm_name'] = df['mpid'].apply(get_firm_name)
    if 'firm_category' not in df.columns:
        df['firm_category'] = df['mpid'].apply(get_firm_category)
    
    # Get top N firms
    top_firms = df['firm_name'].value_counts().head(top_n).index
    plot_df = df[df['firm_name'].isin(top_firms)].copy()
    
    # Sample for performance
    plot_df = smart_sample(plot_df, max_size=500_000, stratify_col='firm_name')
    
    # Sort by median latency
    firm_order = plot_df.groupby('firm_name')['latency_ms'].median().sort_values().index.tolist()
    
    # Create figure
    fig, ax = setup_figure(figsize=(FIGURE_WIDTH * 1.2, FIGURE_HEIGHT * 1.5))
    
    # Boxplot (faster than violin for large data)
    sns.boxplot(data=plot_df, y='firm_name', x='latency_ms', order=firm_order,
                hue='firm_category', dodge=False, ax=ax, showfliers=False,
                palette={'Active Fast Market Maker': '#2ecc71',
                        'Sporadic/Slow HFT': '#e74c3c',
                        'Traditional Broker': '#3498db',
                        'Other': '#95a5a6'})
    
    ax.set_xlabel('Latency (ms)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Firm', fontsize=13, fontweight='bold')
    ax.set_title(f'Top {top_n} Firms by Trading Volume (n = {len(df):,})', 
                 fontsize=15, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, axis='x')
    ax.legend(title='Category', loc='lower right', fontsize=9)
    
    # Add count annotations
    for i, firm in enumerate(firm_order):
        count = len(df[df['firm_name'] == firm])
        median = df[df['firm_name'] == firm]['latency_ms'].median()
        ax.text(ax.get_xlim()[1] * 0.95, i, f'n={count:,}\nMed={median:.1f}ms',
                verticalalignment='center', horizontalalignment='right',
                fontsize=8, bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
    
    output_path = output_dir / 'fig_03_top_firms.png'
    save_figure(fig, output_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='Path to latencies.parquet')
    parser.add_argument('--output', default=str(FIGURES_DIR), help='Output directory')
    parser.add_argument('--top-n', type=int, default=TOP_N_FIRMS, help='Number of top firms')
    args = parser.parse_args()
    
    df = pd.read_parquet(args.data)
    generate_figure_03(df, Path(args.output), args.top_n)
