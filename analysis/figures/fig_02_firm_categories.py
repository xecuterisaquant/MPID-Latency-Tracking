"""
Figure 02: Firm Category Analysis  
Comparison of Active Fast MMs vs Other participants
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

def categorize_firm_by_type(mpid):
    """Categorize firms by business type to highlight diversity of top participants"""
    
    # Investment Banks
    if mpid in ['JPMS', 'GSCO', 'UBSS']:
        return 'Investment Banks'
    
    # Wealth Managers / Retail Brokers
    elif mpid in ['WBPX', 'WBSI']:
        return 'Wealth Managers'
    
    # Pure HFT / Market Makers
    elif mpid in ['WCHV', 'VIRT', 'CDRG', 'IMCC', 'SGAS']:
        return 'HFT / Market Makers'
    
    # Trading Firms
    elif mpid in ['FLTU', 'XGWD', 'ETMM']:
        return 'Proprietary Trading'
    
    # Everything else
    else:
        return 'Other'

def generate_figure_02(df: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> None:
    """
    Generate firm category comparison by business type
    Shows diversity of top participants: Investment Banks, Wealth Managers, HFT firms
    """
    print("📊 Generating Figure 02: Firm Category Analysis...")
    
    # Create category based on firm business type
    firm_category = df['mpid'].apply(categorize_firm_by_type)
    
    # Sample for plotting (balanced across categories)
    plot_data = []
    for category in firm_category.unique():
        cat_mask = firm_category == category
        n_samples = min(100000, cat_mask.sum())
        cat_indices = df.index[cat_mask].to_series().sample(n=n_samples, random_state=42)
        plot_data.append(df.loc[cat_indices].assign(firm_category=category))
    
    plot_df = pd.concat(plot_data, ignore_index=True)
    
    # Create figure
    fig, ax = setup_figure(figsize=(FIGURE_WIDTH * 1.5, FIGURE_HEIGHT))
    
    # Sort categories by median latency
    category_order = plot_df.groupby('firm_category')['latency_ms'].median().sort_values().index.tolist()
    
    # Use seaborn violin plot for cleaner visualization
    sns.violinplot(data=plot_df, x='firm_category', y='latency_ms', order=category_order,
                   palette='Set2', ax=ax, inner='box', cut=0)
    
    # Add median points
    medians = plot_df.groupby('firm_category')['latency_ms'].median().reindex(category_order)
    ax.scatter(range(len(category_order)), medians.values, color='red', s=100, zorder=3, 
               label='Median', marker='D')
    
    # Labels and formatting
    ax.set_xlabel('Firm Type', fontsize=13, fontweight='bold')
    ax.set_ylabel('Latency (ms)', fontsize=13, fontweight='bold')
    ax.set_title(f'Latency by Firm Category (n = {len(df):,})', 
                 fontsize=15, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(loc='upper right')
    
    # Rotate x labels for readability
    ax.set_xticklabels(ax.get_xticklabels(), rotation=15, ha='right')
    
    # Add summary statistics annotation
    stats_text = "Top 3 Firms:\n"
    stats_text += "• JPMS (Investment Bank)\n"
    stats_text += "• WBPX (Wealth Manager)\n"
    stats_text += "• WCHV (HFT Market Maker)\n\n"
    for category in category_order:
        cat_data = plot_df[plot_df['firm_category'] == category]['latency_ms']
        stats_text += f"{category}:\n  Med={cat_data.median():.1f}ms\n"
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
            verticalalignment='top', horizontalalignment='left',
            fontsize=9, family='monospace')
    
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
            verticalalignment='top', horizontalalignment='right',
            fontsize=9, family='monospace')
    
    output_path = output_dir / 'fig_02_firm_categories.png'
    save_figure(fig, output_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='Path to latencies.parquet')
    parser.add_argument('--output', default=str(FIGURES_DIR), help='Output directory')
    args = parser.parse_args()
    
    df = pd.read_parquet(args.data)
    generate_figure_02(df, Path(args.output))
