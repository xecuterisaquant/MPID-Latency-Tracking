# MPID Latency Tracking - Cross-Market Response Times

**Measuring high-frequency liquidity provider reaction latencies from ES futures trades to NASDAQ order updates**

### Team Members
- Harsh, Ivaylo, Chintan

---

## Executive Summary

This project measures how fast NASDAQ market makers react to CME E-mini S&P 500 (ES) futures trades. We track 12.25 million latency observations from March 10, 2025 (7.74 hours of trading), revealing extreme market concentration and surprising differences in firm behavior.

**Key Findings:**
- **95.7% of activity** dominated by just 3 firms (Wolverine, Wedbush, JP Morgan)
- **~96ms median latency** for active market makers (Chicago → NASDAQ full pipeline)
- **26x symbol variation**: QQQ at 35.6ms vs META at 929ms median
- "Famous HFT firms" (Citadel, Virtu, IMC) barely participate - sporadic 4+ second latencies

---

## Quick Start

```bash
# Install dependencies
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Run latency analysis
python analysis/latency_join_pipeline.py --trade-date 2025-03-10

# Generate analytics
python analysis/generate_analytics_seaborn.py --results data/output/latencies.parquet --output data/output/analytics
```

**Results:** `data/output/analytics/` (8 publication-quality figures + tables + interpretation)

---

## Repository Structure

```
MPID-Latency-Tracking/
├── analysis/               # Analytics pipeline
│   ├── latency_join_pipeline.py    # Main processing (ES → NASDAQ matching)
│   └── generate_analytics_seaborn.py   # Visualization generation
├── mpid_latency/          # Core matching engine
│   ├── ingest.py          # ES futures data loading
│   ├── parser.py          # NASDAQ ITCH parser
│   └── messages.py        # Binary message structures
├── mpid_lookup/           # Firm categorization
│   ├── mpid_to_firm.py    # MPID → firm name mapping
│   └── mpidlist.txt       # MPID registry
├── data/
│   ├── itch/              # ES futures trades (CSV)
│   ├── pcap/              # NASDAQ ITCH data (PCAP)
│   └── output/
│       ├── latencies.parquet         # Final results (12.25M rows)
│       └── analytics/                # Figures + tables
├── tests/                 # Test suite
└── README.md
```

---

## Methodology

### Data Sources
1. **ES Futures Trades** (CME Chicago)
   - Source: QuantConnect/LEAN ES data
   - Coverage: March 10, 2025, 6:00 AM - 4:39 PM ET
   - Format: CSV with nanosecond timestamps
   
2. **NASDAQ ITCH Events** (NASDAQ Carteret, NJ)
   - Source: NASDAQ TotalView-ITCH 5.0 PCAP files
   - Coverage: March 10, 2025, 8:15 AM - 4:00 PM ET
   - Events: AddOrderMPID, Replace, Delete (with MPID attribution)

### Latency Calculation
```
Latency = NASDAQ_event_timestamp - ES_trade_timestamp
```

**Key Challenge Solved:** ES timestamps were UTC-encoded but represented EDT times. Applied +4 hour offset to align with NASDAQ's EDT-based system. Final overlap: 8:15 AM - 4:00 PM ET (7.74 hours).

### Matching Algorithm
- Binary search on sorted NASDAQ events within 10-second window
- Filters: same symbol, event after ES trade
- Deduplication: First matching event per (ES trade, MPID, symbol)
- Result: 12,252,369 latency measurements across 51 MPIDs, 10 symbols

---

## Key Results

### 1. Market Concentration (Top 3 = 95.7%)
| Firm | Count | Median Latency | % of Total |
|------|-------|----------------|------------|
| Wedbush Securities | 4.24M | 96.3 ms | 34.6% |
| Wolverine Trading | 4.16M | 95.9 ms | 34.0% |
| JP Morgan Securities | 3.32M | 97.3 ms | 27.1% |

### 2. Firm Category Performance
- **Active Fast Market Makers**: 96.4ms median (11.72M obs)
- **Sporadic/Slow HFT**: 4,578ms median (391K obs) - **48x slower**
- **Traditional Brokers**: 3,943ms median (124K obs)

### 3. Symbol-Level Variation (26x difference)
- **Fastest**: QQQ at 35.6ms median
- **Slowest**: META at 929ms median
- Active MMs focus on high-liquidity names (SPY, QQQ, IWM)

### 4. Statistical Validation
- Kruskal-Wallis tests: All p < 0.001
- Effect sizes: MPID explains 10.3% variance (medium-large)
- Temporal clustering present (95% obs within 1s) but doesn't invalidate findings
- Results robust across sample sizes (10K - 12M observations)

---

