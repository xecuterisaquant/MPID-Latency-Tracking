"""
Batch Preprocessing - All Remaining Days
Processes days 2-10 (2025-03-11 to 2025-03-21)
"""
from pathlib import Path
from datetime import date, timedelta
import subprocess
import sys

# Days to process (excluding weekends)
start_date = date(2025, 3, 11)
end_date = date(2025, 3, 21)

dates_to_process = []
current = start_date
while current <= end_date:
    if current.weekday() < 5:  # Monday=0, Friday=4
        dates_to_process.append(current)
    current += timedelta(days=1)

print("="*70)
print("BATCH NASDAQ PREPROCESSING")
print("="*70)
print(f"Processing {len(dates_to_process)} days: {dates_to_process[0]} to {dates_to_process[-1]}")
print(f"Estimated time: {len(dates_to_process) * 2} minutes")
print("="*70)

for i, trade_date in enumerate(dates_to_process, 1):
    print(f"\n[{i}/{len(dates_to_process)}] Processing {trade_date}...")
    
    cmd = [
        sys.executable,
        "analysis/preprocess_nasdaq.py",
        "--date", trade_date.strftime("%Y-%m-%d")
    ]
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode != 0:
        print(f"❌ FAILED: {trade_date}")
    else:
        print(f"✅ COMPLETE: {trade_date}")

print("\n" + "="*70)
print("BATCH PREPROCESSING COMPLETE")
print("="*70)
