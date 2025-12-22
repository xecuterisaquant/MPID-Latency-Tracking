"""
High-Performance Plotting Utilities with Numba Optimization
Optimized for large-scale multi-day, multi-contract analysis
"""

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from numba import jit
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# Import config
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import (
    FIGURE_DPI, FIGURE_WIDTH, FIGURE_HEIGHT, FIGURE_FORMAT,
    SEABORN_STYLE, SEABORN_CONTEXT, CATEGORY_COLORS,
    MAX_SAMPLE_SIZE
)

# Set global plotting style
sns.set_style(SEABORN_STYLE)
sns.set_context(SEABORN_CONTEXT)


@jit(nopython=True, cache=True)
def fast_percentile(arr: np.ndarray, percentiles: np.ndarray) -> np.ndarray:
    """Numba-optimized percentile calculation"""
    sorted_arr = np.sort(arr)
    n = len(sorted_arr)
    result = np.empty(len(percentiles))
    
    for i, p in enumerate(percentiles):
        idx = (n - 1) * p / 100.0
        lower = int(np.floor(idx))
        upper = int(np.ceil(idx))
        weight = idx - lower
        result[i] = sorted_arr[lower] * (1 - weight) + sorted_arr[upper] * weight
    
    return result


@jit(nopython=True, cache=True)
def fast_histogram(data: np.ndarray, bins: int, range_min: float, range_max: float) -> Tuple[np.ndarray, np.ndarray]:
    """Numba-optimized histogram calculation"""
    hist = np.zeros(bins)
    bin_width = (range_max - range_min) / bins
    
    for val in data:
        if range_min <= val <= range_max:
            bin_idx = int((val - range_min) / bin_width)
            if bin_idx >= bins:
                bin_idx = bins - 1
            hist[bin_idx] += 1
    
    edges = np.linspace(range_min, range_max, bins + 1)
    return hist, edges


