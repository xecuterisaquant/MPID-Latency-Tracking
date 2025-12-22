"""
Figure 01: Overall Latency Distribution
Publication-quality distribution plot with log-scale companion
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import FIGURES_DIR, FIGURE_DPI, FIGURE_WIDTH, FIGURE_HEIGHT
from analysis.utils.plotting import setup_figure, save_figure, add_summary_stats_text

def generate_figure_01(df: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> None:
    """
    Generate overall latency distribution (linear + log scale)
    """
    print("📊 Generating Figure 01: Overall Latency Distribution...")
    
    # Create 2-panel figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(FIGURE_WIDTH * 2, FIGURE_HEIGHT), dpi=FIGURE_DPI)
    
    latency_ms = df['latency_ms'].values
    
    # Panel 1: Linear scale
    ax1.hist(latency_ms, bins=100, alpha=0.75, edgecolor='black', linewidth=0.5, color='#3498db')
    ax1.set_xlabel('Latency (ms)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Count', fontsize=12, fontweight='bold')
    ax1.set_title('Overall Latency Distribution (Linear Scale)', fontsize=14, fontweight='bold', pad=15)
    ax1.grid(True, alpha=0.3)
    add_summary_stats_text(ax1, latency_ms, x=0.97, y=0.97)
    
    # Panel 2: Log scale (proper log x-axis)
    ax2.hist(latency_ms + 1, bins=np.logspace(0, 4, 100), alpha=0.75, edgecolor='black', linewidth=0.5, color='#e74c3c')
    ax2.set_xscale('log')
    ax2.set_xlabel('Latency (ms, log scale)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Count', fontsize=12, fontweight='bold')
    ax2.set_title('Overall Latency Distribution (Log Scale)', fontsize=14, fontweight='bold', pad=15)
    ax2.grid(True, alpha=0.3, which='both')
    
    # Add median/mean lines
    median_val = np.median(latency_ms)
    mean_val = np.mean(latency_ms)
    ax2.axvline(median_val, color='green', linestyle='--', linewidth=2, label=f'Median: {median_val:.1f} ms')
    ax2.axvline(mean_val, color='orange', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.1f} ms')
    ax2.legend(fontsize=10)
    
    fig.suptitle(f'MPID Latency Distribution (n = {len(df):,})', 
                 fontsize=16, fontweight='bold', y=1.02)
    
    output_path = output_dir / 'fig_01_latency_distribution.png'
    save_figure(fig, output_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='Path to latencies.parquet')
    parser.add_argument('--output', default=str(FIGURES_DIR), help='Output directory')
    args = parser.parse_args()
    
    df = pd.read_parquet(args.data)
    generate_figure_01(df, Path(args.output))
