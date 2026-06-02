# NASDAQ Data Analysis Summary

## Dataset Overview
- **Date:** March 10, 2025
- **Total Events:** 144,413,922
- **Time Coverage:** ~10 hours (full trading day + extended hours)
- **Unique MPIDs:** 87
- **Unique Symbols:** 11,235

## Target Symbols Dataset
**Saved to:** `data/nasdaq_mpid_events_20250310_targets.parquet`
**Size:** 239.37 MB
**Events:** 30,676,405

### Symbol Breakdown:
| Symbol | Events | % of Total |
|--------|--------|------------|
| QQQ | 8,849,113 | 6.13% |
| SPY | 4,985,063 | 3.45% |
| NVDA | 3,368,530 | 2.33% |
| AAPL | 3,041,194 | 2.11% |
| AMZN | 2,553,778 | 1.77% |
| IWM | 2,279,501 | 1.58% |
| TSLA | 2,092,845 | 1.45% |
| GOOGL | 2,009,516 | 1.39% |
| MSFT | 1,199,117 | 0.83% |
| META | 297,748 | 0.21% |

### Message Type Distribution:
- **Replace (U):** 30,580,087 (99.69%)
- **AddOrderMPID (F):** 61,753 (0.20%)
- **Delete (D):** 34,564 (0.11%)
- **Cancel (X):** 1 (0.00%)

### Top MPIDs in Target Symbols:
1. WBPX - Summit Securities Group (59.20%)
2. JPMS - JPMorgan (23.70%)
3. WCHV - Wolverine Trading (14.43%)
4. VIRT - Virtu Financial (0.93%)
5. GSCO - Goldman Sachs (0.29%)
... 51 total MPIDs

## Data Schema:
```
event_time_ns: int64    # Timestamp in nanoseconds
mpid: string            # Market Participant ID (4 chars)
symbol: string          # Stock ticker
side: string            # B (Buy) or S (Sell)
price: int64            # Price (needs scaling - likely 1/10000 units)
size: int64             # Share quantity
message_type: string    # AddOrderMPID, Replace, Delete, Cancel
```

## Timestamp Issue:
The `event_time_ns` values appear to be nanoseconds but NOT Unix epoch:
- Raw range: 25.5 trillion to 61.0 trillion
- Likely interpretation: **nanoseconds since midnight of trade date**
- Need to add date offset: `2025-03-10 00:00:00` + event_time_ns

## Next Steps:
1. ✅ NASDAQ data ready
2. ⏳ Get CME ES trade data from Chintan
3. ⏳ Build latency join pipeline
4. ⏳ Generate analytics and figures
