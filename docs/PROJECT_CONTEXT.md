# MPID Latency Tracking Project - Complete Context

**Date Generated:** December 22, 2025  
**Project Deadline:** Imminent (hours remaining)  
**Current Status:** Data Complete | Figures 2-9 Blocked

---

## 🎯 Project Overview

**Research Question:** How quickly do NASDAQ MPID-attributed liquidity providers react to CME E-mini S&P 500 futures trade events?

**Measurement:** Nanosecond-precision latency from ES trade timestamp to first subsequent NASDAQ MPID action (add/cancel/replace)

**Data Period:** March 10-21, 2025 (10 trading days)
- **Contracts:** ESH25 (March 2025), ESM25 (June 2025)
- **Symbols:** SPY, QQQ, IWM, AAPL, MSFT, GOOG, AMZN, META, NVDA, TSLA

---

## ✅ Completed Work

### 1. Data Processing Pipeline (SUCCESS)

**NASDAQ Preprocessing:**
- ✅ Processed 10 days of NASDAQ ITCH data
- ✅ Filtered to market hours (8:15 AM - 4:00 PM ET)
- ✅ Extracted MPID-attributed events only
- ✅ Output: 4.45 GB preprocessed data (~750M+ events)
- ✅ Location: `data/nasdaq/extracted_md/`
- ✅ Runtime: ~5-10 minutes per day

**Latency Pipeline:**
- ✅ Processed all 10 days × 2 contracts = 20 daily runs
- ✅ Generated **93,031,377 latency observations**
- ✅ Runtime: 9 minutes 24 seconds total
- ✅ Memory-efficient: Chunked processing, streaming joins
- ✅ Output: 20 daily parquet files + 1 combined file

**Data Validation:**
- ✅ Timestamp integrity verified
- ✅ All contracts and symbols present
- ✅ No missing days or data gaps
- ✅ Comprehensive statistics generated

### 2. Final Dataset Statistics

**File:** `outputs/latencies/latencies_multiday_combined.parquet`
- **Size on disk:** 1.45 GB
- **Size in RAM:** 15.68 GB (when fully loaded with all columns)
- **Observations:** 93,031,377
- **Contracts:** ESH25 (60.4M, 64.9%) | ESM25 (32.6M, 35.1%)
- **Columns:** 9 (es_trade_time_ns, mpid, symbol, event_type, latency_ns, nasdaq_time_ns, contract, date, latency_ms)

**Latency Statistics:**
- **Median:** 147.2 ms
- **Mean:** 625.8 ms
- **Min:** 0.001 ms
- **Max:** 49,999 ms
- **95th percentile:** 3,215 ms

**Market Participants:**
- **52 unique MPIDs** tracked
- **Top 3 firms account for 95.7% of activity:**
  - WBPX (Summit Securities Group): 33,376,802 obs (35.9%)
  - WCHV (Wolverine): 32,138,992 obs (34.5%)
  - JPMS (JP Morgan): 24,726,515 obs (26.6%)

**Symbols (10 total):**
- SPY, QQQ, IWM (index ETFs)
- AAPL, MSFT, GOOG, AMZN, META, NVDA, TSLA (mega-cap tech)

### 3. Figure 1 - Distribution (COMPLETE)

**File:** `outputs/figures/fig_01_full_dataset.png`
- ✅ Generated from full 93M dataset
- ✅ 2-panel plot: Linear scale + Log scale
- ✅ Memory-optimized: Loaded only `latency_ms` column (0.69 GB vs 15.68 GB)
- ✅ Professional seaborn styling
- ✅ Runtime: ~1 minute
- ✅ Resolution: 150 DPI, publication-quality

**Success Pattern:**
```python
df = pd.read_parquet('...', columns=['latency_ms'])  # Load ONLY needed column
# Fast numpy operations, no lookups, no function calls on 93M rows
```

---

## 🚨 CRITICAL BLOCKERS: Figures 2-9

### The Problem: Memory + Performance

**1. Memory Constraint (CRITICAL)**
- **System RAM:** 16 GB total
- **Dataset size:** 15.68 GB when fully loaded in memory
- **Issue:** Loading all columns exhausts RAM, causes thrashing/hanging
- **Workaround:** Column selection works (e.g., only `latency_ms` = 0.69 GB)

