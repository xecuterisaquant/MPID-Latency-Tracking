"""
Figure 04: Symbol-Level Analysis
Latency variation across different equity symbols
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from config import FIGURES_DIR, FIGURE_DPI, FIGURE_WIDTH, FIGURE_HEIGHT
from analysis.utils.plotting import setup_figure, save_figure, smart_sample

def generate_figure_04(df: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> None:
    """
    Generate symbol-level latency comparison
    """
    print("📊 Generating Figure 04: Symbol-Level Analysis...")
    
    # Sample for performance
    plot_df = smart_sample(df, max_size=500_000, stratify_col='symbol')
    
    # Sort symbols by median latency
    symbol_order = plot_df.groupby('symbol')['latency_ms'].median().sort_values().index.tolist()
    
    # Create figure
    fig, ax = setup_figure(figsize=(FIGURE_WIDTH * 1.3, FIGURE_HEIGHT))
    
    # Boxplot
    sns.boxplot(data=plot_df, x='symbol', y='latency_ms', order=symbol_order,
                palette='Set2', ax=ax, showfliers=False)
    
    ax.set_xlabel('Symbol', fontsize=13, fontweight='bold')
    ax.set_ylabel('Latency (ms)', fontsize=13, fontweight='bold')
    ax.set_title(f'Latency by Symbol (n = {len(df):,})', 
                 fontsize=15, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add median + count annotations
    for i, symbol in enumerate(symbol_order):
        symbol_data = df[df['symbol'] == symbol]['latency_ms']
        median_val = symbol_data.median()
        count = len(symbol_data)
        
        # Place annotation above box
        ax.text(i, median_val * 1.5, f'{median_val:.1f}ms\nn={count:,}',
                ha='center', va='bottom', fontsize=8,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Rotate x-axis labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    
    output_path = output_dir / 'fig_04_symbols.png'
    save_figure(fig, output_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='Path to latencies.parquet')
    parser.add_argument('--output', default=str(FIGURES_DIR), help='Output directory')
    args = parser.parse_args()
    
    df = pd.read_parquet(args.data)
    generate_figure_04(df, Path(args.output))
