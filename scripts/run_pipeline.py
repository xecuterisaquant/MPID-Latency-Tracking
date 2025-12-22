"""Clean pipeline execution script - No interruptions"""
import subprocess
import sys
from pathlib import Path

# Set paths
es_dir = Path("data/es")
nasdaq_dir = Path("data/nasdaq")
output_dir = Path("data/output")

# Ensure output directory exists
output_dir.mkdir(parents=True, exist_ok=True)

# Build command
cmd = [
    sys.executable,
    "analysis/latency_pipeline_fast.py",
    "--es-dir", str(es_dir),
    "--nasdaq-dir", str(nasdaq_dir),
    "--output-dir", str(output_dir)
]

print("=" * 70)
print("RUNNING MULTI-DAY LATENCY PIPELINE")
print("=" * 70)
print(f"ES data: {es_dir}")
print(f"NASDAQ data: {nasdaq_dir}")
print(f"Output dir: {output_dir}")
print("=" * 70)
print("\nRunning pipeline... (this will take 15-20 minutes)")
print("Do not interrupt.\n")

# Run pipeline
result = subprocess.run(cmd, capture_output=False, text=True)

if result.returncode == 0:
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    # Check for output files
    output_files = list(output_dir.glob("latencies_*.parquet"))
    if output_files:
        total_size = sum(f.stat().st_size for f in output_files)
        print(f"Output files: {len(output_files)}")
        print(f"Total size: {total_size / (1024 * 1024):.2f} MB")
else:
    print("\n" + "=" * 70)
    print("PIPELINE FAILED")
    print("=" * 70)
    print(f"Exit code: {result.returncode}")
    sys.exit(result.returncode)
