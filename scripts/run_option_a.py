"""
MASTER EXECUTION SCRIPT - OPTION A FAST TRACK
Runs full pipeline → combines → analytics → figures
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_step(step_num, total_steps, name, command, estimated_mins):
    """Run a command and track timing"""
    print("\n" + "="*70)
    print(f"STEP {step_num}/{total_steps}: {name}")
    print(f"Estimated time: {estimated_mins} minutes")
    print("="*70)
    
    start = datetime.now()
    result = subprocess.run(command, shell=False)
    elapsed = (datetime.now() - start).total_seconds() / 60
    
    if result.returncode != 0:
        print(f"\n❌ FAILED: {name}")
        return False
    
    print(f"\n✅ COMPLETE: {name} (took {elapsed:.1f} minutes)")
    return True

# Main execution
print("="*70)
print("OPTION A: FAST TRACK TO PUBLICATION")
print("="*70)
print("Full pipeline execution:")
print("  1. Multi-day pipeline (10 days × 2 contracts)")
print("  2. Combine all outputs")
print("  3. Statistical analysis")
print("  4. Generate all figures")
print("="*70)

start_time = datetime.now()

# Step 1: Run full 10-day pipeline
if not run_step(1, 4, "Multi-Day Pipeline (10 days)", 
               [sys.executable, "run_pipeline.py"], 25):
    sys.exit(1)

# Step 2: Combine outputs
if not run_step(2, 4, "Combine Outputs",
               [sys.executable, "combine_outputs.py"], 5):
    sys.exit(1)

# Step 3: Statistical analysis
if not run_step(3, 4, "Comprehensive Statistics",
               [sys.executable, "analysis/stats/comprehensive_stats.py",
                "--data", "data/output/latencies_multiday_combined.parquet",
                "--output", "data/output/analytics/tables"], 10):
    sys.exit(1)

# Step 4: Generate all figures
if not run_step(4, 4, "Generate All Figures",
               [sys.executable, "analysis/run_all_analytics.py",
                "--data", "data/output/latencies_multiday_combined.parquet",
                "--output", "data/output/analytics/figures",
                "--skip-stats"], 10):
    sys.exit(1)

# Final summary
total_time = (datetime.now() - start_time).total_seconds() / 60
print("\n" + "="*70)
print("🎉 OPTION A COMPLETE!")
print("="*70)
print(f"Total execution time: {total_time:.1f} minutes")
print("\nOutputs:")
print("  Combined data: data/output/latencies_multiday_combined.parquet")
print("  Statistics: data/output/analytics/tables/")
print("  Figures: data/output/analytics/figures/ (9 figures)")
print("="*70)
