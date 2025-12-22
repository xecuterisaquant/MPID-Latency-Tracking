"""
Quick Test Script - Validate Setup Before Data Arrives
Tests all components without requiring the full dataset
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test all required imports"""
    print("🧪 Testing imports...")
    try:
        import pandas as pd
        import numpy as np
        import numba
        import matplotlib
        import seaborn
        import scipy
        print("  ✅ All core packages imported successfully")
        return True
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False


def test_numba_compilation():
    """Test Numba JIT compilation"""
    print("\n🧪 Testing Numba JIT compilation...")
    try:
        from numba import jit
        
        @jit(nopython=True, cache=True)
        def test_func(x):
            return x * 2 + 1
        
        result = test_func(5.0)
        assert result == 11.0
        print("  ✅ Numba JIT compilation working")
        return True
    except Exception as e:
        print(f"  ❌ Numba error: {e}")
        return False


def test_config():
    """Test configuration file"""
    print("\n🧪 Testing config.py...")
    try:
        from config import (
            ALL_DATES, CONTRACTS, SYMBOLS, EDT_OFFSET_NS,
            FIGURES_DIR, TABLES_DIR, MATCHING_WINDOW_NS
        )
        
        print(f"  Date range: {len(ALL_DATES)} trading days")
        print(f"  Contracts: {list(CONTRACTS.keys())}")
        print(f"  Symbols: {len(SYMBOLS)} ({', '.join(SYMBOLS[:3])}...)")
        print(f"  EDT offset: {EDT_OFFSET_NS / 3600 / 1e9:.0f} hours")
        print(f"  Matching window: {MATCHING_WINDOW_NS / 1e9:.0f} seconds")
        print("  ✅ Config loaded successfully")
        return True
    except Exception as e:
        print(f"  ❌ Config error: {e}")
        return False


def test_utilities():
    """Test utility functions"""
    print("\n🧪 Testing utility functions...")
    try:
        from analysis.utils.stats import summarize_group, fast_median
        from analysis.utils.plotting import smart_sample
        
        # Test data
        test_data = np.random.randn(10000)
        
        # Test stats
        stats = summarize_group(test_data)
        assert 'mean' in stats and 'median' in stats
        
        # Test numba median
        median_val = fast_median(test_data)
        assert abs(median_val - np.median(test_data)) < 0.01
        
        # Test sampling
        test_df = pd.DataFrame({'value': test_data, 'category': np.random.choice(['A', 'B', 'C'], 10000)})
        sampled = smart_sample(test_df, max_size=1000, stratify_col='category')
        assert len(sampled) <= 1000
        
        print("  ✅ All utility functions working")
        return True
    except Exception as e:
        print(f"  ❌ Utility error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mpid_lookup():
    """Test MPID lookup functions"""
    print("\n🧪 Testing MPID lookup...")
    try:
        from mpid_lookup.mpid_to_firm import get_firm_name, get_firm_category
        
        # Test known MPIDs
        test_mpids = ['WEDB', 'WLOV', 'JPMS', 'NITE', 'CANT']
        
        for mpid in test_mpids:
            firm = get_firm_name(mpid)
            category = get_firm_category(mpid)
            print(f"    {mpid}: {firm} ({category})")
        
        print("  ✅ MPID lookup working")
        return True
    except Exception as e:
        print(f"  ❌ MPID lookup error: {e}")
        return False


def test_binary_search():
    """Test optimized binary search"""
    print("\n🧪 Testing binary search algorithm...")
    try:
        from analysis.latency_pipeline_multiday import binary_search_first_after
        
        # Test data
        timestamps = np.array([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
        
        # Test cases
        test_cases = [
            (150, 1000, 1),  # Should find 200 (index 1)
            (250, 1000, 2),  # Should find 300 (index 2)
            (950, 100, 9),   # Should find 1000 (index 9)
            (1000, 100, -1), # Should not find (window too small)
        ]
        
        for target, window, expected in test_cases:
            result = binary_search_first_after(timestamps, target, window)
            assert result == expected, f"Expected {expected}, got {result} for target={target}"
        
        print("  ✅ Binary search algorithm working")
        return True
    except Exception as e:
        print(f"  ❌ Binary search error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_directory_structure():
    """Test that all required directories exist"""
    print("\n🧪 Testing directory structure...")
    try:
        from config import FIGURES_DIR, TABLES_DIR, OUTPUT_DIR
        
        required_dirs = [
            FIGURES_DIR,
            TABLES_DIR,
            OUTPUT_DIR,
            Path('analysis/figures'),
            Path('analysis/stats'),
            Path('analysis/utils'),
        ]
        
        for dir_path in required_dirs:
            if dir_path.exists():
                print(f"  ✓ {dir_path}")
            else:
                print(f"  ✗ Missing: {dir_path}")
                return False
        
        print("  ✅ All directories exist")
        return True
    except Exception as e:
        print(f"  ❌ Directory error: {e}")
        return False


def test_figure_scripts():
    """Test that all figure scripts can be imported"""
    print("\n🧪 Testing figure generation scripts...")
    try:
        from analysis.figures.fig_01_distribution import generate_figure_01
        from analysis.figures.fig_02_firm_categories import generate_figure_02
        from analysis.figures.fig_03_top_firms import generate_figure_03
        from analysis.figures.fig_04_symbols import generate_figure_04
        from analysis.figures.fig_05_time_of_day import generate_figure_05
        from analysis.figures.fig_06_firm_correlation import generate_figure_06
        from analysis.figures.fig_07_symbol_correlation import generate_figure_07
        from analysis.figures.fig_08_weekly_heatmap import generate_figure_08
        from analysis.figures.fig_09_contract_comparison import generate_figure_09
        
        print("  ✅ All 9 figure scripts importable")
        return True
    except Exception as e:
        print(f"  ❌ Figure script error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 80)
    print("  MPID LATENCY TRACKING - PRE-DATA VALIDATION SUITE")
    print("=" * 80)
    
    tests = [
        test_imports,
        test_numba_compilation,
        test_config,
        test_utilities,
        test_mpid_lookup,
        test_binary_search,
        test_directory_structure,
        test_figure_scripts,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n  ✅ Passed: {passed}/{total}")
    if passed < total:
        print(f"  ❌ Failed: {total - passed}/{total}")
        print("\n  ⚠️  Fix errors before processing data")
        return 1
    else:
        print("\n  🎉 All tests passed! Ready to process data when it arrives.")
        return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
