"""
Figure 08: Weekly Trading Heatmap
Hour × Day-of-Week latency patterns
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

def generate_figure_08(df: pd.DataFrame, output_dir: Path = FIGURES_DIR) -> None:
    """
    Generate weekly trading heatmap (hour × day-of-week)
    OPTIMIZED: Fast aggregation with sampling
    """
    print("📊 Generating Figure 08: Weekly Trading Heatmap...")
    print(f"  Dataset size: {len(df):,} rows")
    
    # Use full dataset: aggregate median latency per hour/day without sampling
    print("  Using all data for heatmap (no sampling)...")
    df_top = df.copy()
    # Create datetime features
    print("  Extracting time features...")
    df_top['datetime'] = pd.to_datetime(df_top['nasdaq_time_ns'], unit='ns')
    df_top['hour'] = df_top['datetime'].dt.hour
    df_top['day_of_week'] = df_top['datetime'].dt.day_name()

    # Aggregate median latency per (hour, day_of_week) then pivot
    print("  Computing heatmap data (aggregating median latency per hour/day)...")
    grouped = df_top.groupby(['hour', 'day_of_week'])['latency_ms'].median().reset_index()
    heatmap_data = grouped.pivot(index='hour', columns='day_of_week', values='latency_ms')
    
    # Reorder days
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    heatmap_data = heatmap_data[[d for d in day_order if d in heatmap_data.columns]]
    
    # Create figure
    fig, ax = setup_figure(figsize=(FIGURE_WIDTH * 1.2, FIGURE_HEIGHT * 1.3))
    
    # Heatmap
    sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='YlOrRd',
                linewidths=0.5, cbar_kws={'label': 'Median Latency (ms)'},
                ax=ax)
    
    ax.set_xlabel('Day of Week', fontsize=13, fontweight='bold')
    ax.set_ylabel('Hour of Day (ET)', fontsize=13, fontweight='bold')
    ax.set_title('Weekly Trading Patterns: Median Latency by Hour and Day',
                 fontsize=15, fontweight='bold', pad=20)
    
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    
    output_path = output_dir / 'fig_08_weekly_heatmap.png'
    save_figure(fig, output_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='Path to latencies.parquet')
    parser.add_argument('--output', default=str(FIGURES_DIR), help='Output directory')
    args = parser.parse_args()
    
    df = pd.read_parquet(args.data)
    generate_figure_08(df, Path(args.output))
