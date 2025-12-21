"""
Generate comprehensive analytics and visualizations from latency results.

Creates:
1. Latency distribution histogram (log scale)
2. Per-MPID boxplots (top MPIDs by activity)
3. Time-of-day heatmap (hourly bins)
4. Per-symbol comparison charts
5. Summary statistics tables
6. Event type distribution
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
import argparse
from datetime import datetime
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from mpid_lookup.mpid_to_firm import get_firm_name, get_firm_category

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set style for publication-quality figures
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("Set2")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False


class LatencyAnalytics:
    """Generate comprehensive analytics from latency measurement data."""
    
    def __init__(self, results_path: str, output_dir: str):
        """
        Initialize analytics generator.
        
        Args:
            results_path: Path to latency results parquet file
            output_dir: Directory to save figures and tables
        """
        self.results_path = results_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.figures_dir = self.output_dir / "figures"
        self.tables_dir = self.output_dir / "tables"
        self.figures_dir.mkdir(exist_ok=True)
        self.tables_dir.mkdir(exist_ok=True)
        
        self.df = None
    
    def load_data(self):
        """Load latency results."""
        logger.info(f"Loading latency results from {self.results_path}")
        self.df = pd.read_parquet(self.results_path)
        logger.info(f"  Loaded {len(self.df):,} latency measurements")
        
        # Add firm name mapping
        self.df['firm'] = self.df['mpid'].apply(get_firm_name)
        self.df['firm_category'] = self.df['firm'].apply(get_firm_category)
        
        logger.info(f"  Date range: {self.df['date'].min()} to {self.df['date'].max()}")
        logger.info(f"  Unique MPIDs: {self.df['mpid'].nunique()}")
        logger.info(f"  Unique firms: {self.df['firm'].nunique()}")
        logger.info(f"  Unique symbols: {self.df['symbol'].nunique()}")
    
    def generate_latency_histogram(self):
        """Generate clean latency distribution histogram."""
        logger.info("\n📊 Generating latency distribution histogram...")
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Linear scale
        ax1 = axes[0]
        latency_ms = self.df['latency_ms']
        counts, bins, patches = ax1.hist(latency_ms, bins=80, edgecolor='white', 
                                         alpha=0.8, color='steelblue', linewidth=0.5)
        ax1.set_xlabel('Latency (milliseconds)', fontweight='bold')
        ax1.set_ylabel('Frequency', fontweight='bold')
        ax1.set_title('Latency Distribution (Linear Scale)', fontweight='bold')
        ax1.grid(True, alpha=0.25, linestyle='--')
        
        # Add percentile lines
        percentiles = [(50, 'green', 'Median'), (90, 'orange', 'p90'), 
                      (95, 'red', 'p95'), (99, 'darkred', 'p99')]
        for p, color, label in percentiles:
            val = np.percentile(latency_ms, p)
            ax1.axvline(val, color=color, linestyle='--', linewidth=2, alpha=0.7)
            ax1.text(val, ax1.get_ylim()[1] * 0.9, f'{label}\n{val:.1f}ms',
                    ha='center', fontsize=9, 
                    bbox=dict(boxstyle='round,pad=0.4', facecolor=color, alpha=0.2))
        
        # Log scale (microseconds)
        ax2 = axes[1]
        latency_us_nonzero = self.df[self.df['latency_us'] > 0]['latency_us']
        counts, bins, patches = ax2.hist(latency_us_nonzero, bins=80, edgecolor='white',
                                        alpha=0.8, color='coral', linewidth=0.5)
        ax2.set_xlabel('Latency (microseconds)', fontweight='bold')
        ax2.set_ylabel('Frequency', fontweight='bold')
        ax2.set_title('Latency Distribution (Log Scale)', fontweight='bold')
        ax2.set_xscale('log')
        ax2.grid(True, alpha=0.25, linestyle='--', which='both')
        
        # Add percentile lines on log scale
        for p, color, label in percentiles:
            val = np.percentile(latency_us_nonzero, p)
            ax2.axvline(val, color=color, linestyle='--', linewidth=2, alpha=0.7)
        
        plt.tight_layout()
        
        output_path = self.figures_dir / "latency_distribution.png"
        plt.savefig(output_path, bbox_inches='tight', facecolor='white', dpi=300)
        logger.info(f"  ✓ Saved to {output_path}")
        plt.close()
    
    def generate_mpid_boxplot(self, top_n: int = 12):
        """Generate clean boxplot comparing latencies across top firms."""
        logger.info(f"\n📊 Generating per-firm boxplot (top {top_n})...")
        
        # Get top firms by count
        top_firms = self.df['firm'].value_counts().head(top_n).index.tolist()
        
        # Filter data
        df_top = self.df[self.df['firm'].isin(top_firms)].copy()
        
        # Filter out extreme outliers for better visualization
        df_top = df_top[df_top['latency_us'] > 0].copy()
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Sort by median latency
        firm_order = (df_top.groupby('firm')['latency_us']
                      .median()
                      .sort_values()
                      .index.tolist())
        
        # Create boxplot with better styling
        bp = ax.boxplot(
            [df_top[df_top['firm'] == firm]['latency_us'].values for firm in firm_order],
            labels=firm_order,
            showfliers=False,
            patch_artist=True,
            widths=0.6,
            medianprops=dict(color='red', linewidth=2),
            boxprops=dict(facecolor='lightblue', edgecolor='navy', linewidth=1.5),
            whiskerprops=dict(color='navy', linewidth=1.5),
            capprops=dict(color='navy', linewidth=1.5)
        )
        
        ax.set_xlabel('Firm', fontweight='bold')
        ax.set_ylabel('Latency (microseconds)', fontweight='bold')
        ax.set_title(f'Market Maker Reaction Latency (Top {top_n} by Activity)', 
                    fontsize=14, pad=20)
        ax.set_yscale('log')
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')
        plt.xticks(rotation=45, ha='right')
        
        # Add subtle count labels below x-axis
        for i, firm in enumerate(firm_order, 1):
            count = (df_top['firm'] == firm).sum()
            median = df_top[df_top['firm'] == firm]['latency_us'].median()
            ax.text(i, ax.get_ylim()[0] * 0.8, 
                   f'n={count:,}\nmd={median:.0f}μs',
                   ha='center', va='top', fontsize=8, 
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='wheat', alpha=0.3))
        
        plt.tight_layout()
        
        output_path = self.figures_dir / "latency_by_firm.png"
        plt.savefig(output_path, bbox_inches='tight', facecolor='white')
        logger.info(f"  ✓ Saved to {output_path}")
        plt.close()
        plt.close()
    
    def generate_time_of_day_heatmap(self):
        """Generate heatmap showing latency patterns by time of day."""
        logger.info("\n📊 Generating time-of-day heatmap...")
        
        # Create hour bins and compute median latency
        df_copy = self.df.copy()
        df_copy['minute_bin'] = (df_copy['minute_of_hour'] // 10) * 10
        
        # Aggregate by hour and minute bin
        heatmap_data = (df_copy.groupby(['hour_of_day', 'minute_bin'])['latency_us']
                       .median()
                       .unstack(fill_value=np.nan))
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot heatmap (use log scale for better visualization)
        heatmap_data_log = np.log10(heatmap_data.clip(lower=1))
        sns.heatmap(heatmap_data_log, cmap='YlOrRd', ax=ax, 
                   cbar_kws={'label': 'Log₁₀(Median Latency μs)'})
        
        ax.set_xlabel('Minute of Hour')
        ax.set_ylabel('Hour of Day (Eastern Time)')
        ax.set_title('MPID Reaction Latency by Time of Day')
        
        # Mark market open and close
        market_open_idx = heatmap_data.index.get_loc(9) if 9 in heatmap_data.index else None
        market_close_idx = heatmap_data.index.get_loc(16) if 16 in heatmap_data.index else None
        
        if market_open_idx is not None:
            ax.axhline(market_open_idx + 0.5, color='green', linewidth=2, 
                      linestyle='--', label='Market Open (9:30 AM)')
        if market_close_idx is not None:
            ax.axhline(market_close_idx, color='red', linewidth=2,
                      linestyle='--', label='Market Close (4:00 PM)')
        
        if market_open_idx or market_close_idx:
            ax.legend(loc='upper right')
        
        plt.tight_layout()
        
        output_path = self.figures_dir / "latency_time_of_day.png"
        plt.savefig(output_path, bbox_inches='tight')
        logger.info(f"  ✓ Saved to {output_path}")
        plt.close()
    
    def generate_symbol_comparison(self):
        """Generate comparison charts across symbols."""
        logger.info("\n📊 Generating per-symbol comparison...")
        
        fig, axes = plt.subplots(2, 1, figsize=(12, 10))
        
        # Violin plot
        ax1 = axes[0]
        df_plot = self.df.copy()
        df_plot['latency_us_log'] = np.log10(df_plot['latency_us'].clip(lower=1))
        
        symbol_order = (self.df.groupby('symbol')['latency_us']
                       .median()
                       .sort_values()
                       .index.tolist())
        
        sns.violinplot(data=df_plot, x='symbol', y='latency_us_log',
                      order=symbol_order, ax=ax1, inner='quartile')
        
        ax1.set_xlabel('Symbol')
        ax1.set_ylabel('Log₁₀(Latency in microseconds)')
        ax1.set_title('Latency Distribution by Symbol')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Bar chart of counts
        ax2 = axes[1]
        symbol_counts = self.df['symbol'].value_counts().loc[symbol_order]
        symbol_counts.plot(kind='bar', ax=ax2, color='steelblue', edgecolor='black')
        
        ax2.set_xlabel('Symbol')
        ax2.set_ylabel('Number of Latency Measurements')
        ax2.set_title('MPID Activity by Symbol')
        ax2.grid(True, alpha=0.3, axis='y')
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add value labels
        for i, v in enumerate(symbol_counts):
            ax2.text(i, v, f'{v:,}', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        
        output_path = self.figures_dir / "latency_by_symbol.png"
        plt.savefig(output_path, bbox_inches='tight')
        logger.info(f"  ✓ Saved to {output_path}")
        plt.close()
    
    def generate_event_type_distribution(self):
        """Generate event type distribution chart."""
        logger.info("\n📊 Generating event type distribution...")
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Pie chart
        ax1 = axes[0]
        event_counts = self.df['event_type'].value_counts()
        ax1.pie(event_counts, labels=event_counts.index, autopct='%1.1f%%',
               startangle=90)
        ax1.set_title('Distribution of Event Types')
        
        # Bar chart with latency comparison
        ax2 = axes[1]
        event_latencies = self.df.groupby('event_type')['latency_us'].median().sort_values()
        event_latencies.plot(kind='barh', ax=ax2, color='coral', edgecolor='black')
        
        ax2.set_xlabel('Median Latency (microseconds)')
        ax2.set_ylabel('Event Type')
        ax2.set_title('Median Latency by Event Type')
        ax2.grid(True, alpha=0.3, axis='x')
        
        # Add value labels
        for i, v in enumerate(event_latencies):
            ax2.text(v, i, f'  {v:.0f}μs', va='center', fontsize=9)
        
        plt.tight_layout()
        
        output_path = self.figures_dir / "event_type_analysis.png"
        plt.savefig(output_path, bbox_inches='tight')
        logger.info(f"  ✓ Saved to {output_path}")
        plt.close()
    
    def generate_summary_tables(self):
        """Generate comprehensive summary statistics tables."""
        logger.info("\n📊 Generating summary tables...")
        
        # Overall statistics table
        stats = self.df['latency_us'].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
        stats_df = pd.DataFrame({
            'Statistic': stats.index,
            'Value (μs)': stats.values
        })
        stats_path = self.tables_dir / "overall_statistics.csv"
        stats_df.to_csv(stats_path, index=False)
        logger.info(f"  ✓ Saved overall statistics to {stats_path}")
        
        # Per-MPID summary
        mpid_stats = self.df.groupby('mpid')['latency_us'].agg([
            ('Count', 'count'),
            ('Mean_μs', 'mean'),
            ('Median_μs', 'median'),
            ('Std_μs', 'std'),
            ('P10_μs', lambda x: np.percentile(x, 10)),
            ('P90_μs', lambda x: np.percentile(x, 90)),
            ('P95_μs', lambda x: np.percentile(x, 95)),
            ('P99_μs', lambda x: np.percentile(x, 99))
        ]).round(2)
        mpid_stats = mpid_stats.sort_values('Count', ascending=False)
        mpid_path = self.tables_dir / "mpid_statistics.csv"
        mpid_stats.to_csv(mpid_path)
        logger.info(f"  ✓ Saved per-MPID statistics to {mpid_path}")
        
        # Per-symbol summary
        symbol_stats = self.df.groupby('symbol')['latency_us'].agg([
            ('Count', 'count'),
            ('Mean_μs', 'mean'),
            ('Median_μs', 'median'),
            ('P95_μs', lambda x: np.percentile(x, 95))
        ]).round(2)
        symbol_stats = symbol_stats.sort_values('Median_μs')
        symbol_path = self.tables_dir / "symbol_statistics.csv"
        symbol_stats.to_csv(symbol_path)
        logger.info(f"  ✓ Saved per-symbol statistics to {symbol_path}")
        
        # Event type summary
        event_stats = self.df.groupby('event_type')['latency_us'].agg([
            ('Count', 'count'),
            ('Percentage', lambda x: len(x) / len(self.df) * 100),
            ('Median_μs', 'median')
        ]).round(2)
        event_stats = event_stats.sort_values('Count', ascending=False)
        event_path = self.tables_dir / "event_type_statistics.csv"
        event_stats.to_csv(event_path)
        logger.info(f"  ✓ Saved event type statistics to {event_path}")
    
    def generate_all(self):
        """Generate all analytics and visualizations."""
        logger.info("=" * 80)
        logger.info("LATENCY ANALYTICS GENERATION")
        logger.info("=" * 80)
        
        self.load_data()
        
        logger.info("\n" + "=" * 80)
        logger.info("GENERATING VISUALIZATIONS")
        logger.info("=" * 80)
        
        self.generate_latency_histogram()
        self.generate_mpid_boxplot()
        self.generate_time_of_day_heatmap()
        self.generate_symbol_comparison()
        self.generate_event_type_distribution()
        
        logger.info("\n" + "=" * 80)
        logger.info("GENERATING SUMMARY TABLES")
        logger.info("=" * 80)
        
        self.generate_summary_tables()
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ ANALYTICS GENERATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"\n📁 Output directory: {self.output_dir}")
        logger.info(f"   Figures: {self.figures_dir}")
        logger.info(f"   Tables: {self.tables_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate latency analytics")
    parser.add_argument("--results", required=True, help="Path to latency results parquet")
    parser.add_argument("--output", required=True, help="Output directory for analytics")
    
    args = parser.parse_args()
    
    analytics = LatencyAnalytics(args.results, args.output)
    analytics.generate_all()
