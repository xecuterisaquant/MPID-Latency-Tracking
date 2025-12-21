"""
Generate beautiful analytics visualizations using seaborn.
Cleaner, more professional styling for academic presentation.
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
from scipy import stats

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from mpid_lookup.mpid_to_firm import get_firm_name, get_firm_category

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set beautiful seaborn style
sns.set_theme(style="whitegrid", context="notebook", palette="deep")
plt.rc('font', family='sans-serif', size=11)
plt.rc('axes', labelsize=12, titlesize=13, titleweight='bold')


class LatencyAnalytics:
    """Generate comprehensive analytics with beautiful seaborn visualizations."""
    
    def __init__(self, results_path: str, output_dir: str):
        self.results_path = Path(results_path)
        self.output_dir = Path(output_dir)
        self.figures_dir = self.output_dir / "figures"
        self.tables_dir = self.output_dir / "tables"
        
        # Create output directories
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        self.tables_dir.mkdir(parents=True, exist_ok=True)
        
        self.df = None
    
    def load_data(self):
        """Load latency results and enrich with firm/category info."""
        logger.info(f"\n📂 Loading results from {self.results_path}")
        
        self.df = pd.read_parquet(self.results_path)
        logger.info(f"  Loaded {len(self.df):,} latency measurements")
        logger.info(f"  Unique MPIDs: {self.df['mpid'].nunique()}")
        logger.info(f"  Unique symbols: {self.df['symbol'].nunique()}")
        
        # Add firm and category info
        self.df['firm'] = self.df['mpid'].apply(get_firm_name)
        self.df['firm_category'] = self.df['firm'].apply(get_firm_category)
        logger.info(f"  Unique firms: {self.df['firm'].nunique()}")
    
    def generate_latency_histogram(self):
        """Beautiful histogram with KDE overlay."""
        logger.info("\n📊 Generating latency distribution...")
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
        
        # Linear scale with KDE
        ax = axes[0]
        sns.histplot(data=self.df, x='latency_us', bins=100, kde=True,
                    color='#3498db', edgecolor='white', linewidth=0.5, ax=ax, alpha=0.7)
        ax.set_xlabel('Latency (μs)', fontweight='bold')
        ax.set_ylabel('Count', fontweight='bold')
        ax.set_title('Latency Distribution', fontweight='bold', pad=15)
        
        # Add percentile markers
        percentiles = [10, 50, 90, 95, 99]
        colors = ['#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#34495e']
        for p, color in zip(percentiles, colors):
            val = np.percentile(self.df['latency_us'], p)
            if val < ax.get_xlim()[1]:
                ax.axvline(val, color=color, linestyle='--', alpha=0.7, linewidth=2.5)
        
        # Log scale with KDE
        ax = axes[1]
        log_data = np.log10(self.df['latency_us'])
        sns.histplot(x=log_data, bins=100, kde=True,
                    color='#e67e22', edgecolor='white', linewidth=0.5, ax=ax, alpha=0.7)
        ax.set_xlabel('log₁₀(Latency in μs)', fontweight='bold')
        ax.set_ylabel('Count', fontweight='bold')
        ax.set_title('Latency Distribution (Log Scale)', fontweight='bold', pad=15)
        
        # Add percentile annotations
        for p, color in zip(percentiles, colors):
            val = np.log10(np.percentile(self.df['latency_us'], p))
            if ax.get_xlim()[0] < val < ax.get_xlim()[1]:
                ax.axvline(val, color=color, linestyle='--', alpha=0.7, linewidth=2.5)
                ax.text(val, ax.get_ylim()[1] * 0.85, f'p{p}',
                       ha='center', va='top', fontsize=10, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                                edgecolor=color, linewidth=2, alpha=0.95))
        
        plt.tight_layout()
        output_path = self.figures_dir / "latency_distribution.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        logger.info(f"  ✓ Saved {output_path.name}")
        plt.close()
    
    def generate_firm_violin_plot(self, top_n: int = 12):
        """Beautiful violin plot with box overlay for firm comparison."""
        logger.info(f"\n📊 Generating firm comparison (top {top_n})...")
        
        top_firms = self.df['firm'].value_counts().head(top_n).index.tolist()
        df_top = self.df[self.df['firm'].isin(top_firms)].copy()
        
        # Sort by median
        firm_medians = df_top.groupby('firm')['latency_us'].median().sort_values()
        df_top['firm'] = pd.Categorical(df_top['firm'], categories=firm_medians.index, ordered=True)
        
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # Violin plot with inner box
        sns.violinplot(data=df_top, x='firm', y='latency_us',
                      palette='Set2', inner=None, ax=ax, alpha=0.6, linewidth=1.5)
        sns.boxplot(data=df_top, x='firm', y='latency_us',
                   width=0.25, boxprops=dict(alpha=0.9, linewidth=2.5),
                   whiskerprops=dict(linewidth=2),
                   capprops=dict(linewidth=2),
                   medianprops=dict(color='#c0392b', linewidth=4),
                   flierprops=dict(marker='o', markersize=2, alpha=0.15),
                   ax=ax)
        
        ax.set_yscale('log')
        ax.set_ylabel('Latency (μs, log scale)', fontweight='bold', fontsize=13)
        ax.set_xlabel('Firm', fontweight='bold', fontsize=13)
        ax.set_title(f'Latency Distribution by Firm (Top {top_n} by Activity)',
                    fontweight='bold', fontsize=15, pad=20)
        ax.grid(axis='y', alpha=0.25, which='both')
        plt.xticks(rotation=45, ha='right', fontsize=11)
        
        # Add annotations
        for i, firm in enumerate(firm_medians.index):
            count = len(df_top[df_top['firm'] == firm])
            median = df_top[df_top['firm'] == firm]['latency_us'].median()
            ax.text(i, ax.get_ylim()[0] * 1.8, f'{count:,}\n{median:.0f}μs',
                   ha='center', va='bottom', fontsize=9, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                            edgecolor='gray', linewidth=1.5, alpha=0.9))
        
        plt.tight_layout()
        output_path = self.figures_dir / "latency_by_firm.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        logger.info(f"  ✓ Saved {output_path.name}")
        plt.close()
    
    def generate_mpid_breakdown(self, top_n: int = 15):
        """MPID-level breakdown with category-based coloring."""
        logger.info(f"\n📊 Generating MPID breakdown (top {top_n})...")
        
        top_mpids = self.df['mpid'].value_counts().head(top_n).index.tolist()
        df_top = self.df[self.df['mpid'].isin(top_mpids)].copy()
        
        # Sort by median latency
        mpid_medians = df_top.groupby('mpid')['latency_us'].median().sort_values()
        df_top['mpid'] = pd.Categorical(df_top['mpid'], categories=mpid_medians.index, ordered=True)
        
        # Map MPIDs to categories for coloring
        mpid_to_category = df_top.groupby('mpid')['firm_category'].agg(
            lambda x: x.mode()[0] if len(x.mode()) > 0 else 'Other'
        ).to_dict()
        category_colors = {
            'Active Fast Market Maker': '#2ecc71', 
            'Sporadic/Slow HFT': '#e74c3c',
            'Traditional Broker': '#3498db', 
            'Other': '#95a5a6'
        }
        colors = [category_colors.get(mpid_to_category.get(mpid, 'Other'), '#95a5a6') 
                  for mpid in mpid_medians.index]
        
        fig, ax = plt.subplots(figsize=(16, 7))
        sns.boxplot(data=df_top, x='mpid', y='latency_us',
                   palette=colors, ax=ax, linewidth=1.5,
                   flierprops=dict(marker='o', markersize=1, alpha=0.1))
        ax.set_yscale('log')
        ax.set_ylabel('Latency (μs, log scale)', fontweight='bold', fontsize=13)
        ax.set_xlabel('MPID', fontweight='bold', fontsize=13)
        ax.set_title(f'Reaction Latency by MPID (Top {top_n} by Activity)',
                    fontweight='bold', fontsize=15, pad=20)
        ax.grid(axis='y', alpha=0.25, which='both')
        plt.xticks(rotation=90, fontsize=10)
        
        # Add counts above each box
        for i, mpid in enumerate(mpid_medians.index):
            count = len(df_top[df_top['mpid'] == mpid])
            median = mpid_medians[mpid]
            y_pos = ax.get_ylim()[1] * 0.85
            ax.text(i, y_pos, f'n={count:,}',
                   ha='center', va='bottom', fontsize=7, rotation=90)
        
        plt.tight_layout()
        output_path = self.figures_dir / "latency_by_mpid.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        logger.info(f"  ✓ Saved {output_path.name}")
        plt.close()
    
    def generate_time_of_day_analysis(self):
        """Clean time-of-day analysis with error bands."""
        logger.info("\n📊 Generating time-of-day analysis...")
        
        hourly = self.df.groupby('hour_of_day')['latency_us'].agg([
            ('median', 'median'),
            ('count', 'count'),
            ('p25', lambda x: np.percentile(x, 25)),
            ('p75', lambda x: np.percentile(x, 75))
        ]).reset_index()
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Line plot with IQR shading
        ax = axes[0]
        ax.plot(hourly['hour_of_day'], hourly['median'],
               marker='o', linewidth=3, markersize=12, color='#3498db',
               markerfacecolor='white', markeredgewidth=2.5, markeredgecolor='#3498db')
        ax.fill_between(hourly['hour_of_day'], hourly['p25'], hourly['p75'],
                       alpha=0.25, color='#3498db', label='IQR (p25-p75)')
        ax.set_xlabel('Hour of Day (ET)', fontweight='bold', fontsize=13)
        ax.set_ylabel('Median Latency (μs)', fontweight='bold', fontsize=13)
        ax.set_title('Median Latency by Hour', fontweight='bold', fontsize=14, pad=15)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xticks(hourly['hour_of_day'])
        ax.legend(fontsize=11, frameon=True, fancybox=True, shadow=True)
        
        # Volume bar chart with gradient
        ax = axes[1]
        colors = sns.cubehelix_palette(len(hourly), start=2, rot=0, dark=0.3, light=0.8, reverse=True)
        bars = ax.bar(hourly['hour_of_day'], hourly['count'],
                     color=colors, edgecolor='white', linewidth=2, alpha=0.9)
        ax.set_xlabel('Hour of Day (ET)', fontweight='bold', fontsize=13)
        ax.set_ylabel('Measurement Count', fontweight='bold', fontsize=13)
        ax.set_title('Activity Volume by Hour', fontweight='bold', fontsize=14, pad=15)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_xticks(hourly['hour_of_day'])
        
        # Value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height,
                   f'{int(height/1000)}K',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        output_path = self.figures_dir / "latency_time_of_day.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        logger.info(f"  ✓ Saved {output_path.name}")
        plt.close()
    
    def generate_symbol_comparison(self):
        """Clean symbol comparison with violin plots."""
        logger.info("\n📊 Generating symbol comparison...")
        
        symbol_stats = self.df.groupby('symbol')['latency_us'].agg([
            ('median', 'median'), ('count', 'count')
        ]).reset_index().sort_values('median')
        
        symbol_order = symbol_stats['symbol'].tolist()
        df_plot = self.df[self.df['symbol'].isin(symbol_order)].copy()
        df_plot['symbol'] = pd.Categorical(df_plot['symbol'], categories=symbol_order, ordered=True)
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
        
        # Violin plot
        ax = axes[0]
        sns.violinplot(data=df_plot, x='symbol', y='latency_us',
                      palette='muted', inner='box', ax=ax, alpha=0.75, linewidth=1.5)
        ax.set_yscale('log')
        ax.set_ylabel('Latency (μs, log scale)', fontweight='bold', fontsize=13)
        ax.set_xlabel('Symbol', fontweight='bold', fontsize=13)
        ax.set_title('Latency Distribution by Symbol', fontweight='bold', fontsize=14, pad=15)
        ax.grid(axis='y', alpha=0.25, which='both')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=12)
        
        # Volume bar chart
        ax = axes[1]
        colors = sns.color_palette('viridis', len(symbol_stats))
        bars = ax.bar(symbol_stats['symbol'], symbol_stats['count'],
                     color=colors, edgecolor='white', linewidth=2, alpha=0.9)
        ax.set_xlabel('Symbol', fontweight='bold', fontsize=13)
        ax.set_ylabel('Measurement Count', fontweight='bold', fontsize=13)
        ax.set_title('Activity Volume by Symbol', fontweight='bold', fontsize=14, pad=15)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=12)
        
        # Value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height,
                   f'{int(height/1000)}K',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        output_path = self.figures_dir / "latency_by_symbol.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        logger.info(f"  ✓ Saved {output_path.name}")
        plt.close()
    
    def generate_event_type_analysis(self):
        """Beautiful event type breakdown."""
        logger.info("\n📊 Generating event type analysis...")
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Pie chart with percentages
        ax = axes[0]
        event_counts = self.df['event_type'].value_counts()
        colors = sns.color_palette('Set3', len(event_counts))
        wedges, texts, autotexts = ax.pie(event_counts.values, labels=event_counts.index,
                                          autopct='%1.1f%%', colors=colors,
                                          startangle=90, textprops={'fontweight': 'bold', 'fontsize': 12})
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(13)
        ax.set_title('Event Type Distribution', fontweight='bold', fontsize=14, pad=15)
        
        # Latency comparison
        ax = axes[1]
        event_order = event_counts.index.tolist()
        sns.violinplot(data=self.df, x='event_type', y='latency_us', order=event_order,
                      palette='Set2', inner='box', ax=ax, alpha=0.75, linewidth=1.5)
        ax.set_yscale('log')
        ax.set_ylabel('Latency (μs, log scale)', fontweight='bold', fontsize=13)
        ax.set_xlabel('Event Type', fontweight='bold', fontsize=13)
        ax.set_title('Latency by Event Type', fontweight='bold', fontsize=14, pad=15)
        ax.grid(axis='y', alpha=0.25, which='both')
        
        # Add medians
        for i, et in enumerate(event_order):
            median = self.df[self.df['event_type'] == et]['latency_us'].median()
            ax.text(i, ax.get_ylim()[0] * 1.5, f'{median:.0f}μs',
                   ha='center', va='bottom', fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                            edgecolor='gray', linewidth=1.5, alpha=0.9))
        
        plt.tight_layout()
        output_path = self.figures_dir / "event_type_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        logger.info(f"  ✓ Saved {output_path.name}")
        plt.close()
    
    def generate_hft_vs_traditional(self):
        """Beautiful firm category comparison."""
        logger.info("\n📊 Generating firm category analysis...")
        
        # Sample data to avoid memory issues (500k per category max)
        df_sampled = self.df.groupby('firm_category', group_keys=False).apply(
            lambda x: x.sample(min(len(x), 500000), random_state=42)
        ).reset_index(drop=True)
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
        
        # Order categories by median latency
        cat_order = df_sampled.groupby('firm_category')['latency_us'].median().sort_values().index.tolist()
        
        # Box plot comparison
        ax = axes[0]
        sns.boxplot(data=df_sampled, x='firm_category', y='latency_us',
                   order=cat_order, palette=['#2ecc71', '#e74c3c', '#95a5a6', '#3498db'],
                   ax=ax, linewidth=2, flierprops=dict(marker='o', markersize=2, alpha=0.1))
        ax.set_yscale('log')
        ax.set_ylabel('Latency (μs, log scale)', fontweight='bold', fontsize=13)
        ax.set_xlabel('Firm Category', fontweight='bold', fontsize=13)
        ax.set_title('HFT vs Traditional Broker Latencies', fontweight='bold', fontsize=14, pad=15)
        ax.grid(axis='y', alpha=0.25, which='both')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=20, ha='right', fontsize=11)
        
        # Histogram overlay
        ax = axes[1]
        colors = {'Active Fast Market Maker': '#2ecc71', 'Sporadic/Slow HFT': '#e74c3c',
                  'Traditional Broker': '#3498db', 'Other': '#95a5a6'}
        for cat in cat_order:
            data = self.df[self.df['firm_category'] == cat]['latency_us']
            if len(data) > 100:  # Only plot if sufficient data
                # Sample for histogram too
                if len(data) > 100000:
                    data = data.sample(100000, random_state=42)
                sns.histplot(np.log10(data), bins=60, kde=True, alpha=0.5,
                           color=colors.get(cat, '#95a5a6'), label=cat, ax=ax, linewidth=0, stat='density')
        ax.set_xlabel('log₁₀(Latency in μs)', fontweight='bold', fontsize=13)
        ax.set_ylabel('Density', fontweight='bold', fontsize=13)
        ax.set_title('Latency Distribution Overlay', fontweight='bold', fontsize=14, pad=15)
        ax.legend(fontsize=10, frameon=True, fancybox=True, shadow=True)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        output_path = self.figures_dir / "firm_category_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        logger.info(f"  ✓ Saved {output_path.name}")
        plt.close()
    
    def run_statistical_tests(self):
        """Run comprehensive statistical tests."""
        logger.info("\n📈 Running statistical tests...")
        
        results = {}
        
        # H1: MPID differences
        mpid_groups = [g['latency_us'].values for _, g in self.df.groupby('mpid') if len(g) >= 100]
        if len(mpid_groups) >= 2:
            h, p = stats.kruskal(*mpid_groups)
            results['H1_MPID'] = {'H': h, 'p_value': p, 'sig': p < 0.01}
            logger.info(f"  H1 (MPID): H={h:.2f}, p={p:.2e}, Sig={p < 0.01}")
        
        # H2: Time-of-day
        hour_groups = [g['latency_us'].values for _, g in self.df.groupby('hour_of_day') if len(g) >= 100]
        if len(hour_groups) >= 2:
            h, p = stats.kruskal(*hour_groups)
            results['H2_TimeOfDay'] = {'H': h, 'p_value': p, 'sig': p < 0.01}
            logger.info(f"  H2 (Time): H={h:.2f}, p={p:.2e}, Sig={p < 0.01}")
        
        # H3: Symbol differences
        symbol_groups = [g['latency_us'].values for _, g in self.df.groupby('symbol') if len(g) >= 100]
        if len(symbol_groups) >= 2:
            h, p = stats.kruskal(*symbol_groups)
            results['H3_Symbol'] = {'H': h, 'p_value': p, 'sig': p < 0.01}
            logger.info(f"  H3 (Symbol): H={h:.2f}, p={p:.2e}, Sig={p < 0.01}")
        
        # HFT vs Traditional
        hft = self.df[self.df['firm_category'] == 'HFT/Market Maker']['latency_us'].values
        trad = self.df[self.df['firm_category'] == 'Traditional Broker-Dealer']['latency_us'].values
        if len(hft) > 0 and len(trad) > 0:
            u, p = stats.mannwhitneyu(hft, trad)
            speedup = np.median(trad) / np.median(hft)
            results['HFT_vs_Trad'] = {
                'U': u, 'p_value': p, 'sig': p < 0.01,
                'HFT_median': np.median(hft), 'Trad_median': np.median(trad),
                'speedup': speedup
            }
            logger.info(f"  HFT vs Trad: U={u:.2e}, p={p:.2e}, Speedup={speedup:.1f}x")
        
        # Save results
        pd.DataFrame(results).T.to_csv(self.tables_dir / "statistical_tests.csv")
        logger.info(f"  ✓ Saved statistical_tests.csv")
        
        return results
    
    def generate_summary_tables(self):
        """Generate all summary tables."""
        logger.info("\n📊 Generating summary tables...")
        
        # Overall stats
        stats_df = self.df['latency_us'].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
        stats_df.to_csv(self.tables_dir / "overall_statistics.csv")
        
        # Firm stats
        firm_stats = self.df.groupby('firm')['latency_us'].agg([
            ('Count', 'count'), ('Median_μs', 'median'), ('Mean_μs', 'mean'),
            ('P10_μs', lambda x: np.percentile(x, 10)),
            ('P90_μs', lambda x: np.percentile(x, 90))
        ]).round(2).sort_values('Count', ascending=False)
        firm_stats.to_csv(self.tables_dir / "firm_statistics.csv")
        
        # Symbol stats
        symbol_stats = self.df.groupby('symbol')['latency_us'].agg([
            ('Count', 'count'), ('Median_μs', 'median')
        ]).round(2).sort_values('Median_μs')
        symbol_stats.to_csv(self.tables_dir / "symbol_statistics.csv")
        
        # Event type stats
        event_stats = self.df.groupby('event_type')['latency_us'].agg([
            ('Count', 'count'), ('Pct', lambda x: len(x)/len(self.df)*100),
            ('Median_μs', 'median')
        ]).round(2).sort_values('Count', ascending=False)
        event_stats.to_csv(self.tables_dir / "event_type_statistics.csv")
        
        # Category stats
        cat_stats = self.df.groupby('firm_category')['latency_us'].agg([
            ('Count', 'count'), ('Median_μs', 'median'), ('Mean_μs', 'mean')
        ]).round(2)
        cat_stats.to_csv(self.tables_dir / "firm_category_statistics.csv")
        
        logger.info("  ✓ Saved 5 summary tables")
    
    def generate_all(self):
        """Generate all visualizations and analyses."""
        logger.info("=" * 80)
        logger.info("BEAUTIFUL LATENCY ANALYTICS (SEABORN)")
        logger.info("=" * 80)
        
        self.load_data()
        
        self.generate_latency_histogram()
        self.generate_firm_violin_plot()
        self.generate_mpid_breakdown()
        self.generate_time_of_day_analysis()
        self.generate_symbol_comparison()
        self.generate_event_type_analysis()
        self.generate_hft_vs_traditional()
        
        self.generate_summary_tables()
        self.run_statistical_tests()
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ COMPLETE")
        logger.info("=" * 80)
        logger.info(f"📁 {self.output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate beautiful analytics")
    parser.add_argument("--results", required=True, help="Latency results parquet")
    parser.add_argument("--output", required=True, help="Output directory")
    
    args = parser.parse_args()
    
    analytics = LatencyAnalytics(args.results, args.output)
    analytics.generate_all()
