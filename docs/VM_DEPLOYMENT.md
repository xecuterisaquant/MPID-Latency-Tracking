# VM Deployment Guide for MPID Latency Analysis

## 🚀 Quick Start on Professor's Fintech Lab VM

### 1. Transfer Code to VM

```bash
# From your local machine
cd "d:\Harsh\FIN556 MPID\MPID-Latency-Tracking"
tar -czf mpid_latency_code.tar.gz *.py analysis/ mpid_latency/ scripts/ config.py requirements.txt

# SCP to VM (replace with actual VM address)
scp mpid_latency_code.tar.gz username@fintech-lab.university.edu:/home/username/

# On VM
ssh username@fintech-lab.university.edu
cd ~
tar -xzf mpid_latency_code.tar.gz
cd MPID-Latency-Tracking
```

### 2. Setup Python Environment on VM

```bash
# Create virtual environment (Python 3.9+)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install pandas pyarrow numpy matplotlib seaborn scipy
pip install jupyter ipython  # Optional for interactive work

# Verify installation
python -c "import pandas as pd; print(f'Pandas {pd.__version__}')"
python -c "import pyarrow as pa; print(f'PyArrow {pa.__version__}')"
```

### 3. Configure Paths for VM

Edit `config.py` to point to VM data directories:

```python
# config.py - Update these paths
ES_DATA_DIR = Path("/data/cme/es_trades")           # Update with actual VM path
NASDAQ_DATA_DIR = Path("/data/nasdaq/extracted")    # Update with actual VM path
OUTPUT_DIR = Path("/home/username/mpid_results")    # Your output location

# Increase worker count for beefy VM
NUM_WORKERS = 64  # Adjust based on VM core count

# Increase memory limit
MAX_MEMORY_MB = 128000  # 128GB if available
```

### 4. Test with Single Day

```bash
# Test pipeline with one day of data (update paths as needed)
python analysis/latency_join_pipeline.py \
    --es-trades /data/cme/trade_events_20250220_es_mes.parquet2 \
    --nasdaq-events /data/nasdaq/extracted/20250310/nasdaq_mpid_events_20250310_targets.parquet \
    --output results/test_latency_20250220.parquet \
    --trade-date 2025-02-20 \
    --min-trade-size 5

# Check output
python -c "import pandas as pd; df = pd.read_parquet('results/test_latency_20250220.parquet'); print(f'Rows: {len(df):,}'); print(df.head())"
```

### 5. Run Batch Processing for Multiple Months

```bash
# Process February 2025
python scripts/run_batch_latency.py \
    --start-date 20250201 \
    --end-date 20250228 \
    --workers 64

# Process multiple months
python scripts/run_batch_latency.py \
    --start-date 20250101 \
    --end-date 20250331 \
    --workers 64

# Monitor progress
tail -f logs/batch_run_*.log
```

## ⚡ Performance Optimization

### For Very Large Datasets (Multi-Month Processing)

1. **Use Parallel Processing**
   ```bash
   # Split by month and run in parallel
   python scripts/run_batch_latency.py --start-date 20250101 --end-date 20250131 --workers 32 &
   python scripts/run_batch_latency.py --start-date 20250201 --end-date 20250228 --workers 32 &
   wait
   ```

2. **Memory-Efficient Settings**
   ```python
   # In config.py
   CHUNK_SIZE = 5000  # Smaller chunks if memory constrained
   PARQUET_COMPRESSION = 'zstd'  # Better compression for storage
   PARQUET_COMPRESSION_LEVEL = 9
   ```

3. **Pre-filter NASDAQ Data**
   ```bash
   # On VM, pre-filter NASDAQ data to target symbols only
   python -c "
   import pandas as pd
   from pathlib import Path
   from config import TARGET_SYMBOLS
   
   for date_dir in Path('/data/nasdaq/extracted').glob('202*'):
       df = pd.concat([pd.read_parquet(f) for f in date_dir.glob('*.parquet')])
       df_filtered = df[df['symbol'].isin(TARGET_SYMBOLS)]
       output = date_dir / f'nasdaq_mpid_events_{date_dir.name}_targets.parquet'
       df_filtered.to_parquet(output, compression='snappy')
       print(f'Filtered {date_dir.name}: {len(df):,} -> {len(df_filtered):,}')
   "
   ```

