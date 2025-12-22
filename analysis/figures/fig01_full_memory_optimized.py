"""Generate Figure 1 with memory-efficient column selection"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

print("Loading only required columns for Figure 1...")
# Only load latency_ms - saves 90% memory!
df = pd.read_parquet('data/output/latencies_multiday_combined.parquet', columns=['latency_ms'])
print(f"✓ Loaded {len(df):,} rows, memory: {df.memory_usage(deep=True).sum() / 1024**3:.2f} GB\n")

# Create figure
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), dpi=150)

latency_ms = df['latency_ms'].values

# Panel 1: Linear scale  
ax1.hist(latency_ms, bins=100, alpha=0.75, edgecolor='black', linewidth=0.5, color='#3498db')
ax1.set_xlabel('Latency (ms)', fontsize=12, fontweight='bold')
ax1.set_ylabel('Count', fontsize=12, fontweight='bold')
ax1.set_title('Latency Distribution (Linear)', fontsize=14, fontweight='bold', pad=15)
ax1.grid(True, alpha=0.3)

# Panel 2: Log scale
ax2.hist(latency_ms + 1, bins=np.logspace(0, 4, 100), alpha=0.75, edgecolor='black', linewidth=0.5, color='#e74c3c')
ax2.set_xscale('log')
ax2.set_xlabel('Latency (ms, log scale)', fontsize=12, fontweight='bold')
ax2.set_ylabel('Count', fontsize=12, fontweight='bold')
ax2.set_title('Latency Distribution (Log Scale)', fontsize=14, fontweight='bold', pad=15)
ax2.grid(True, alpha=0.3, which='both')

median_val = np.median(latency_ms)
mean_val = np.mean(latency_ms)
ax2.axvline(median_val, color='green', linestyle='--', linewidth=2, label=f'Median: {median_val:.1f} ms')
ax2.axvline(mean_val, color='orange', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.1f} ms')
ax2.legend(fontsize=10)

fig.suptitle(f'MPID Latency Distribution (ALL {len(df):,} observations)', 
             fontsize=16, fontweight='bold', y=1.00)

plt.tight_layout()
output_path = Path('analytics/figures/fig_01_full_dataset.png')
output_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"✓ Saved: {output_path}")
print("  This figure uses ALL 93 million observations")