## Technical Details

### Timestamp Handling
**Critical Fix:** ES data timestamps were Unix epoch values in UTC encoding but represented EDT times. Added 4-hour offset:
```python
EDT_OFFSET_NS = 4 * 3600 * 1_000_000_000
df['trade_time_ns'] = df['trade_time_ns'] + EDT_OFFSET_NS
```
Validated with comprehensive sanity checks (9/9 passed).

### Performance Optimizations
- Numba JIT compilation for binary search (100x speedup)
- Parquet format for compressed storage
- Chunked processing for memory efficiency

### Data Quality
- ✅ No negative latencies
- ✅ No zero latencies  
- ✅ All latencies < 10 seconds (matching window)
- ✅ 48.8% under 100ms (physically reasonable)

---

## Figures & Analytics

Generated in `data/output/analytics/`:

1. **latency_distribution.png** - Overall histogram + log-scale view
2. **firm_category_analysis.png** - Boxplots + KDE overlays by category
3. **latency_by_firm.png** - Violin plots for top 12 firms
4. **latency_by_mpid.png** - Top 15 MPIDs (color-coded by category)
5. **latency_by_symbol.png** - Symbol comparison with volume
6. **latency_time_of_day.png** - Hourly patterns + activity volume
7. **event_type_analysis.png** - Replace (95%) vs Add (4%) vs Delete (1%)

**Tables:** Summary statistics, firm breakdowns, statistical test results

---

## Running the Analysis

### Prerequisites
- Python 3.10+
- 16GB+ RAM recommended
- Windows/Linux/Mac

### Installation
```bash
git clone <repo-url>
cd MPID-Latency-Tracking
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Full Pipeline
```bash
# 1. Process ES → NASDAQ latencies
python analysis/latency_join_pipeline.py \
    --trade-date 2025-03-10 \
    --es-data data/itch/ \
    --nasdaq-pcap data/pcap/ \
    --output data/output/latencies.parquet

# 2. Generate analytics
python analysis/generate_analytics_seaborn.py \
    --results data/output/latencies.parquet \
    --output data/output/analytics

# 3. Validate statistics
python validate_statistical_tests.py
```

### Testing
```bash
pytest tests/ -v
```

---

## Findings & Implications

### For Market Structure
- Extreme concentration: 3 firms control 95.7% of MPID-attributed liquidity
- Barrier to entry is high: requires sub-100ms cross-market infrastructure
- Market resilience depends on continued participation of top 3

### For Trading
- 96ms represents competitive performance (network + processing + logging)
- Symbol selection matters: 26x latency difference based on focus
- "Famous HFT firms" may be focused elsewhere (options, other venues, different strategies)

### For Regulation
- Speed bumps >100ms could disadvantage legitimate market makers
- MPID attribution enables transparency into liquidity provision patterns
- Concentration risk: 95.7% from 3 firms is potential systemic concern

---

## Literature & References

**Market Microstructure:**
- Hasbrouck & Saar (2013) - Low-latency trading
- Brogaard et al. (2014) - High-frequency trading and price discovery
- Baron et al. (2019) - Risk and return in high-frequency trading

**Cross-Market Latency:**
- Menkveld (2013) - High-frequency trading and the new market makers
- Laughlin et al. (2014) - The Flash Crash: High-frequency trading in an electronic market

**Data Specifications:**
- NASDAQ TotalView-ITCH 5.0 Specification
- CME Group Market Data Platform

---

## Known Limitations

1. **Single trading day**: March 10, 2025 only (7.74 hours)
2. **Temporal clustering**: 95% of observations within 1s violates independence assumption
3. **Causality assumption**: First matching NASDAQ event may not be causal response
4. **Symbol selection**: 10 symbols (SPY, QQQ, IWM, FAANG+) - not comprehensive
5. **MPID coverage**: Only MPID-attributed events (excludes anonymous liquidity)

---

## Future Work

- [ ] Multi-day analysis for robustness
- [ ] Mixed-effects models to account for temporal clustering  
- [ ] Granger causality tests for causal validation
- [ ] Expand to full symbol universe
- [ ] Compare to options market latencies
- [ ] Analyze during high-volatility events (FOMC, earnings)

---

## Citation

```bibtex
@misc{harsh2025mpidlatency,
  title={Cross-Market MPID Latency Tracking: ES Futures to NASDAQ Equity Responses},
  author={Harsh and Ivaylo and Chintan},
  year={2025},
  month={March},
  note={FIN 556 - Algorithmic Market Microstructure, UIUC}
}
```

---

## License

Academic use only. Data sources subject to respective provider terms of service.

---

## Contact

For questions: See course GitLab or contact team members via UIUC email.
