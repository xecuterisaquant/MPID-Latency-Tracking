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
    
    # Determine timestamp column name
    timestamp_col = 'nasdaq_time_ns' if 'nasdaq_time_ns' in df.columns else 'nasdaq_timestamp'
    
    # Create hour column in ET (convert from UTC, data is in UTC)
    # UTC to ET: subtract 4 hours (EDT) or 5 hours (EST)
    # March 2025 is EDT (daylight saving), so UTC-4
    nasdaq_dt = pd.to_datetime(df[timestamp_col], unit='ns')
    hour_et = (nasdaq_dt.dt.hour - 4) % 24
    
    # Filter to regular trading hours only (9:30-16:00 ET = hours 9-16)
    trading_mask = hour_et.between(9, 16)
    
    # Create temporary dataframe with just what we need to avoid memory issues
    temp_df = pd.DataFrame({
        'hour': hour_et[trading_mask],
        'latency_ms': df.loc[trading_mask, 'latency_ms'].values
    })
    
    # Create figure with dual y-axis
    fig, ax1 = plt.subplots(figsize=(FIGURE_WIDTH * 1.5, FIGURE_HEIGHT), dpi=FIGURE_DPI)
    
    # Median latency by hour
    hourly_latency = temp_df.groupby('hour')['latency_ms'].median()
    
    ax1.plot(hourly_latency.index, hourly_latency.values, 
             marker='o', linewidth=2.5, markersize=8, color='#3498db', label='Median Latency')
    ax1.set_xlabel('Hour of Day (ET)', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Median Latency (ms)', fontsize=13, fontweight='bold', color='#3498db')
    ax1.tick_params(axis='y', labelcolor='#3498db')
    ax1.grid(True, alpha=0.3)
    
    # Volume on secondary axis
    ax2 = ax1.twinx()
    hourly_volume = temp_df.groupby('hour').size()
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
    
    # Set hour range to regular trading hours (9:30-16:00 ET)
    ax1.set_xlim(9, 16)
    ax1.set_xticks(range(9, 17))
    # Add custom labels to show actual times
    ax1.set_xticklabels(['9 AM', '10 AM', '11 AM', '12 PM', '1 PM', '2 PM', '3 PM', '4 PM'])
    
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