**2. MPID Lookup Performance (CRITICAL)**
- **Task:** Add firm names/categories to 93M rows
- **Method attempted:** `df['firm_name'] = df['mpid'].apply(get_firm_category)`
- **Issue:** Python function calls on 93M rows = 10+ minutes, often hangs
- **Workaround attempted:** Vectorized `.map()` with pre-loaded dicts → failed silently

**3. Sampling Complexity**
- **Problem:** "Sample-after-load" still loads full 15.68 GB dataset first
- **Solution attempted:** Load → sample → categorize → plot
- **Result:** Hung at categorization step even on samples

### Failed Attempts Log

**Attempt 1:** Load full dataset once, generate all figures
- **Result:** Out of memory

**Attempt 2:** Load columns per figure, delete dataframes between figures
- **Result:** Hung on MPID lookups (10+ minutes)

**Attempt 3:** Sample 200K rows, then categorize
- **Result:** Still hung on categorization

**Attempt 4:** Pre-load MPID mappings, vectorized `.map()`
- **Result:** Failed silently, no output, no errors

**Attempt 5:** Load pre-sampled 20M file, sample to 500K
- **Result:** Hung immediately, no logging output

**Common failure modes:**
- Scripts hang with no output
- No error messages
- Process appears stuck in I/O or computation
- Even print statements don't execute

### What Works vs What Doesn't

**✅ WORKS:**
- Loading specific columns only (`columns=['latency_ms']`)
- Direct numpy/pandas aggregations
- Simple matplotlib plots with no lookups
- Statistics on full dataset (no function calls per row)

**❌ DOESN'T WORK:**
- Loading full dataset (all columns)
- Applying Python functions to 93M rows
- Sample-after-load strategies
- Batch multi-figure generation

---

## 📋 Required Figures (Specifications)

### Figure 1: Distribution ✅ COMPLETE
- 2-panel histogram (linear + log scale)
- Full 93M dataset
- **Status:** Complete

### Figure 2: Latency by Firm Category ❌ BLOCKED
- **Type:** Violin plot
- **X-axis:** Latency (ms)
- **Y-axis:** Firm category (Market Maker, HFT, Prop Trading, Other)
- **Data needed:** mpid + latency_ms + firm category lookup
- **Blocker:** MPID categorization too slow

### Figure 3: Top 15 Firms ❌ BLOCKED
- **Type:** Box plot (horizontal)
- **X-axis:** Latency (ms)
- **Y-axis:** Firm name
- **Sorting:** By median latency
- **Data needed:** mpid + latency_ms + firm name lookup
- **Blocker:** MPID name lookup too slow

### Figure 4: Latency by Symbol ❌ BLOCKED
- **Type:** Violin plot
- **X-axis:** Symbol
- **Y-axis:** Latency (ms)
- **Symbols:** All 10 (SPY, QQQ, IWM, etc.)
- **Data needed:** symbol + latency_ms
- **Blocker:** None (data available), but hung in batch scripts

### Figure 5: Time of Day Pattern ❌ BLOCKED
- **Type:** Line plot with confidence interval
- **X-axis:** Hour of day (EST)
- **Y-axis:** Median latency
- **Data needed:** es_trade_time_ns + latency_ms
- **Blocker:** Need to extract hour from timestamp (93M rows)

### Figure 6: Firm Correlation ❌ BLOCKED
- **Type:** Heatmap (correlation matrix)
- **Data:** Top 10 MPIDs, latency correlations
- **Data needed:** mpid + es_trade_time_ns + latency_ms
- **Blocker:** Pivot table on 93M rows

### Figure 7: Symbol Correlation ❌ BLOCKED
- **Type:** Heatmap (correlation matrix)
- **Data:** All 10 symbols, latency correlations
- **Data needed:** symbol + es_trade_time_ns + latency_ms
- **Blocker:** Pivot table on 93M rows

### Figure 8: Weekly Heatmap ❌ BLOCKED
- **Type:** 2D heatmap (day × hour)
- **X-axis:** Hour of day
- **Y-axis:** Date
- **Color:** Median latency
- **Data needed:** date + hour + latency_ms
- **Blocker:** Groupby on 93M rows

### Figure 9: Contract Comparison ❌ BLOCKED
- **Type:** 2-panel plot (violin + area)
- **Panel 1:** ESH25 vs ESM25 distributions
- **Panel 2:** Rollover timeline (volume over time)
- **Data needed:** contract + date + latency_ms
- **Blocker:** None (data available), but hung in batch scripts

