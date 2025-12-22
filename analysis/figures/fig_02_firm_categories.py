"""
Figure 02: Firm Category Analysis
Comparison across Active Fast MMs, Sporadic/Slow HFT, Traditional Brokers, Other
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from config import FIGURES_DIR, FIGURE_DPI, FIGURE_WIDTH, FIGURE_HEIGHT, CATEGORY_COLORS
from analysis.utils.plotting import setup_figure, save_figure, smart_sample
from mpid_lookup.mpid_to_firm import get_firm_category

def generate_figure_02(df: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> None:
    """
    Generate firm category comparison with boxplots and overlays
    """
    print("📊 Generating Figure 02: Firm Category Analysis...")
    
    # Add firm category column if not present
    if 'firm_category' not in df.columns:
        df['firm_category'] = df['mpid'].apply(get_firm_category)
    
    # Sample for plotting performance
    plot_df = smart_sample(df, max_size=500_000, stratify_col='firm_category')
    
    # Create figure
    fig, ax = setup_figure(figsize=(FIGURE_WIDTH * 1.5, FIGURE_HEIGHT))
    
    # Category order by median latency
    category_order = plot_df.groupby('firm_category')['latency_ms'].median().sort_values().index.tolist()
    
    # Boxplot
    sns.boxplot(data=plot_df, x='latency_ms', y='firm_category', order=category_order,
                palette=CATEGORY_COLORS, ax=ax, showfliers=False)
    
    # Add KDE overlays
    for i, category in enumerate(category_order):
        cat_data = plot_df[plot_df['firm_category'] == category]['latency_ms']
        # Clip extreme values for cleaner KDE
        cat_data_clipped = cat_data[cat_data <= cat_data.quantile(0.99)]
        
        # Create KDE
        from scipy.stats import gaussian_kde
        if len(cat_data_clipped) > 100:
            kde = gaussian_kde(cat_data_clipped)
            x_range = np.linspace(cat_data_clipped.min(), cat_data_clipped.max(), 200)
            kde_values = kde(x_range)
            
            # Normalize and shift for overlay
            kde_normalized = kde_values / kde_values.max() * 0.4  # Scale to 40% of box height
            ax.fill_betweenx(i + kde_normalized, x_range, alpha=0.3, 
                            color=CATEGORY_COLORS.get(category, '#95a5a6'))
    
    ax.set_xlabel('Latency (ms)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Firm Category', fontsize=13, fontweight='bold')
    ax.set_title('Latency by Firm Category (n = {:,})'.format(len(df)), 
                 fontsize=15, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, axis='x')
    
    # Add summary stats annotation
    stats_text = ""
    for category in category_order:
        cat_data = df[df['firm_category'] == category]['latency_ms']
        stats_text += f"{category}:\n  Med={cat_data.median():.1f}ms, n={len(cat_data):,}\n"
    
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7),
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