## 🔍 Data Discovery on VM

### Find Available Data

```bash
# List ES trade data
find /data/cme -name "trade_events_*.parquet*" | head -20

# List NASDAQ data directories
ls -lh /data/nasdaq/extracted/

# Check data sizes
du -sh /data/cme/
du -sh /data/nasdaq/extracted/
```

### Verify Date Coverage

```python
# On VM Python shell
from pathlib import Path
import re

# ES dates
es_files = list(Path("/data/cme").glob("trade_events_*_es_mes.parquet*"))
es_dates = sorted({re.search(r'(\d{8})', f.name).group(1) for f in es_files})
print(f"ES data: {len(es_dates)} days from {es_dates[0]} to {es_dates[-1]}")

# NASDAQ dates
nasdaq_dates = sorted([d.name for d in Path("/data/nasdaq/extracted").glob("202*") if d.is_dir()])
print(f"NASDAQ data: {len(nasdaq_dates)} days from {nasdaq_dates[0]} to {nasdaq_dates[-1]}")

# Find intersection
common_dates = set(es_dates) & set(nasdaq_dates)
print(f"Common dates: {len(common_dates)}")
```

## 📊 Post-Processing on VM

### Combine Multi-Day Results

```bash
# Combine all daily results into one master file
python -c "
import pandas as pd
from pathlib import Path

results_dir = Path('results')
all_files = sorted(results_dir.glob('latency_results_*.parquet'))
print(f'Combining {len(all_files)} files...')

df_combined = pd.concat([pd.read_parquet(f) for f in all_files], ignore_index=True)
print(f'Total rows: {len(df_combined):,}')

output = results_dir / 'latency_results_all_dates.parquet'
df_combined.to_parquet(output, compression='zstd', compression_level=9)
print(f'Saved to {output} ({output.stat().st_size / 1e9:.2f} GB)')
"
```

### Generate Summary Statistics

```bash
# Quick stats on combined results
python -c "
import pandas as pd

df = pd.read_parquet('results/latency_results_all_dates.parquet')

print(f'\\nLatency Summary (microseconds):')
print(df['latency_us'].describe(percentiles=[.1, .25, .5, .75, .9, .95, .99]))

print(f'\\nTop 10 MPIDs by count:')
print(df['mpid'].value_counts().head(10))

print(f'\\nSymbol distribution:')
print(df['symbol'].value_counts())
"
```

## 💾 Download Results from VM

```bash
# Compress results for download
cd ~/mpid_results/results
tar -czf latency_results_final.tar.gz *.parquet

# From local machine
scp username@fintech-lab.university.edu:~/mpid_results/results/latency_results_final.tar.gz .

# Extract locally
tar -xzf latency_results_final.tar.gz
```

## 🐛 Troubleshooting

### Out of Memory Error
```python
# Reduce chunk size in config.py
CHUNK_SIZE = 2000

# Or process fewer dates at once
python scripts/run_batch_latency.py --start-date 20250201 --end-date 20250207 --workers 32
```

### Permission Denied
```bash
# Ensure output directory is writable
chmod -R 755 ~/mpid_results
mkdir -p ~/mpid_results/logs ~/mpid_results/results
```

### Module Not Found
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Verify PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Slow Performance
```bash
# Check VM load
htop  # or top

# Monitor disk I/O
iostat -x 5

# Use fewer workers if system is overloaded
python scripts/run_batch_latency.py --workers 16  # Instead of 64
```

## 📝 Best Practices

1. **Always test with 1 day first** before running multi-month batches
2. **Monitor disk space** - results can be large (100GB+ for months of data)
3. **Use screen/tmux** for long-running jobs to prevent disconnection
4. **Save logs** - they're invaluable for debugging
5. **Compress final results** before downloading from VM

## 🔗 Useful Commands

```bash
# Run in background with screen
screen -S latency_job
python scripts/run_batch_latency.py --start-date 20250101 --end-date 20250331 --workers 64
# Ctrl+A, then D to detach
# screen -r latency_job to reattach

# Check progress
watch -n 10 'ls -lh results/ | tail -20'

# Disk usage
df -h | grep data
du -sh results/

# Process count
ps aux | grep python | grep latency
```