---

## 🛠️ Technical Environment

**System:**
- **OS:** Windows
- **RAM:** 16 GB (critical constraint)
- **Python:** 3.14.0
- **Environment:** `.venv` virtual environment

**Key Dependencies:**
```
pandas
numpy
matplotlib
seaborn
polars (group-by aggregation in the analytics layer: report stats + figure loading)
numba (JIT compilation for pipeline)
pyarrow (parquet backend)
```

**Data Locations:**
```
data/es/                          # ES futures trades (CSV/Parquet)
data/nasdaq/extracted/            # Raw NASDAQ ITCH (Parquet)
data/nasdaq/extracted_md/         # Preprocessed market-hours data
outputs/latencies/                # Latency results
  ├── latencies_multiday_combined.parquet  # 93M obs, 1.45 GB
  ├── latencies_20250310_ESH25.parquet     # Daily files
  └── ...
outputs/statistics/               # Statistics
  └── quick_summary.txt
outputs/figures/                  # Figures
  └── fig_01_full_dataset.png     # Only complete figure
```

**MPID Lookup File:**
```
mpid_lookup/mpidlist.txt          # 52 MPIDs with format:
                                  # MPID|Firm Name|Category
```

---

## 💡 Proposed Solutions (Not Yet Implemented)

### Option 1: Daily File Processing (RECOMMENDED)
**Strategy:** Process 20 daily files instead of combined 93M file

**Approach:**
```python
# For each of 20 daily files (~4-5M rows each):
for file in daily_files:
    df = pd.read_parquet(file)  # ~4M rows = manageable
    df['firm_category'] = df['mpid'].map(category_dict)  # Fast on 4M
    # Generate partial plot
# Combine plots or aggregate results
```

**Pros:**
- Each file ~70-100 MB in memory (vs 15.68 GB)
- MPID lookups fast on 4M rows (<1 second vs 10+ minutes)
- Can use full dataset precision

**Cons:**
- More complex plotting logic
- Need to combine results across files

### Option 2: Pre-compute Lookups in Pipeline (CLEANEST)
**Strategy:** Add firm_name and firm_category columns during pipeline run

**Approach:**
```python
# Modify run_pipeline.py to add:
df['firm_name'] = df['mpid'].map(mpid_to_firm)
df['firm_category'] = df['mpid'].map(mpid_to_category)
df['hour'] = pd.to_datetime(df['es_trade_time_ns'], unit='ns').dt.hour
# Save enriched dataset
```

**Pros:**
- One-time cost (~10 minutes to re-run pipeline)
- All future analysis is fast
- No lookup performance issues

**Cons:**
- Need to re-run pipeline (but only takes 9min 24sec)
- Slightly larger output files

### Option 3: Stratified Sampling (USER APPROVED)
**Strategy:** Sample 500K-1M rows stratified by contract/symbol

**Approach:**
```python
# Load full dataset
df = pd.read_parquet('...')
# Stratified sample
df_sample = df.groupby(['contract', 'symbol']).sample(frac=sample_frac)
# Add lookups (fast on 1M rows)
df_sample['firm_category'] = df_sample['mpid'].map(category_dict)
# Generate all figures from sample
```

**Pros:**
- Industry-standard approach for visualization
- Fast execution (2-3 minutes total)
- All patterns preserved in sample

**Cons:**
- User initially resistant (accuracy concerns)
- Not "full dataset" (but 1M is statistically sound)

**Current Status:** User approved sampling, but current sampled file is 20M rows (too large)

### Option 4: Polars Backend (IMPLEMENTED in the analytics layer)
**Strategy:** Use Polars for parquet loading and group-by aggregation instead of pandas

**Approach:**
```python
import polars as pl
# Stats layer: LAZY scan -> projection pushdown reads only needed columns
scan = pl.scan_parquet('...')
scan.group_by('mpid').agg(pl.col('latency_ms').median()).collect()  # PROJECT 2/N cols
# Figure layer: eager load, convert at the Seaborn boundary
df = pl.read_parquet('...').to_pandas()
```

**Where it's used:**
- `scripts/extract_report_stats.py` — every report table (overall, per-MPID, hour,
  symbol, event-type, firm category, contract, top firms) is a **lazy** Polars query
  (`scan_parquet`), so each table only reads the columns it needs off disk
