"""
Figure 09: Contract Comparison (March vs June ES)
Side-by-side comparison of March and June contract latencies
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

def generate_figure_09(df: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> None:
    """
    Generate contract comparison (March vs June)
    """
    print("📊 Generating Figure 09: Contract Comparison (March vs June)...")
    
    # Check if contract column exists
    if 'contract' not in df.columns:
        print("⚠️  Contract column not found - skipping Figure 09")
        return
    
    # Use full dataset (no sampling)
    print("  Using full dataset for contract comparison (no sampling)...")
    plot_df = df.copy()
    
    # Create figure with multiple panels
    fig, axes = plt.subplots(2, 2, figsize=(FIGURE_WIDTH * 2, FIGURE_HEIGHT * 2), dpi=FIGURE_DPI)
    
    # Panel 1: Distribution comparison
    ax1 = axes[0, 0]
    for contract in plot_df['contract'].unique():
        contract_data = plot_df[plot_df['contract'] == contract]['latency_ms']
        ax1.hist(contract_data, bins=50, alpha=0.6, label=contract, edgecolor='black', linewidth=0.5)
    ax1.set_xlabel('Latency (ms)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Count', fontsize=11, fontweight='bold')
    ax1.set_title('Distribution Comparison', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Boxplot comparison
    ax2 = axes[0, 1]
    sns.boxplot(data=plot_df, x='contract', y='latency_ms', palette='Set2', ax=ax2, showfliers=False)
    ax2.set_xlabel('Contract', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Latency (ms)', fontsize=11, fontweight='bold')
    ax2.set_title('Box Plot Comparison', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Panel 3: Over-time comparison
    ax3 = axes[1, 0]
    plot_df['date'] = pd.to_datetime(plot_df['nasdaq_time_ns'], unit='ns').dt.date
    daily_median = plot_df.groupby(['date', 'contract'])['latency_ms'].median().reset_index()
    for contract in daily_median['contract'].unique():
        contract_series = daily_median[daily_median['contract'] == contract]
        ax3.plot(contract_series['date'], contract_series['latency_ms'], 
                marker='o', label=contract, linewidth=2)
    ax3.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Median Latency (ms)', fontsize=11, fontweight='bold')
    ax3.set_title('Daily Median Latency Trend', fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    plt.setp(ax3.get_xticklabels(), rotation=45, ha='right')
    
    # Panel 4: Volume comparison
    ax4 = axes[1, 1]
    volume_data = plot_df['contract'].value_counts()
    ax4.bar(volume_data.index, volume_data.values, color=['#3498db', '#e74c3c'])
    ax4.set_xlabel('Contract', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Number of Observations', fontsize=11, fontweight='bold')
    ax4.set_title('Trading Volume by Contract', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for i, (idx, val) in enumerate(volume_data.items()):
        ax4.text(i, val, f'{val:,}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    fig.suptitle('ES Futures Contract Comparison: March vs June',
                 fontsize=16, fontweight='bold', y=0.995)
    
    output_path = output_dir / 'fig_09_contract_comparison.png'
    save_figure(fig, output_path, tight=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='Path to latencies.parquet')
    parser.add_argument('--output', default=str(FIGURES_DIR), help='Output directory')
    args = parser.parse_args()
    
    df = pd.read_parquet(args.data)
    generate_figure_09(df, Path(args.output))
