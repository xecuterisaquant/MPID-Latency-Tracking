"""
Comprehensive Statistical Analysis Script
Publication-ready statistical tests with Numba optimization
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from typing import Dict

sys.path.append(str(Path(__file__).parent.parent.parent))
from config import TABLES_DIR, SIGNIFICANCE_LEVEL
from analysis.utils.stats import (
    kruskal_wallis_test, mann_whitney_test, calculate_summary_table,
    run_robustness_tests, bootstrap_confidence_interval, cohens_d,
    summarize_group
)
from mpid_lookup.mpid_to_firm import get_firm_name, get_firm_category


def run_comprehensive_analysis(df: pd.DataFrame, output_dir: Path = TABLES_DIR) -> Dict:
    """
    Run all statistical tests and save results
    OPTIMIZED: Uses sampling for expensive operations
    """
    print("\n🔬 Running Comprehensive Statistical Analysis...")
    print(f"  Dataset size: {len(df):,} rows")
    
    # Add firm info if not present
    if 'firm_name' not in df.columns:
        print("  Adding firm names...")
        df['firm_name'] = df['mpid'].apply(get_firm_name)
    if 'firm_category' not in df.columns:
        print("  Adding firm categories...")
        df['firm_category'] = df['mpid'].apply(get_firm_category)
    
    results = {}
    
    # ========================================================================
    # 1. Overall Summary Statistics
    # ========================================================================
    print("\n📊 Computing overall summary statistics...")
    overall_stats = summarize_group(df['latency_ms'].values)
    
    # Bootstrap CI for median
    median_ci = bootstrap_confidence_interval(df['latency_ms'].values, statistic_func=np.median)
    overall_stats['median_ci_lower'] = median_ci[0]
    overall_stats['median_ci_upper'] = median_ci[1]
    
    # Save
    overall_df = pd.DataFrame([overall_stats])
    overall_df.to_csv(output_dir / 'overall_statistics.csv', index=False)
    print(f"  ✓ Saved: overall_statistics.csv")
    results['overall'] = overall_stats
    
    # ========================================================================
    # 2. Kruskal-Wallis Tests (H1-H5)
    # ========================================================================
    print("\n🧪 Running Kruskal-Wallis tests...")
    
    kw_tests = {
        'H1_MPID': ('mpid', 'Do different MPIDs have different reaction latencies?'),
        'H2_Time': ('hour', 'Does latency vary by hour of day?'),
        'H3_Symbol': ('symbol', 'Does latency vary by symbol?'),
        'H4_FirmCategory': ('firm_category', 'Do firm categories have different latencies?'),
    }
    
    # Add contract test if column exists
    if 'contract' in df.columns and df['contract'].nunique() > 1:
        kw_tests['H5_Contract'] = ('contract', 'Do March and June contracts have different latencies?')
    
    # Add hour column if not present
    if 'hour' not in df.columns:
        df['hour'] = pd.to_datetime(df['nasdaq_time_ns'], unit='ns').dt.hour
    
    kw_results = []
    for hypothesis, (group_col, question) in kw_tests.items():
        print(f"  Testing {hypothesis}: {question}")
        result = kruskal_wallis_test(df, group_col, 'latency_ms')
        result['hypothesis'] = hypothesis
        result['group_column'] = group_col
        result['question'] = question
        kw_results.append(result)
        
        # Print result
        sig_marker = "✓ SIGNIFICANT" if result['significant'] else "✗ Not significant"
        print(f"    H = {result['h_statistic']:.2f}, p = {result['p_value']:.2e}, ε² = {result['epsilon_squared']:.4f} ({result['effect_size']}) {sig_marker}")
    
    kw_df = pd.DataFrame(kw_results)
    kw_df.to_csv(output_dir / 'kruskal_wallis_tests.csv', index=False)
    print(f"  ✓ Saved: kruskal_wallis_tests.csv")
    results['kruskal_wallis'] = kw_results
    
    # ========================================================================
    # 3. Group Summary Tables
    # ========================================================================
    print("\n📋 Generating group summary tables...")
    
    summary_tables = {
        'firm_category': ('firm_category', None),
        'top_firms': ('firm_name', 12),
        'top_mpids': ('mpid', 15),
        'symbols': ('symbol', None),
    }
    
    for name, (group_col, top_n) in summary_tables.items():
        print(f"  Creating {name} summary...")
        summary_df = calculate_summary_table(df, group_col, 'latency_ms', top_n=top_n)
        summary_df.to_csv(output_dir / f'summary_{name}.csv', index=False)
        print(f"    ✓ Saved: summary_{name}.csv ({len(summary_df)} groups)")
    
    # ========================================================================
    # 4. Robustness Tests
    # ========================================================================
    print("\n🔄 Running robustness tests across sample sizes...")
    # OPTIMIZED: Limit max sample size to 1M for speed
    sample_sizes = [10_000, 50_000, 100_000, 500_000, 1_000_000]
    
    # Filter to available sample sizes
    max_size = min(len(df), 1_000_000)  # Cap at 1M even if more data available
    sample_sizes = [s for s in sample_sizes if s <= max_size]
    
    if sample_sizes:
        print(f"  Testing sample sizes: {sample_sizes}")
        robustness_df = run_robustness_tests(df, 'mpid', 'latency_ms', sample_sizes=sample_sizes)
        robustness_df.to_csv(output_dir / 'robustness_tests.csv', index=False)
        print(f"  ✓ Saved: robustness_tests.csv (tested {len(sample_sizes)} sample sizes)")
        results['robustness'] = robustness_df.to_dict('records')
    
    # ========================================================================
    # 5. Pairwise Comparisons (Top Firm Categories)
    # ========================================================================
    print("\n🔀 Running pairwise comparisons between firm categories...")
    
    categories = df['firm_category'].unique()
    pairwise_results = []
    
    for i, cat1 in enumerate(categories):
        for cat2 in categories[i+1:]:
            group1 = df[df['firm_category'] == cat1]['latency_ms'].values
            group2 = df[df['firm_category'] == cat2]['latency_ms'].values
            
            # Mann-Whitney U test
            mw_result = mann_whitney_test(group1, group2)
            
            # Cohen's d
            d = cohens_d(group1, group2)
            
            pairwise_results.append({
                'category_1': cat1,
                'category_2': cat2,
                'n1': len(group1),
                'n2': len(group2),
                'median1': np.median(group1),
                'median2': np.median(group2),
                'u_statistic': mw_result['u_statistic'],
                'p_value': mw_result['p_value'],
                'rank_biserial': mw_result['rank_biserial'],
                'cohens_d': d,
                'significant': mw_result['significant']
            })
    
    pairwise_df = pd.DataFrame(pairwise_results)
    pairwise_df.to_csv(output_dir / 'pairwise_comparisons.csv', index=False)
    print(f"  ✓ Saved: pairwise_comparisons.csv ({len(pairwise_df)} comparisons)")
    results['pairwise'] = pairwise_results
    
    # ========================================================================
    # 6. Contract Comparison (if applicable)
    # ========================================================================
    if 'contract' in df.columns and df['contract'].nunique() == 2:
        print("\n📦 Comparing March vs June contracts...")
        
        contracts = df['contract'].unique()
        contract1_data = df[df['contract'] == contracts[0]]['latency_ms'].values
        contract2_data = df[df['contract'] == contracts[1]]['latency_ms'].values
        
        # Mann-Whitney
        mw_result = mann_whitney_test(contract1_data, contract2_data)
        
        # Cohen's d
        d = cohens_d(contract1_data, contract2_data)
        
        contract_comparison = {
            'contract_1': contracts[0],
            'contract_2': contracts[1],
            'n1': len(contract1_data),
            'n2': len(contract2_data),
            'median1': np.median(contract1_data),
            'median2': np.median(contract2_data),
            'mean1': np.mean(contract1_data),
            'mean2': np.mean(contract2_data),
            'u_statistic': mw_result['u_statistic'],
            'p_value': mw_result['p_value'],
            'rank_biserial': mw_result['rank_biserial'],
            'cohens_d': d,
            'significant': mw_result['significant']
        }
        
        contract_df = pd.DataFrame([contract_comparison])
        contract_df.to_csv(output_dir / 'contract_comparison.csv', index=False)
        print(f"  ✓ Saved: contract_comparison.csv")
        results['contract_comparison'] = contract_comparison
    
    print("\n✅ Statistical analysis complete!")
    return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='Path to latencies.parquet')
    parser.add_argument('--output', default=str(TABLES_DIR), help='Output directory')
    args = parser.parse_args()
    
    df = pd.read_parquet(args.data)
    run_comprehensive_analysis(df, Path(args.output))
