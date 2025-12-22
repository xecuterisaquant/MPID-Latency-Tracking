"""
High-Performance Statistical Analysis Utilities
Optimized with Numba for large-scale analysis
"""

import numpy as np
import pandas as pd
from scipy import stats
from numba import jit
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Import config
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import SIGNIFICANCE_LEVEL, EFFECT_SIZE_SMALL, EFFECT_SIZE_MEDIUM, EFFECT_SIZE_LARGE


@jit(nopython=True, cache=True)
def fast_median(arr: np.ndarray) -> float:
    """Numba-optimized median calculation"""
    sorted_arr = np.sort(arr)
    n = len(sorted_arr)
    if n % 2 == 0:
        return (sorted_arr[n//2 - 1] + sorted_arr[n//2]) / 2.0
    else:
        return sorted_arr[n//2]


@jit(nopython=True, cache=True)
def fast_quantiles(arr: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Numba-optimized quantile calculation"""
    sorted_arr = np.sort(arr)
    n = len(sorted_arr)
    result = np.empty(len(q))
    
    for i, quantile in enumerate(q):
        idx = (n - 1) * quantile
        lower = int(np.floor(idx))
        upper = int(np.ceil(idx))
        weight = idx - lower
        result[i] = sorted_arr[lower] * (1 - weight) + sorted_arr[upper] * weight
    
    return result


@jit(nopython=True, cache=True)
def fast_variance(arr: np.ndarray) -> float:
    """Numba-optimized variance calculation"""
    mean = np.mean(arr)
    return np.sum((arr - mean) ** 2) / (len(arr) - 1)


@jit(nopython=True, cache=True)
def fast_std(arr: np.ndarray) -> float:
    """Numba-optimized standard deviation"""
    return np.sqrt(fast_variance(arr))


def summarize_group(data: np.ndarray) -> Dict[str, float]:
    """
    Fast summary statistics for a group
    """
    return {
        'count': len(data),
        'mean': np.mean(data),
        'median': fast_median(data),
        'std': fast_std(data),
        'min': np.min(data),
        'max': np.max(data),
        'q25': fast_quantiles(data, np.array([0.25]))[0],
        'q75': fast_quantiles(data, np.array([0.75]))[0],
        'q95': fast_quantiles(data, np.array([0.95]))[0],
        'q99': fast_quantiles(data, np.array([0.99]))[0]
    }


def kruskal_wallis_test(df: pd.DataFrame, group_col: str, value_col: str) -> Dict[str, float]:
    """
    Perform Kruskal-Wallis H-test for independent samples
    Returns test statistic, p-value, and effect size (epsilon-squared)
    """
    # Group data
    groups = [group[value_col].values for name, group in df.groupby(group_col)]
    
    # Kruskal-Wallis test
    h_stat, p_value = stats.kruskal(*groups)
    
    # Effect size (epsilon-squared)
    n = len(df)
    k = len(groups)
    epsilon_squared = (h_stat - k + 1) / (n - k)
    
    # Interpret effect size
    if epsilon_squared < EFFECT_SIZE_SMALL:
        effect_interpretation = "negligible"
    elif epsilon_squared < EFFECT_SIZE_MEDIUM:
        effect_interpretation = "small"
    elif epsilon_squared < EFFECT_SIZE_LARGE:
        effect_interpretation = "medium"
    else:
        effect_interpretation = "large"
    
    return {
        'h_statistic': h_stat,
        'p_value': p_value,
        'epsilon_squared': epsilon_squared,
        'effect_size': effect_interpretation,
        'n_groups': k,
        'n_total': n,
        'significant': p_value < SIGNIFICANCE_LEVEL
    }


def mann_whitney_test(group1: np.ndarray, group2: np.ndarray) -> Dict[str, float]:
    """
    Perform Mann-Whitney U test for two independent samples
    """
    u_stat, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
    
    # Effect size (rank-biserial correlation)
    n1, n2 = len(group1), len(group2)
    r = 1 - (2 * u_stat) / (n1 * n2)
    
    return {
        'u_statistic': u_stat,
        'p_value': p_value,
        'rank_biserial': r,
        'significant': p_value < SIGNIFICANCE_LEVEL
    }


def bootstrap_confidence_interval(data: np.ndarray, statistic_func=np.median,
                                  n_bootstrap: int = 10000, alpha: float = 0.05,
                                  random_state: int = 42) -> Tuple[float, float]:
    """
    Calculate bootstrap confidence interval for a statistic
    """
    np.random.seed(random_state)
    n = len(data)
    bootstrap_stats = np.empty(n_bootstrap)
    
    for i in range(n_bootstrap):
        sample = np.random.choice(data, size=n, replace=True)
        bootstrap_stats[i] = statistic_func(sample)
    
    lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
    upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))
    
    return lower, upper


def correlation_matrix(df: pd.DataFrame, method: str = 'spearman') -> pd.DataFrame:
    """
    Calculate correlation matrix (Spearman by default for non-normal data)
    """
    if method == 'spearman':
        return df.corr(method='spearman')
    elif method == 'pearson':
        return df.corr(method='pearson')
    elif method == 'kendall':
        return df.corr(method='kendall')
    else:
        raise ValueError(f"Unknown correlation method: {method}")


def test_normality(data: np.ndarray, test: str = 'shapiro') -> Dict[str, float]:
    """
    Test for normality (Shapiro-Wilk by default)
    """
    if test == 'shapiro':
        stat, p_value = stats.shapiro(data[:5000])  # Shapiro limited to 5000 samples
    elif test == 'kstest':
        stat, p_value = stats.kstest(data, 'norm')
    else:
        raise ValueError(f"Unknown normality test: {test}")
    
    return {
        'statistic': stat,
        'p_value': p_value,
        'is_normal': p_value > SIGNIFICANCE_LEVEL
    }


def cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """
    Calculate Cohen's d effect size for two groups
    """
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    
    return (np.mean(group1) - np.mean(group2)) / pooled_std


def calculate_summary_table(df: pd.DataFrame, group_col: str, value_col: str,
                            top_n: Optional[int] = None) -> pd.DataFrame:
    """
    Create comprehensive summary statistics table by group
    """
    # Get top N groups by count if specified
    if top_n:
        top_groups = df[group_col].value_counts().head(top_n).index
        df = df[df[group_col].isin(top_groups)]
    
    # Calculate statistics for each group
    summary_stats = []
    for name, group in df.groupby(group_col):
        data = group[value_col].values
        stats_dict = summarize_group(data)
        stats_dict[group_col] = name
        summary_stats.append(stats_dict)
    
    # Convert to DataFrame
    summary_df = pd.DataFrame(summary_stats)
    
    # Reorder columns
    cols = [group_col, 'count', 'mean', 'median', 'std', 'min', 'q25', 'q75', 'q95', 'q99', 'max']
    summary_df = summary_df[cols]
    
    # Sort by median
    summary_df = summary_df.sort_values('median')
    
    return summary_df


def run_robustness_tests(df: pd.DataFrame, group_col: str, value_col: str,
                        sample_sizes: List[int] = [10000, 50000, 100000, 500000]) -> pd.DataFrame:
    """
    Test robustness across different sample sizes
    """
    results = []
    
    for sample_size in sample_sizes:
        if len(df) < sample_size:
            continue
        
        # Random sample
        sample_df = df.sample(sample_size, random_state=42)
        
        # Run Kruskal-Wallis test
        kw_result = kruskal_wallis_test(sample_df, group_col, value_col)
        
        results.append({
            'sample_size': sample_size,
            'h_statistic': kw_result['h_statistic'],
            'p_value': kw_result['p_value'],
            'epsilon_squared': kw_result['epsilon_squared'],
            'effect_size': kw_result['effect_size']
        })
    
    return pd.DataFrame(results)


def detect_outliers_iqr(data: np.ndarray, multiplier: float = 1.5) -> Tuple[np.ndarray, Dict]:
    """
    Detect outliers using IQR method
    Returns boolean mask and outlier statistics
    """
    q1, q3 = fast_quantiles(data, np.array([0.25, 0.75]))
    iqr = q3 - q1
    
    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr
    
    outlier_mask = (data < lower_bound) | (data > upper_bound)
    
    outlier_stats = {
        'n_outliers': np.sum(outlier_mask),
        'pct_outliers': 100 * np.sum(outlier_mask) / len(data),
        'lower_bound': lower_bound,
        'upper_bound': upper_bound,
        'q1': q1,
        'q3': q3,
        'iqr': iqr
    }
    
    return outlier_mask, outlier_stats
