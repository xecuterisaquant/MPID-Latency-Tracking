"""
Figure 05: Time-of-Day Patterns
Hourly latency variation and trading volume
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

def generate_figure_05(df: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> None:
    """
    Generate time-of-day latency and volume analysis
    """
    print("📊 Generating Figure 05: Time-of-Day Patterns...")
    
    # Create hour column if not present
    if 'hour' not in df.columns:
        df['hour'] = pd.to_datetime(df['nasdaq_time_ns'], unit='ns').dt.hour
    
    # Create figure with dual y-axis
    fig, ax1 = plt.subplots(figsize=(FIGURE_WIDTH * 1.5, FIGURE_HEIGHT), dpi=FIGURE_DPI)
    
    # Median latency by hour
    hourly_latency = df.groupby('hour')['latency_ms'].median()
    
    ax1.plot(hourly_latency.index, hourly_latency.values, 
             marker='o', linewidth=2.5, markersize=8, color='#3498db', label='Median Latency')
    ax1.set_xlabel('Hour of Day (ET)', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Median Latency (ms)', fontsize=13, fontweight='bold', color='#3498db')
    ax1.tick_params(axis='y', labelcolor='#3498db')
    ax1.grid(True, alpha=0.3)
    
    # Volume on secondary axis
    ax2 = ax1.twinx()
    hourly_volume = df.groupby('hour').size()
    ax2.bar(hourly_volume.index, hourly_volume.values, alpha=0.3, color='#e74c3c', label='Volume')
    ax2.set_ylabel('Number of Observations', fontsize=13, fontweight='bold', color='#e74c3c')
    ax2.tick_params(axis='y', labelcolor='#e74c3c')
    
    # Title
    fig.suptitle(f'Latency and Trading Volume by Hour (n = {len(df):,})',
                 fontsize=15, fontweight='bold', y=0.98)
    
    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=11)
    
    # Set hour range to trading hours
    ax1.set_xlim(6, 17)
    ax1.set_xticks(range(6, 18))
    
    output_path = output_dir / 'fig_05_time_of_day.png'
    save_figure(fig, output_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='Path to latencies.parquet')
    parser.add_argument('--output', default=str(FIGURES_DIR), help='Output directory')
    args = parser.parse_args()
    
    df = pd.read_parquet(args.data)
    generate_figure_05(df, Path(args.output))