- `analysis/run_all_analytics.py` — eagerly loads the latencies parquet with Polars,
  then hands a pandas frame to the Seaborn figure generators

**Pros:**
- Lazy projection pushdown avoids materializing the full ~93M-row frame in the stats layer
- Faster, Arrow-backed multithreaded group-by/aggregation vs pandas
- Quantile interpolation set to 'linear' so results match the original numbers exactly

**Note:** Seaborn requires pandas, so the figure path stays eager and converts with
`.to_pandas()` at the plotting step (the documented turbo-mode pattern). Lazy
evaluation applies to the report-stats layer, not figure rendering.

---

## 📁 File Structure

### Core Pipeline Files (WORKING)
```
run_pipeline.py                   # Main orchestrator (WORKS)
batch_preprocess.py               # NASDAQ preprocessing (WORKS)
combine_outputs.py                # Combine daily files (WORKS)
quick_stats.py                    # Statistics generator (WORKS)
analysis/
  ├── latency_pipeline_multiday.py   # Core pipeline (WORKS)
  └── preprocess_nasdaq.py           # NASDAQ filter (WORKS)
mpid_latency/
  ├── ingest.py                      # ES data loader (WORKS)
  ├── parser.py                      # ITCH parser (WORKS)
  └── messages.py                    # Message structures (WORKS)
```

### Figure Generation (PARTIALLY WORKING)
```
fig01_full_memory_optimized.py    # ✅ WORKS (template for success)
fig02.py                           # ❌ HUNG (needs fix)

# Deleted gibberish files:
# - fig02_firm_categories.py
# - generate_all_figures.py
# - generate_all_figures_TURBO.py
# - generate_figures_FINAL.py
# - create_sample_for_figures.py
# - make_1m_sample.py
```

### Outputs (CURRENT STATE)
```
outputs/
  ├── latencies/
  │   ├── latencies_multiday_combined.parquet  # 93M obs, 1.45 GB ✅
  │   ├── latencies_sample_1M.parquet          # 20M sample (TOO LARGE)
  │   └── latencies_YYYYMMDD_*.parquet         # 20 daily files ✅
  ├── statistics/
  │   └── quick_summary.txt                    # Comprehensive stats ✅
  └── figures/
      └── fig_01_full_dataset.png              # Distribution ✅
```

---

## 🎯 Immediate Next Steps (Recommended Approach)

### Step 1: Create Proper 1M Sample (5 minutes)
```python
# Load 20M sample, resample to 1M
df = pd.read_parquet('outputs/latencies/latencies_sample_1M.parquet')
df_1m = df.groupby('contract', group_keys=False).apply(
    lambda x: x.sample(n=min(len(x), 500000), random_state=42)
).reset_index(drop=True)
df_1m.to_parquet('outputs/latencies/latencies_1M_proper.parquet')
```

### Step 2: Create Individual Figure Scripts (10 minutes)
- Use `fig01_full_memory_optimized.py` as template
- Each script:
  1. Load proper 1M sample
  2. Add needed lookups (fast on 1M rows)
  3. Generate one figure
  4. Save and exit

### Step 3: Run Each Figure Sequentially (10 minutes total)
```bash
python fig02.py  # Firm categories
python fig03.py  # Top firms
python fig04.py  # Symbols
python fig05.py  # Time of day
python fig06.py  # Firm correlation
python fig07.py  # Symbol correlation
python fig08.py  # Weekly heatmap
python fig09.py  # Contract comparison
```

### Total Time: ~25 minutes (achievable before deadline)

---

## 🔍 Key Insights for New Chat

### What We Learned

1. **Memory is the bottleneck:** 15.68 GB dataset vs 16 GB RAM = disaster
2. **Column selection is critical:** Loading only needed columns reduces memory by 95%
3. **Function calls are slow:** `.apply()` on 93M rows = 10+ minutes
4. **Vectorized operations work:** `.map()` with pre-loaded dicts (when working)
5. **Sampling is necessary:** 1M stratified sample is industry standard and statistically sound
6. **Simple is better:** Individual scripts > complex batch processing
7. **The 20M "sample" is not a sample:** It's still too large (3.3 GB in RAM)

### What NOT to Do

