"""
Centralized configuration for MPID Latency Analysis

All configurable parameters in one place for easy VM deployment.
Adjust paths and settings here rather than modifying individual scripts.
"""

from pathlib import Path
from typing import List
import multiprocessing

# ============================================================================
# DATA PATHS
# ============================================================================

# Base directories - UPDATE THESE FOR VM DEPLOYMENT
PROJECT_ROOT = Path(__file__).parent.resolve()
DATA_ROOT = PROJECT_ROOT / "data"

# Input data directories
ES_DATA_DIR = DATA_ROOT / "es"
NASDAQ_DATA_DIR = DATA_ROOT / "extracted"
PCAP_DATA_DIR = DATA_ROOT / "pcap"

# Output directories
OUTPUT_DIR = DATA_ROOT / "output"
RESULTS_DIR = OUTPUT_DIR / "results"
FIGURES_DIR = OUTPUT_DIR / "figures"
REPORTS_DIR = OUTPUT_DIR / "reports"

# Ensure output directories exist
for d in [OUTPUT_DIR, RESULTS_DIR, FIGURES_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================================
# ANALYSIS PARAMETERS
# ============================================================================

# Target symbols to analyze (most liquid ES-correlated equities)
TARGET_SYMBOLS = [
    'QQQ',   # NASDAQ 100 ETF
    'SPY',   # S&P 500 ETF
    'IWM',   # Russell 2000 ETF
    'AAPL',  # Apple
    'NVDA',  # NVIDIA
    'TSLA',  # Tesla
    'AMZN',  # Amazon
    'MSFT',  # Microsoft
    'GOOGL', # Alphabet
    'META',  # Meta
]

# ES contracts to analyze (ESH5, ESM5, etc.)
ES_CONTRACTS = [
    'ES',   # Generic front-month
    'MES',  # Micro E-mini
]

# Security IDs from CME (update as needed)
ES_SECURITY_IDS = {
    5002: 'ES',          # E-mini S&P 500
    42005347: 'MES',     # Micro E-mini S&P 500
}

# Top MPIDs to focus on (update from data analysis)
TOP_MPIDS = [
    'WBPX',  # Wells Fargo
    'JPMS',  # JPMorgan
    'WCHV',  # Wells Fargo Clearing
    'VIRT',  # Virtu
    'GSCO',  # Goldman Sachs
    'MSCO',  # Morgan Stanley
    'CITI',  # Citi
    'DBAB',  # Deutsche Bank
    'UBSS',  # UBS
    'WEDB',  # Wells Fargo
]

# ============================================================================
# LATENCY JOIN PARAMETERS
# ============================================================================

# Maximum latency window to search (seconds)
MAX_LATENCY_SECONDS = 10.0

# Minimum trade size to trigger latency measurement (ES contracts)
MIN_ES_TRADE_SIZE = 5  # Filter out tiny trades

# Minimum price movement to consider (ticks)
MIN_PRICE_MOVEMENT = 1  # Optional: filter small price changes

# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

# Number of CPU cores to use (None = auto-detect, leave 1-2 free)
NUM_WORKERS = max(1, multiprocessing.cpu_count() - 2)

# Chunk size for streaming processing
CHUNK_SIZE = 10000  # Rows per chunk

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