def smart_sample(df: pd.DataFrame, max_size: int = MAX_SAMPLE_SIZE, 
                 stratify_col: Optional[str] = None, random_state: int = 42) -> pd.DataFrame:
    """
    Intelligently sample large dataframes for plotting
    Maintains distribution when stratifying
    """
    if len(df) <= max_size:
        return df
    
    if stratify_col and stratify_col in df.columns:
        # Stratified sampling
        return df.groupby(stratify_col, group_keys=False).apply(
            lambda x: x.sample(min(len(x), max_size // df[stratify_col].nunique()), 
                             random_state=random_state)
        ).reset_index(drop=True)
    else:
        # Simple random sample
        return df.sample(max_size, random_state=random_state).reset_index(drop=True)


def setup_figure(figsize: Tuple[float, float] = (FIGURE_WIDTH, FIGURE_HEIGHT)) -> Tuple[plt.Figure, plt.Axes]:
    """Create figure with standard settings"""
    fig, ax = plt.subplots(figsize=figsize, dpi=FIGURE_DPI)
    return fig, ax


def save_figure(fig: plt.Figure, output_path: Path, tight: bool = True) -> None:
    """Save figure with standard settings"""
    if tight:
        fig.tight_layout()
    fig.savefig(output_path, dpi=FIGURE_DPI, format=FIGURE_FORMAT, bbox_inches='tight')
    plt.close(fig)
    print(f"✓ Saved: {output_path.name}")


def format_latency_axis(ax: plt.Axes, unit: str = 'ms') -> None:
    """Format axis labels for latency data"""
    ax.set_xlabel(f'Latency ({unit})', fontsize=12, fontweight='bold')
    ax.set_ylabel('Count', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)


def add_summary_stats_text(ax: plt.Axes, data: np.ndarray, x: float = 0.95, y: float = 0.95) -> None:
    """Add summary statistics text box to plot"""
    stats_text = (
        f"n = {len(data):,}\n"
        f"Median = {np.median(data):.2f} ms\n"
        f"Mean = {np.mean(data):.2f} ms\n"
        f"Std = {np.std(data):.2f} ms\n"
        f"p25 = {np.percentile(data, 25):.2f} ms\n"
        f"p75 = {np.percentile(data, 75):.2f} ms"
    )
    ax.text(x, y, stats_text, transform=ax.transAxes,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
            verticalalignment='top', horizontalalignment='right',
            fontsize=9, family='monospace')


def get_category_color(category: str) -> str:
    """Get color for firm category"""
    return CATEGORY_COLORS.get(category, '#95a5a6')


def plot_distribution_with_stats(data: pd.Series, title: str, output_path: Path,
                                 bins: int = 100, log_scale: bool = False,
                                 max_value: Optional[float] = None) -> None:
    """
    Fast distribution plot with automatic binning and stats
    """
    fig, ax = setup_figure()
    
    # Filter and convert to numpy for speed
    plot_data = data.dropna().values
    if max_value:
        plot_data = plot_data[plot_data <= max_value]
    
    # Fast histogram
    if log_scale:
        plot_data_log = np.log10(plot_data + 1)
        ax.hist(plot_data_log, bins=bins, alpha=0.7, edgecolor='black', linewidth=0.5)
        ax.set_xlabel('log₁₀(Latency + 1) (ms)', fontsize=12, fontweight='bold')
    else:
        ax.hist(plot_data, bins=bins, alpha=0.7, edgecolor='black', linewidth=0.5)
        ax.set_xlabel('Latency (ms)', fontsize=12, fontweight='bold')
    
    ax.set_ylabel('Count', fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3)
    
    # Add stats
    add_summary_stats_text(ax, plot_data)
    
    save_figure(fig, output_path)


def plot_category_comparison(df: pd.DataFrame, category_col: str, value_col: str,
                             title: str, output_path: Path,
                             top_n: Optional[int] = None,
                             palette: Optional[Dict] = None) -> None:
    """
    Fast categorical comparison with automatic sampling
    """
    # Sample if needed
    plot_df = smart_sample(df, stratify_col=category_col)
    
    # Filter to top N categories if specified
    if top_n:
        top_categories = df[category_col].value_counts().head(top_n).index
        plot_df = plot_df[plot_df[category_col].isin(top_categories)]
    
    # Sort by median
    category_order = plot_df.groupby(category_col)[value_col].median().sort_values().index
    
    fig, ax = setup_figure(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT * 1.2))
    
    # Use boxplot for speed (violin plots are slow with large data)
    sns.boxplot(data=plot_df, y=category_col, x=value_col, 
                order=category_order, palette=palette, ax=ax)
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Latency (ms)', fontsize=12, fontweight='bold')
    ax.set_ylabel(category_col.replace('_', ' ').title(), fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    
    save_figure(fig, output_path)


def plot_time_series(df: pd.DataFrame, time_col: str, value_col: str,
                     title: str, output_path: Path,
                     agg_func: str = 'median',
                     window: Optional[int] = None) -> None:
    """
    Fast time series plot with optional smoothing
    """
    # Group and aggregate
    if window:
        # Rolling window
        ts_data = df.groupby(time_col)[value_col].agg(agg_func).rolling(window).mean()
    else:
        ts_data = df.groupby(time_col)[value_col].agg(agg_func)
    
    fig, ax = setup_figure()
    
    ax.plot(ts_data.index, ts_data.values, linewidth=2, alpha=0.8)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel(time_col.replace('_', ' ').title(), fontsize=12, fontweight='bold')
    ax.set_ylabel(f'{agg_func.title()} Latency (ms)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    save_figure(fig, output_path)


def plot_heatmap(data: pd.DataFrame, title: str, output_path: Path,
                 cmap: str = 'YlOrRd', fmt: str = '.0f',
                 annot: bool = True) -> None:
    """
    Fast heatmap for correlation/cross-tabulation
    """
    fig, ax = setup_figure(figsize=(FIGURE_WIDTH * 1.2, FIGURE_HEIGHT))
    
    sns.heatmap(data, annot=annot, fmt=fmt, cmap=cmap, ax=ax,
                cbar_kws={'label': 'Latency (ms)'}, linewidths=0.5)
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    
    save_figure(fig, output_path)


def create_subplot_grid(n_plots: int, ncols: int = 2) -> Tuple[plt.Figure, np.ndarray]:
    """
    Create grid of subplots for multi-panel figures
    """
    nrows = int(np.ceil(n_plots / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(FIGURE_WIDTH * ncols, FIGURE_HEIGHT * nrows), 
                             dpi=FIGURE_DPI)
    
    # Flatten axes array for easy indexing
    if n_plots > 1:
        axes = axes.flatten()
    
    return fig, axes
