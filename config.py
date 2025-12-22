"""
Centralized configuration for Multi-Day, Multi-Contract MPID Latency Analysis
All configurable parameters in one place for easy deployment.
"""

from pathlib import Path
from typing import List, Dict
from datetime import date, timedelta
import multiprocessing

# ============================================================================
# DATA PATHS
# ============================================================================

# Base directories
PROJECT_ROOT = Path(__file__).parent.resolve()
DATA_ROOT = PROJECT_ROOT / "data"

# Input data directories
ES_DATA_DIR = DATA_ROOT / "itch"  # ES futures trades
NASDAQ_DATA_DIR = DATA_ROOT / "extracted"  # NASDAQ ITCH events
PCAP_DATA_DIR = DATA_ROOT / "pcap"  # Raw PCAP files (archive)

# Output directories
OUTPUT_DIR = DATA_ROOT / "output"
RESULTS_DIR = OUTPUT_DIR
FIGURES_DIR = OUTPUT_DIR / "analytics" / "figures"
TABLES_DIR = OUTPUT_DIR / "analytics" / "tables"
REPORTS_DIR = OUTPUT_DIR / "reports"

# Ensure output directories exist
for d in [OUTPUT_DIR, RESULTS_DIR, FIGURES_DIR, TABLES_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================================
# DATE RANGES - MULTI-DAY ANALYSIS
# ============================================================================
# Full analysis period: March 10-21, 2025 (12 trading days)
START_DATE = date(2025, 3, 10)
END_DATE = date(2025, 3, 21)

# Generate all trading days (exclude weekends)
ALL_DATES = []
current = START_DATE
while current <= END_DATE:
    if current.weekday() < 5:  # Monday=0, Friday=4
        ALL_DATES.append(current)
    current += timedelta(days=1)

# ============================================================================
# FUTURES CONTRACTS - MULTI-CONTRACT ANALYSIS
# ============================================================================
CONTRACTS = {
    'ESH25': {  # March 2025 contract
        'name': 'ES March 2025',
        'expiry': date(2025, 3, 21),
        'primary_period': (date(2025, 3, 10), date(2025, 3, 21))
    },
    'ESM25': {  # June 2025 contract
        'name': 'ES June 2025',
        'expiry': date(2025, 6, 20),
        'primary_period': (date(2025, 3, 10), date(2025, 3, 21))
    }
}

# Security IDs from CME
ES_SECURITY_IDS = {
    5002: 'ESH25',      # March E-mini S&P 500
    5003: 'ESM25',      # June E-mini S&P 500
    42005347: 'MES',    # Micro E-mini
}

# ============================================================================
# SYMBOLS - NASDAQ EQUITY UNIVERSE
# ============================================================================
SYMBOLS = [
    'SPY',   # S&P 500 ETF
    'QQQ',   # NASDAQ-100 ETF
    'IWM',   # Russell 2000 ETF
    'AAPL',  # Apple
    'MSFT',  # Microsoft
    'GOOG',  # Alphabet
    'AMZN',  # Amazon
    'META',  # Meta
    'NVDA',  # NVIDIA
    'TSLA'   # Tesla
]

# Legacy alias for backwards compatibility
TARGET_SYMBOLS = SYMBOLS
ES_CONTRACTS = list(CONTRACTS.keys())

# ============================================================================
# TIMESTAMP HANDLING
# ============================================================================
# Critical: ES data is UTC-encoded but represents EDT times
EDT_OFFSET_NS = 4 * 3600 * 1_000_000_000  # +4 hours in nanoseconds

# Timezone info
NASDAQ_TZ = 'America/New_York'  # EDT/EST
CME_TZ = 'America/Chicago'      # CDT/CST

# ============================================================================
# LATENCY MATCHING PARAMETERS
# ============================================================================
MATCHING_WINDOW_NS = 10_000_000_000  # 10 seconds in nanoseconds
MAX_LATENCY_SECONDS = 10.0
MIN_LATENCY_NS = 0
MAX_LATENCY_NS = MATCHING_WINDOW_NS

# Convert to milliseconds for filtering
MIN_LATENCY_MS = MIN_LATENCY_NS / 1_000_000
MAX_LATENCY_MS = MAX_LATENCY_NS / 1_000_000

# ES trade filters
MIN_ES_TRADE_SIZE = 1  # Minimum contracts
MIN_PRICE_MOVEMENT = 0  # Optional price movement filter

# ============================================================================
# PERFORMANCE OPTIMIZATION
# ============================================================================
# Memory management for week-long data
CHUNK_SIZE = 1_000_000  # Process in 1M row chunks
MAX_SAMPLE_SIZE = 500_000  # Max samples per category for plotting

# Parallel processing
NUM_WORKERS = max(1, multiprocessing.cpu_count() - 2)
N_JOBS = -1  # Use all available cores (for sklearn-style APIs)

# Numba optimization
USE_NUMBA = True
NUMBA_CACHE = True

# ============================================================================
# FIGURE SETTINGS - PUBLICATION QUALITY
# ============================================================================
FIGURE_DPI = 300
FIGURE_WIDTH = 12
FIGURE_HEIGHT = 8
FIGURE_FORMAT = 'png'

# Seaborn style
SEABORN_STYLE = 'whitegrid'
SEABORN_CONTEXT = 'paper'
SEABORN_PALETTE = 'Set2'

# Color scheme for firm categories
CATEGORY_COLORS = {
    'Active Fast Market Maker': '#2ecc71',      # Green
    'Sporadic/Slow HFT': '#e74c3c',             # Red
    'Traditional Broker': '#3498db',             # Blue
    'Other': '#95a5a6'                           # Gray
}

# ============================================================================
# STATISTICAL ANALYSIS
# ============================================================================
SIGNIFICANCE_LEVEL = 0.05
CONFIDENCE_LEVEL = 0.95

# Kruskal-Wallis test
KRUSKAL_WALLIS_GROUPS = ['mpid', 'symbol', 'hour', 'firm_category', 'contract']

# Effect size thresholds (epsilon-squared)
EFFECT_SIZE_SMALL = 0.01
EFFECT_SIZE_MEDIUM = 0.06
EFFECT_SIZE_LARGE = 0.14

# ============================================================================
# FIRM CATEGORIZATION
# ============================================================================
# Categories from mpid_lookup/mpid_to_firm.py
FIRM_CATEGORIES = [
    'Active Fast Market Maker',
    'Sporadic/Slow HFT',
    'Traditional Broker',
    'Other'
]

# Top firms/MPIDs to highlight
TOP_N_FIRMS = 12
TOP_N_MPIDS = 15

TOP_MPIDS = [
    'WEDB', 'WLOV', 'JPMS', 'NITE', 'CANT', 'EDGX',
    'MSCO', 'GSCO', 'VIRT', 'CITI', 'UBSS', 'DBAB'
]

# ============================================================================
# OUTPUT SETTINGS
# ============================================================================
# Parquet compression
PARQUET_ENGINE = 'pyarrow'
PARQUET_COMPRESSION = 'snappy'
PARQUET_COMPRESSION_LEVEL = None  # Use default

# CSV settings
CSV_FLOAT_FORMAT = '%.4f'

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ============================================================================
# DATA VALIDATION THRESHOLDS
# ============================================================================
MIN_OBSERVATIONS_PER_DAY = 500_000  # Flag if day has < 500K observations
MAX_OBSERVATIONS_PER_DAY = 20_000_000  # Flag if day has > 20M (potential duplication)

# Latency sanity checks
EXPECTED_MEDIAN_LATENCY_MS = 96  # ~96ms from single-day analysis
LATENCY_OUTLIER_THRESHOLD_MS = 5000  # Flag latencies > 5 seconds
EXPECTED_PCT_UNDER_100MS = 0.45  # ~45-50% should be under 100ms

# ============================================================================
# PROGRESS TRACKING
# ============================================================================
PROGRESS_BAR = True
VERBOSE = True

# Batch size for parallel processing
BATCH_SIZE = 100  # Files per batch

# Memory limits (MB)
MAX_MEMORY_MB = 32000  # 32GB, adjust for VM capacity

# ============================================================================
# DATA QUALITY FILTERS
# ============================================================================

# Exclude pre-market and post-market hours?
REGULAR_HOURS_ONLY = False  # Set to True to filter 9:30-16:00 ET

# Trading hours (Eastern Time)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0

# Extended hours
EXTENDED_HOURS_START = 4  # 4:00 AM ET
EXTENDED_HOURS_END = 20   # 8:00 PM ET

# ============================================================================
# OUTPUT FORMATS
# ============================================================================

# Parquet compression
PARQUET_COMPRESSION = 'snappy'  # Fast compression
PARQUET_COMPRESSION_LEVEL = None  # Default level

# For archival storage, use:
# PARQUET_COMPRESSION = 'zstd'
# PARQUET_COMPRESSION_LEVEL = 9

# CSV export settings
CSV_CHUNKSIZE = 1000000  # For very large outputs

# ============================================================================
# LOGGING
# ============================================================================

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL = 'INFO'

# Log file location
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ============================================================================
# VISUALIZATION
# ============================================================================

# Figure DPI (higher = better quality, larger files)
FIGURE_DPI = 300

# Figure size defaults
FIGURE_SIZE = (12, 8)

# Color palette
COLOR_PALETTE = 'Set2'

# ============================================================================
# VM DEPLOYMENT HELPERS
# ============================================================================

def get_vm_config():
    """
    Return VM-specific configuration.
    Detect if running on VM and adjust paths/settings accordingly.
    """
    import socket
    hostname = socket.gethostname()
    
    # Example VM detection (customize for your lab)
    if 'fintech-lab' in hostname.lower() or 'vm' in hostname.lower():
        return {
            'is_vm': True,
            'data_root': Path('/data/mpid_latency'),  # VM data mount
            'num_workers': 64,  # Assume beefy VM
            'max_memory_mb': 128000,  # 128GB
        }
    else:
        return {
            'is_vm': False,
            'data_root': DATA_ROOT,
            'num_workers': NUM_WORKERS,
            'max_memory_mb': MAX_MEMORY_MB,
        }

# ============================================================================
# DATE RANGE HELPERS
# ============================================================================

def get_analysis_dates():
    """
    Returns list of dates to analyze.
    Can be overridden via command-line or environment variables.
    """
    import os
    
    start_date = os.environ.get('ANALYSIS_START_DATE', '20250201')
    end_date = os.environ.get('ANALYSIS_END_DATE', '20250228')
    
    from datetime import datetime, timedelta
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y%m%d'))
        current += timedelta(days=1)
    
    return dates

# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Check that critical paths and settings are valid."""
    errors = []
    
    if not PROJECT_ROOT.exists():
        errors.append(f"Project root not found: {PROJECT_ROOT}")
    
    if NUM_WORKERS < 1:
        errors.append(f"Invalid NUM_WORKERS: {NUM_WORKERS}")
    
    if MAX_LATENCY_SECONDS <= 0:
        errors.append(f"Invalid MAX_LATENCY_SECONDS: {MAX_LATENCY_SECONDS}")
    
    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(errors))
    
    return True

# Auto-validate on import
validate_config()