❌ Don't load full dataset with all columns  
❌ Don't use `.apply()` with Python functions on 93M rows  
❌ Don't try to generate all figures in one script  
❌ Don't sample-after-load (sample DURING load)  
❌ Don't overthink - follow the fig01 pattern

### What TO Do

✅ Load specific columns only  
✅ Use vectorized operations (`.map()` with dicts)  
✅ Create individual figure scripts  
✅ Use proper 1M stratified sample  
✅ Follow fig01_full_memory_optimized.py pattern  
✅ Test each script independently

---

## 📊 Current Dataset Details

### Contracts
- **ESH25:** 60,428,850 obs (64.9%) - March 2025 contract
- **ESM25:** 32,602,527 obs (35.1%) - June 2025 contract
- **Rollover visible:** ESM25 volume increases over time period

### Top MPIDs (52 total)
| MPID | Firm | Category | Observations | % |
|------|------|----------|--------------|---|
| WBPX | Summit Securities Group | Market Maker | 33,376,802 | 35.9% |
| WCHV | Wolverine Trading | Market Maker | 32,138,992 | 34.5% |
| JPMS | JP Morgan Securities | Market Maker | 24,726,515 | 26.6% |
| JPMX | JP Morgan Execution | Market Maker | 1,440,918 | 1.5% |
| JANE | Jane Street | Market Maker | 537,012 | 0.6% |
| GTCO | Getco (KCG) | Market Maker | 251,734 | 0.3% |
| NITE | Virtu Americas | Market Maker | 178,653 | 0.2% |
| Others (45 firms) | Various | Various | 381,751 | 0.4% |

### Symbols (10 total)
- **ETFs:** SPY, QQQ, IWM
- **Tech:** AAPL, MSFT, GOOG, AMZN, META, NVDA, TSLA

### Event Types
- Add orders (MPID-attributed)
- Replace orders
- Cancel orders

---

## 🚀 Success Criteria

### For Project Completion
✅ Dataset: 93M observations generated and validated  
✅ Statistics: Comprehensive analysis complete  
❌ Figures: 1/9 complete (need 8 more)  
❌ Report: Draft exists but needs figure references  

### For Deadline
**MINIMUM VIABLE:**
- ✅ Figure 1: Distribution (complete)
- ⚠️ Figures 2-5: Core analysis (CRITICAL)
- ⚠️ Figures 6-9: Advanced analysis (NICE TO HAVE)
- ✅ Statistics: Complete
- ⚠️ Report: Update with actual results

**IDEAL:**
- All 9 figures complete
- Report fully updated with figure references
- Presentation-ready visualizations

---

## 📝 Notes for Next Session

**User Frustration Level:** HIGH
- Multiple failed attempts over 30+ minutes
- Stuck in optimization loop
- Deadline pressure

**User Preferences:**
- ✅ Approved sampling strategy
- ✅ Wants simple, working solutions
- ✅ Professional seaborn styling required
- ❌ Don't overcomplicate
- ❌ Stop getting stuck in loops

**Critical Success Pattern (from fig01):**
```python
# 1. Load ONLY needed columns
df = pd.read_parquet('...', columns=['latency_ms'])

# 2. Simple numpy/pandas operations (no function calls)
hist_data = df['latency_ms'].values

# 3. Direct plotting
plt.hist(hist_data, bins=100)

# 4. Save and exit
plt.savefig('output.png')
```

**Avoid:**
- Complex multi-stage processing
- Function calls on full dataset
- Loading all columns
- Batch processing multiple figures

**Remember:**
- User wants results, not explanations
- Simple solutions beat complex optimizations
- Individual scripts > monolithic generators
- Follow what works (fig01 pattern)

---

## 🔗 Key Files for Reference

**Working Template:**
- `fig01_full_memory_optimized.py` - COPY THIS PATTERN

**Data Files:**
- `outputs/latencies/latencies_multiday_combined.parquet` - Full dataset
- `outputs/latencies/latencies_20250310_ESH25.parquet` (and 19 others) - Daily files

**Lookup Files:**
- `mpid_lookup/mpidlist.txt` - MPID → Firm name + Category

**Documentation:**
- `README.md` - Updated with current status
- `reports/report.md` - Academic manuscript
- `PROJECT_CONTEXT.md` - This file

---

**End of Context Document**

Last Updated: December 22, 2025  
Status: Ready for new chat session with complete project context
