"""
Master Orchestrator Script - Generate All Analytics
Executes all figure generation and statistical analysis in sequence
Optimized for multi-day, multi-contract analysis
"""

import pandas as pd
import argparse
from pathlib import Path
import sys
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from config import FIGURES_DIR, TABLES_DIR

# Import all figure generators
from analysis.figures.fig_01_distribution import generate_figure_01
from analysis.figures.fig_02_firm_categories import generate_figure_02
from analysis.figures.fig_03_top_firms import generate_figure_03
from analysis.figures.fig_04_symbols import generate_figure_04
from analysis.figures.fig_05_time_of_day import generate_figure_05
from analysis.figures.fig_06_firm_correlation import generate_figure_06
from analysis.figures.fig_07_symbol_correlation import generate_figure_07
from analysis.figures.fig_08_weekly_heatmap import generate_figure_08
from analysis.figures.fig_09_contract_comparison import generate_figure_09


def print_banner(text: str) -> None:
    """Print formatted banner"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Generate all MPID latency analytics')
    parser.add_argument('--data', required=True, help='Path to latencies.parquet file')
    parser.add_argument('--output', default=str(FIGURES_DIR), help='Output directory for figures')
    parser.add_argument('--skip-stats', action='store_true', help='Skip statistical analysis')
    parser.add_argument('--skip-figs', action='store_true', help='Skip figure generation')
    args = parser.parse_args()
    
    # Load data
    print_banner("MPID LATENCY ANALYSIS - MASTER ORCHESTRATOR")
    print(f"📂 Loading data from: {args.data}")
    start_time = datetime.now()
    
    df = pd.read_parquet(args.data)
    print(f"✓ Loaded {len(df):,} latency observations")
    print(f"  Date range: {pd.to_datetime(df['nasdaq_time_ns'], unit='ns').min()} to {pd.to_datetime(df['nasdaq_time_ns'], unit='ns').max()}")
    print(f"  Symbols: {df['symbol'].nunique()} unique")
    print(f"  MPIDs: {df['mpid'].nunique()} unique")
    
    # Ensure output directories exist
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate figures
    if not args.skip_figs:
        print_banner("GENERATING FIGURES (9 Total)")
        
        figures = [
            ("Figure 01: Overall Distribution", generate_figure_01),
            ("Figure 02: Firm Categories", generate_figure_02),
            ("Figure 03: Top Firms", generate_figure_03),
            ("Figure 04: Symbol Analysis", generate_figure_04),
            ("Figure 05: Time-of-Day Patterns", generate_figure_05),
            ("Figure 06: Firm Correlation", generate_figure_06),
            ("Figure 07: Symbol Correlation", generate_figure_07),
            ("Figure 08: Weekly Heatmap", generate_figure_08),
            ("Figure 09: Contract Comparison", generate_figure_09),
        ]
        
        for i, (name, func) in enumerate(figures, 1):
            try:
                print(f"\n[{i}/9] {name}...")
                func(df, output_dir)
            except Exception as e:
                print(f"❌ Error generating {name}: {e}")
                import traceback
                traceback.print_exc()
    
    # Run statistical analysis
    if not args.skip_stats:
        print_banner("RUNNING STATISTICAL ANALYSIS")
        try:
            from analysis.stats.comprehensive_stats import run_comprehensive_analysis
            stats_results = run_comprehensive_analysis(df, TABLES_DIR)
            print(f"✓ Statistical analysis complete - results saved to {TABLES_DIR}")
        except Exception as e:
            print(f"❌ Error in statistical analysis: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print_banner("ANALYSIS COMPLETE")
    print(f"⏱️  Total execution time: {duration:.1f} seconds")
    print(f"📊 Figures saved to: {output_dir}")
    print(f"📈 Tables saved to: {TABLES_DIR}")
    print(f"\n🎉 All analytics generated successfully!")


if __name__ == '__main__':
    main()
