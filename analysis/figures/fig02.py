"""Figure 2: Firm Categories"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

print("Figure 2: Firm Categories")
print("-" * 40)

# Load and sample data (20M file is too large, sample to 500K)
print("Loading and sampling data...")
df_full = pd.read_parquet('data/output/latencies_sample_1M.parquet')
print(f"  Loaded {len(df_full):,} rows")
df = df_full.sample(n=500_000, random_state=42)
del df_full
print(f"  ✓ Sampled to: {len(df):,} rows")

# Load MPID category mapping
print("Mapping firm categories...")
cat_map = {}
with open('mpid_lookup/mpidlist.txt', 'r') as f:
    for line in f:
        if '|' in line:
            parts = line.strip().split('|')
            if len(parts) >= 3:
                cat_map[parts[0].strip()] = parts[2].strip()

# Map categories
df['category'] = df['mpid'].map(cat_map).fillna('Other')
print(f"  ✓ Categories: {list(df['category'].unique())}")

# Plot
print("Generating plot...")
sns.set_style("whitegrid")
fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
order = df.groupby('category')['latency_ms'].median().sort_values().index
sns.violinplot(data=df, x='latency_ms', y='category', order=order, palette='Set2', ax=ax)
ax.set_xlabel('Latency (ms)', fontsize=12, fontweight='bold')
ax.set_ylabel('Firm Category', fontsize=12, fontweight='bold')
ax.set_title(f'Latency by Firm Category (n={len(df):,})', fontsize=14, fontweight='bold')
ax.set_xlim(0, df['latency_ms'].quantile(0.95))
plt.tight_layout()

# Save
Path('analytics/figures').mkdir(parents=True, exist_ok=True)
output_path = 'analytics/figures/fig_02_firm_categories.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"  ✓ Saved: {output_path}")
