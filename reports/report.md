# High-Frequency Liquidity Provider Response Latency to External Price Shocks: An Empirical Analysis of MPID-Attributed Market Participants on NASDAQ

**Authors:** Harsh Hari, Ivaylo Maksimov, Chintan Vajariya 
**Date:** December 22, 2025  
**Course:** FIN556 Market Microstructure  

---

## Abstract

This study measures the reaction time of NASDAQ market participants, as proxied by Market Participant Identifiers (MPIDs), to external price shocks originating from CME E-mini S&P 500 futures (ES) trades. We define a stimulus as an ES trade event (LastTradeMsg) and a response as the first subsequent add, cancel, or replace action associated with a given MPID on NASDAQ XNAS. Using nanosecond-precision timestamps from market data feeds, we compute MPID-level latency distributions and examine temporal patterns across trading hours and days. Our findings provide empirical evidence on [TBD: key finding placeholder] with median latencies of [TBD] and significant heterogeneity across market participants. We document important limitations including potential clock misalignment between venues, incomplete MPID attribution, and challenges in establishing causal links between stimulus and response events.

## Acknowledgments

The authors thank **Professor David Lariviere** for his guidance and feedback throughout the development of this project. We also thank **Gustaf Soederlind** for providing his **CME MDP 3.0 parser**, which enabled the construction and processing of the ES trade event data used in this analysis.


**Keywords:** High-frequency trading, market microstructure, latency measurement, MPID, liquidity provision, cross-market arbitrage

---

## 1. Introduction

### 1.1 Motivation

The speed at which market participants react to price signals has become a defining characteristic of modern financial markets. Liquidity providers on equity exchanges face continuous pressure to update quotes in response to information from correlated assets, particularly equity index futures. Understanding the magnitude and distribution of these reaction times is essential for:

1. **Market structure policy**: Evaluating the effectiveness of speed bumps and latency-based regulations
2. **Trading strategy design**: Benchmarking proprietary trading systems against market participants
3. **Risk management**: Quantifying adverse selection risk from stale quotes during fast-moving markets
4. **Academic research**: Providing empirical evidence on information transmission across markets

### 1.2 Research Question

**How quickly do NASDAQ MPID-attributed liquidity providers react (via add/cancel/replace actions) to external price shocks, using CME ES trade events as the stimulus?**

This question is operationalized through precise measurement of the time interval between ES trade timestamps and the first subsequent MPID action on NASDAQ, aggregated by market participant, symbol, and time of day.

### 1.3 Contribution

This study makes the following contributions to the market microstructure literature:

- **Direct latency measurement**: We measure actual reaction times at nanosecond precision rather than inferring speed from proxy variables
- **MPID-level granularity**: Unlike aggregate market studies, we decompose latencies by individual market participants
- **Cross-venue analysis**: We link stimuli from futures markets to responses in equity markets, capturing cross-asset arbitrage dynamics
- **Temporal heterogeneity**: We document how reaction times vary across trading hours and days, revealing capacity constraints and strategic timing

### 1.4 Structure

The remainder of this paper is organized as follows. Section 2 reviews related literature. Section 3 describes our data sources and schemas. Section 4 presents our methodology with precise definitions of stimulus, response, and latency metrics. Section 5 presents results. Section 6 discusses interpretations and limitations. Section 7 concludes.

---

## 2. Literature Review

### 2.1 High-Frequency Trading and Latency

The role of speed in modern markets has been extensively studied. Hasbrouck and Saar (2013) demonstrate that low-latency traders contribute to price discovery and liquidity. Brogaard et al. (2014) show that high-frequency traders (HFTs) impose adverse selection costs on slower participants. Our work extends this literature by providing direct latency measurements at the MPID level.

Menkveld (2013) examines the role of a single high-frequency market maker and documents quote adjustments within milliseconds of price changes. We expand this analysis to multiple participants and use cross-venue stimuli.

### 2.2 Cross-Market Information Transmission

The informational link between equity index futures and constituent stocks is well-established (Hasbrouck 2003; Hendershott and Moulton 2011). ES futures often lead equity indices due to lower transaction costs and higher leverage. Our study operationalizes this lead-lag relationship through explicit latency measurement.

Chordia et al. (2011) document cross-market liquidity provision patterns. We extend this work by measuring the speed of liquidity adjustment rather than just occurrence.

### 2.3 MPID Attribution and Market Transparency

Market Participant Identifiers provide transparency into which firms provide liquidity on NASDAQ. Comerton-Forde and Putniņš (2015) examine the effects of anonymity on market quality. Our use of MPID attribution allows participant-level analysis while recognizing that attribution coverage is incomplete.

---

## 3. Data

### 3.1 Data Sources

Our analysis relies on two primary data sources:

#### 3.1.1 CME E-mini S&P 500 Futures (ES)

**Source:** CME MDP 3.0 (Market Data Platform) feed  
**Format:** PCAP files containing binary market data messages  
**Timestamp precision:** Nanoseconds (sending time from CME Globex matching engine)  
**Collection period:** March 10th, 2025 - March 21st, 2025
**Message types used:** LastTradeMsg (trade executions only)  

**Schema (relevant fields):**
```
- timestamp_ns: int64 (nanosecond epoch time)
- security_id: int32 (CME instrument ID)
- trade_price: float64 (execution price)
- trade_quantity: int32 (contracts traded)
- aggressor_side: enum (buy/sell)
- trade_id: int64 (unique trade identifier)
```

**Rationale for ES trades as stimulus:**  
ES futures are the most liquid equity index derivative globally, with trade latencies often predicting equity market movements. Trade events (not quotes) represent actual price discovery events where information is revealed through executed transactions. We use only LastTradeMsg to avoid double-counting and to focus on realized transactions.

#### 3.1.2 NASDAQ XNAS Order Book Events

**Source:** NASDAQ TotalView-ITCH 5.0 feed  
**Format:** PCAP files with ITCH binary protocol messages  
**Timestamp precision:** Nanoseconds (NASDAQ gateway timestamp)  
**Collection period:** March 10th, 2025 - March 21st, 2025  
**Message types used:**
- Add Order MPID (F message): New limit order (MPID-attributed)
- Order Cancel (X message): Partial order cancellation
- Order Replace (U message): Price/size modification
- Order Delete (D message): Full order cancellation

**Schema (relevant fields):**
```
- timestamp_ns: int64 (nanosecond epoch time)
- mpid: string(4) (Market Participant ID, e.g., "NITE", "ARCA")
- stock_symbol: string (ticker symbol)
- order_reference: int64 (unique order ID)
- side: enum (buy/sell)
- price: int32 (price in 1/10000 units)
- shares: int32 (share quantity)
- message_type: string ("AddOrderMPID", "Cancel", "Replace", "Delete")
```

**MPID Attribution:**  
NASDAQ assigns 4-character MPIDs to registered market participants. Attribution is **voluntary** and incomplete—many orders are submitted without MPID identifiers. Moreover, individual firms may have several distinct MPIDs assigned to them. Our analysis is restricted to the subset of orders where MPID is populated, which introduces potential selection bias (discussed in Section 6.2).

### 3.2 Data Processing Pipeline

**File Locations:**
- Raw PCAP files: Stored on the course-provided virtual machine 
- Extracted messages: ITCH/MDP messages parsed directly on the VM (processed via `message_extraction/message_extraction.py`)
- Parsed data: Stored locally in Parquet format

**Processing Steps:**
1. **PCAP parsing:** Extract UDP packets containing ITCH/MDP messages using `dpkt` or `scapy`
2. **Message deserialization:** Decode binary message structures per protocol specification
3. **Timestamp extraction:** Convert binary timestamp fields to int64 nanosecond epoch times
4. **MPID filtering:** Retain only NASDAQ messages with non-null MPID fields
5. **Symbol filtering:** Restrict to top N symbols by message volume (scope control)

**Data Volume:**
- ES trades per day: [TBD] (estimate ~50,000-100,000 for liquid hours)
- NASDAQ MPID messages per day: [TBD] (estimate ~millions for top symbols)
- Total dataset size: [TBD GB]

### 3.3 Symbol Selection

To ensure statistical power while limiting computational burden, we focus on highly liquid symbols with strong correlation to ES futures:

**Target symbols (preliminary):**
- **QQQ:** Invesco QQQ Trust (NASDAQ-100 ETF) — direct index exposure
- **IWM:** iShares Russell 2000 ETF — broad small-cap exposure
- **TSLA:** Tesla Inc. — highly traded equity with strong retail/institutional interest
- [TBD: Additional symbols based on message volume analysis]

**Selection criteria:**
1. High average daily trading volume (> 10M shares/day)
2. Presence in multiple indices (to maximize ES correlation)
3. Active MPID participation (verified via preliminary data inspection)

### 3.4 MPID Selection

We rank MPIDs by total message activity (sum of add/cancel/replace events) across selected symbols and select the top K participants for detailed analysis.

**Rationale:**  
High-activity MPIDs are more likely to be professional liquidity providers with infrastructure capable of fast reactions. This introduces **survivorship bias** (we observe only successful, active participants) but ensures statistical significance.

**Preliminary MPID list (to be updated):**
- [TBD: Top 10-20 MPIDs by message count]
- Examples: NITE (Virtu), ARCA (NYSE Arca), DRCTEDGE, BATS, etc.

### 3.5 Temporal Coverage

**Trading hours analyzed:**  
Regular NASDAQ trading hours: 09:30-16:00 ET  
CME ES trading hours: 09:30-16:00 ET (aligned subset)

**Rationale:**  
We restrict to overlapping regular trading hours to avoid pre-market/post-market dynamics where liquidity and MPID participation may differ significantly. Extended hours analysis can be added as robustness check.

---

## 4. Methodology

### 4.1 Definitions and Notation

#### 4.1.1 Stimulus Event (ES Trade)

A stimulus event $s_i$ is defined as a CME ES LastTradeMsg at timestamp $t_i^{\text{ES}}$ (in nanoseconds since Unix epoch). We extract:

$$
s_i = \{t_i^{\text{ES}}, p_i^{\text{ES}}, q_i^{\text{ES}}, \text{side}_i^{\text{ES}}\}
$$

where:
- $t_i^{\text{ES}}$ = CME sending timestamp (ns)
- $p_i^{\text{ES}}$ = trade price (USD)
- $q_i^{\text{ES}}$ = quantity (contracts)
- $\text{side}_i^{\text{ES}}$ = aggressor side (buy/sell)

**Filtering:**  
No additional filtering applied to ES trades. All LastTradeMsg events are used as stimuli.

#### 4.1.2 Response Event (MPID Action)

A response event $r_j$ is defined as an MPID-attributed message on NASDAQ XNAS at timestamp $t_j^{\text{XNAS}}$ with message type in $\{\text{Add}, \text{Cancel}, \text{Delete}, \text{Replace}\}$:

$$
r_j = \{t_j^{\text{XNAS}}, \text{MPID}_j, \text{symbol}_j, \text{side}_j, \text{type}_j\}
$$

where:
- $t_j^{\text{XNAS}}$ = NASDAQ gateway timestamp (ns)
- $\text{MPID}_j$ = 4-character market participant ID
- $\text{symbol}_j$ = stock ticker
- $\text{side}_j$ = bid/ask (derived from order side)
- $\text{type}_j \in \{\text{F, X, U, D}\}$

**Filtering:**
- MPID must be non-null
- Symbol must be in selected symbol list
- MPID must be in top-K active participants

#### 4.1.3 Latency Metric

For each stimulus event $s_i$ at time $t_i^{\text{ES}}$, we identify the **first subsequent response** event $r_j$ for each (MPID, symbol) pair such that:

$$
j^* = \arg\min_{j: t_j^{\text{XNAS}} > t_i^{\text{ES}}, \, \text{symbol}_j = \sigma} t_j^{\text{XNAS}}
$$

where $\sigma$ is a symbol of interest (e.g., QQQ).

The latency is then:

$$
\Delta t_{i,\text{MPID}} = t_{j^*}^{\text{XNAS}} - t_i^{\text{ES}}
$$

measured in nanoseconds.

**Key properties of this metric:**
1. **Asymmetric:** We consider only responses *after* stimulus, not before
2. **First-action:** We take the minimum timestamp for each (MPID, symbol) pair after each stimulus
3. **Per-symbol:** Latencies are computed separately for each symbol (QQQ response to ES, IWM response to ES, etc.)
4. **No causality assumption:** This metric measures temporal ordering, not proven causation (see Section 6)

### 4.2 Join Procedure

**Algorithm:**

```
For each ES trade event s_i at time t_i:
    For each symbol σ in selected_symbols:
        For each MPID m in top_MPIDs:
            Find first XNAS message r_j where:
                - r_j.timestamp > t_i
                - r_j.mpid == m
                - r_j.symbol == σ
                - r_j.type in {Add, Cancel, Replace}
            
            If r_j exists:
                latency = r_j.timestamp - t_i
                Record: (t_i, m, σ, latency, r_j.type, ...)
            Else:
                No response found (right-censored observation)
```

**Implementation notes:**
- Efficient implementation uses sorted timestamp arrays with binary search
- Window limit: Impose maximum latency threshold $T_{\max} = 10$ seconds to avoid spurious matches
- Right-censoring: If no response occurs within $T_{\max}$, the observation is censored
- Multiple stimuli: Each stimulus is processed independently; overlapping windows are allowed

### 4.3 Temporal Aggregation

#### 4.3.1 Hour-of-Day Binning

Each latency observation is assigned to an hour-of-day bin based on the **stimulus timestamp**:

$$
h = \lfloor (\text{hour\_of\_day}(t_i^{\text{ES}})) \rfloor
$$

Bins: $h \in \{9, 10, 11, 12, 13, 14, 15\}$ (for 09:30-16:00 ET)

**Note:** The 09:30-10:00 bin is labeled as hour 9; 15:00-16:00 as hour 15.

#### 4.3.2 Day-Level Aggregation

Each latency observation is assigned a calendar date based on the stimulus timestamp:

$$
d = \text{date}(t_i^{\text{ES}})
$$

This allows analysis of day-to-day variation, trading volume effects, and identification of anomalous days (e.g., high volatility events).

### 4.4 Statistical Analysis

#### 4.4.1 Distributional Metrics

For each aggregation group (overall, per-MPID, per-hour, etc.), we compute:

- **Median latency** ($p_{50}$): Robust central tendency measure
- **Percentiles** ($p_{10}, p_{25}, p_{75}, p_{90}, p_{95}, p_{99}$): Distributional shape
- **Mean latency** ($\mu$): Average response time (sensitive to outliers)
- **Standard deviation** ($\sigma$): Dispersion measure

#### 4.4.2 Visualization

- **Overall histogram:** Distribution of all latencies (log-scale x-axis if needed)
- **Per-MPID boxplots:** Comparative distributions across market participants
- **Time-of-day heatmap/line plot:** Median latency by hour of day
- **Symbol comparison:** Latency distributions stratified by equity symbol

#### 4.4.3 Hypothesis Testing

**Research hypotheses (to be tested):**

1. **H1:** Latencies differ significantly across MPIDs (Kruskal-Wallis test)
2. **H2:** Latencies vary by time of day (Friedman test or ANOVA)
3. **H3:** Latencies differ across symbols (Kruskal-Wallis test)
4. **H4:** Latencies exhibit day-of-week effects (ANOVA)

Statistical tests will be reported with $p$-values and effect sizes. Significance threshold: $\alpha = 0.01$ (Bonferroni correction for multiple tests).

### 4.5 Scope Control and Filtering

To ensure robust results and computational feasibility:

1. **Top-K MPIDs:** Limit to top 10-20 MPIDs by message count
2. **Top-N symbols:** Limit to 3-10 symbols with highest ES correlation
3. **Trading hours:** Regular hours only (09:30-16:00 ET)
4. **Outlier treatment:** Flag latencies > 10 seconds as potential clock issues
5. **Minimum activity threshold:** Exclude MPID-day pairs with < 100 observations

---

## 5. Results

### 5.1 Overall Latency Distribution

**Figure 1: Overall Latency Histogram**  
![Overall Histogram](../outputs/latency_hist_overall.png)  
*Caption: Distribution of measured latencies (in microseconds) from ES trade events to first MPID action across all symbols and market participants. N = [TBD] observations.*

**Table 1: Overall Latency Summary Statistics**

| Metric | Value (μs) |
|--------|-----------|
| Mean | [TBD] |
| Median (p50) | [TBD] |
| p10 | [TBD] |
| p25 | [TBD] |
| p75 | [TBD] |
| p90 | [TBD] |
| p95 | [TBD] |
| p99 | [TBD] |
| Std. Dev. | [TBD] |
| Min | [TBD] |
| Max | [TBD] |
| N observations | [TBD] |

**Interpretation (to be written after results):**  
[TBD: Describe shape of distribution—unimodal/multimodal, skewness, presence of outliers. Compare to prior literature values. Discuss physical plausibility (e.g., minimum latency bounded by network/exchange latency).]

---

### 5.2 Per-MPID Latency Analysis

**Figure 2: Latency Distributions by MPID**  
![MPID Boxplots](../outputs/latency_by_mpid_boxplot.png)  
*Caption: Box plots showing latency distributions for each MPID. Boxes represent IQR (p25-p75), whiskers extend to 1.5×IQR, outliers shown as points.*

**Table 2: Per-MPID Summary Statistics**

| MPID | N obs | Median (μs) | Mean (μs) | p10 (μs) | p90 (μs) | Std Dev (μs) |
|------|-------|-------------|-----------|----------|----------|--------------|
| [MPID1] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| [MPID2] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| [MPID3] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| ... | ... | ... | ... | ... | ... | ... |
| [MPIDK] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

**Statistical Test:**  
Kruskal-Wallis H-test for differences across MPIDs: $H = [TBD]$, $p < [TBD]$

**Interpretation:**  
[TBD: Identify fastest and slowest MPIDs. Discuss potential explanations—technology infrastructure, market-making strategy (aggressive vs. passive), geographic co-location. Note that MPID identity may not perfectly correspond to firm identity due to routing arrangements.]

---

### 5.3 Time-of-Day Effects

**Figure 3: Median Latency by Hour of Day**  
![Time of Day Plot](../outputs/latency_by_hour.png)  
*Caption: Median latency (with IQR bands) across trading hours. Hour 9 = 09:30-10:30, Hour 15 = 15:00-16:00.*

**Table 3: Latency by Hour of Day**

| Hour | N obs | Median (μs) | Mean (μs) | p25 (μs) | p75 (μs) |
|------|-------|-------------|-----------|----------|----------|
| 9 (09:30-10:30) | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| 10 (10:00-11:00) | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| 11 (11:00-12:00) | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| 12 (12:00-13:00) | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| 13 (13:00-14:00) | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| 14 (14:00-15:00) | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| 15 (15:00-16:00) | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

**Statistical Test:**  
Friedman test / Kruskal-Wallis for hour-of-day effect: $\chi^2 = [TBD]$, $p < [TBD]$

**Interpretation:**  
[TBD: Discuss patterns—market open vs. close effects, lunch hour lull, relationship to ES trading volume. Consider capacity constraints (higher latency during high-volume periods) or strategic behavior (slower quotes during uncertain periods).]

---

### 5.4 Symbol-Level Analysis

**Figure 4: Latency Distributions by Symbol**  
![Symbol Comparison](../outputs/latency_by_symbol.png)  
*Caption: Violin plots or box plots comparing latency distributions across analyzed symbols.*

**Table 4: Per-Symbol Summary Statistics**

| Symbol | N obs | Median (μs) | Mean (μs) | p10 (μs) | p90 (μs) |
|--------|-------|-------------|-----------|----------|----------|
| QQQ | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| IWM | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| TSLA | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| ... | ... | ... | ... | ... | ... |

**Interpretation:**  
[TBD: Discuss differences—ETFs (QQQ/IWM) vs. single stocks (TSLA). ETFs may have tighter correlation to ES and thus faster reactions. Consider tick size effects, spread width, and average order size.]

---

### 5.5 Response Action Type Analysis

**Table 5: Latency by Response Action Type**

| Action Type | N obs | Median (μs) | Mean (μs) | p10 (μs) | p90 (μs) |
|-------------|-------|-------------|-----------|----------|----------|
| Add Order | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Cancel Order | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |
| Replace Order | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] |

**Interpretation:**  
[TBD: Cancels may be faster than adds due to risk management (removing stale quotes quickly). Replaces may have intermediate latency. Discuss implications for adverse selection and liquidity provision strategies.]

---

### 5.6 Day-Level Variation

**Figure 5: Daily Median Latency Time Series**  
![Daily Time Series](../outputs/latency_daily_timeseries.png)  
*Caption: Evolution of median latency across trading days. Shaded regions indicate [TBD: market events, high volatility days, etc.].*

**Interpretation:**  
[TBD: Identify anomalous days with unusually high/low latencies. Correlate with market volatility (VIX), ES volume, or news events. Discuss stability of infrastructure vs. adaptive behavior.]

---

## 6. Discussion and Limitations

### 6.1 Interpretation of Results

#### 6.1.1 Causality vs. Correlation

**Critical caveat:** Our latency metric measures **temporal ordering**, not proven causation. A NASDAQ MPID action following an ES trade does not definitively establish that the ES trade *caused* the MPID action. Possible confounds include:

1. **Common information arrival:** Both ES traders and NASDAQ MPIDs may react to the same external signal (e.g., macroeconomic news release)
2. **Coincidental timing:** MPID actions may be part of pre-scheduled algorithmic strategies unrelated to ES trades
3. **Unobserved stimuli:** Other market events (e.g., trades on other exchanges, dark pool activity) may trigger MPID reactions

**Mitigation strategies (future work):**
- Placebo tests: Measure latencies to random ES trades vs. large price-moving trades
- Event studies: Condition on ES trade characteristics (size, price impact) to identify informative trades
- Control variables: Include ES bid-ask spread, volume, and volatility as covariates

#### 6.1.2 Economic Significance

Observed median latencies of [TBD] μs correspond to [TBD] microseconds or [TBD] milliseconds. For context:

- **Speed of light (1-way):** NYC to Chicago ≈ 4 ms (fiber), ≈ 7 ms (microwave)
- **Typical exchange matching latency:** 50-500 μs
- **FPGA-based trading system response:** 1-10 μs

Fast latencies (< 100 μs) suggest:
- Co-located infrastructure with direct exchange connectivity
- Hardware-accelerated order generation (FPGAs, kernel-bypass networking)
- Sophisticated algorithmic strategies optimized for speed

Slow latencies (> 10 ms) may indicate:
- Geographically distant participants
- Software-based (CPU) order generation
- Deliberate strategic delays (quote fading, inventory management)
- Human or semi-automated decision processes

### 6.2 Data Limitations

#### 6.2.1 Clock Synchronization

**Issue:** CME and NASDAQ timestamps are generated by independent systems with potentially different clock sources.

**Implications:**
- **Clock drift:** If CME and NASDAQ clocks are not perfectly synchronized via PTP (Precision Time Protocol) or GPS, measured latencies may include systematic bias
- **Timestamp definition differences:** CME "sending time" may differ semantically from NASDAQ "gateway receipt time" in terms of what point in the message processing pipeline is timestamped
- **Magnitude of error:** Clock drift is typically < 1 μs for modern exchanges with GPS/PTP, but can be larger during system issues

**Evidence of quality:**
- Both CME and NASDAQ use GPS-synchronized clocks (documented in technical specifications)
- Cross-venue arbitrage studies (e.g., Bartlett and McCrary 2019) rely on cross-exchange timestamps and find sensible results

**Conservative approach:** We report latencies and note that values < 10 μs should be interpreted with caution due to potential timestamp noise.

#### 6.2.2 MPID Attribution Coverage

**Issue:** MPID identifiers are voluntarily provided and do not cover all NASDAQ orders.

**Selection bias:**
- MPIDs are more commonly used by **registered market makers** and **large broker-dealers**
- Retail orders routed through wholesalers may lack MPID attribution
- Proprietary trading firms may selectively use/omit MPIDs based on strategic considerations

**Implications for generalizability:**
- Our results characterize **professional, attributed liquidity providers**, not the entire market
- Median latencies may be **faster** than the true population median if MPID users are disproportionately sophisticated
- Conversely, some MPIDs may represent aggregated order flow rather than single firms

**Scope of conclusions:** Results apply to the **MPID-attributed subset** of market participants. Extrapolation to the full market requires caution.

#### 6.2.3 Symbol and MPID Selection Bias

**Issue:** We analyze only top symbols and top MPIDs by activity.

**Consequences:**
- **Liquidity concentration:** Top symbols (QQQ, IWM) are more liquid than average, potentially yielding faster reactions
- **Survivorship bias:** Top MPIDs are successful, active participants—slower or less active firms are excluded
- **Correlation strength:** Selected symbols have strong ES correlation by design; results may not apply to weakly correlated stocks

**Justification:**  
This scope limitation is **deliberate** to ensure statistical power and focus on economically meaningful participants. We do not claim results generalize to illiquid stocks or infrequent traders.

### 6.3 Methodological Limitations

#### 6.3.1 "First Subsequent Action" Metric

**Definition choice:** We measure time to the **first** MPID action after an ES trade, not cumulative activity or order book impact.

**Limitations:**
- **Incomplete response:** A single add/cancel/replace may not represent the full adjustment to new information
- **Spurious first actions:** The first action may be unrelated to the ES trade; subsequent actions might be the true response
- **Aggregation loss:** We do not capture the magnitude of quote updates (price change, size change)

**Alternative metrics (future work):**
- Time to "significant" order book change (e.g., 10% depth change)
- Cumulative activity in a post-stimulus window (e.g., message count in [0, 100ms])
- Price impact-weighted latency (weight by magnitude of MPID quote change)

#### 6.3.2 Windowing and Censoring

**Window choice:** $T_{\max} = 10$ seconds is arbitrary but necessary to avoid spurious matches.

**Right-censoring:** If no MPID action occurs within 10 seconds, we discard the stimulus event (right-censored).

**Implications:**
- Slow reactions (> 10s) are excluded, biasing median downward
- Silent periods (no MPID activity) are not captured
- Choice of $T_{\max}$ affects sample size and distributional shape

**Robustness check:** Vary $T_{\max} \in \{1s, 5s, 10s, 60s\}$ and report sensitivity.

### 6.4 External Validity

**Market conditions:** Our data spans [TBD date range], which may include specific market regimes (low/high volatility, trending/mean-reverting).

**Regulatory environment:** Results reflect current market structure (Reg NMS, maker-taker pricing, etc.). Changes in regulation or exchange fee structures could alter behavior.

**Technology evolution:** High-frequency trading infrastructure evolves rapidly. Latencies measured in 2025 may not reflect 2020 or 2030 capabilities.

### 6.5 Confounding Factors

#### 6.5.1 Observability Limitations

**Unobserved channels:**
- **Dark pools:** Off-exchange trading is not captured; MPIDs may react to dark pool activity correlated with ES
- **Proprietary signals:** Firms may use non-public data (order flow, news feeds) that correlate with ES trades
- **Cross-exchange activity:** MPIDs may react to events on BATS, IEX, or other lit venues not analyzed here

#### 6.5.2 Strategic Behavior

**Endogeneity concerns:**
- **Anticipatory trading:** MPIDs may predict ES trades and pre-position, creating negative latencies (action before observed stimulus)
- **Strategic delays:** MPIDs may intentionally slow quote updates to avoid adverse selection or signal trading intent
- **Gaming:** If MPIDs are aware of latency measurement methodologies, they may optimize for metrics rather than economic efficiency

---

## 7. Conclusion

This study provides direct empirical measurement of reaction latencies for NASDAQ MPID-attributed liquidity providers in response to CME ES trade events. Using nanosecond-precision timestamps from market data feeds, we document [TBD: key findings on median latencies, cross-MPID heterogeneity, and temporal patterns].

### 7.1 Key Findings (Summary Placeholder)

1. **Overall latency:** Median response time of [TBD] μs, with [p10, p90] = [TBD, TBD] μs
2. **MPID heterogeneity:** Top performers achieve [TBD] μs; slowest participants exhibit [TBD] μs (statistically significant differences, $p < 0.01$)
3. **Time-of-day effects:** Latencies [increase/decrease/stable] during [market open/close/midday], with peak values of [TBD] μs at [TBD hour]
4. **Symbol differences:** QQQ exhibits [faster/slower] reactions than [IWM/TSLA], consistent with [index arbitrage/liquidity] theory
5. **Action type patterns:** Cancellations are [faster/slower] than adds by [TBD] μs, suggesting [risk management/opportunistic] behavior

### 7.2 Implications

**For market structure policy:**  
[TBD: Discuss whether observed latencies justify speed bump proposals, tick size changes, or MPID disclosure requirements]

**For trading strategy design:**  
[TBD: Benchmarking opportunities for proprietary traders; competitive dynamics in the "latency arms race"]

**For academic research:**  
[TBD: Contribution to understanding information transmission, liquidity provision under adverse selection, and cross-market dynamics]

### 7.3 Future Research Directions

1. **Causal identification:** Use instrumental variables or natural experiments to establish causal links between ES trades and MPID actions
2. **Expanded scope:** Include additional exchanges (CBOE, IEX), symbols (full S&P 500), and MPIDs (long-tail participants)
3. **Quote quality outcomes:** Link latencies to bid-ask spreads, depth, and adverse selection costs
4. **Machine learning:** Predict latencies using trade characteristics (size, volatility, time-of-day) and MPID features
5. **Intraday dynamics:** High-frequency analysis (second-by-second) to capture real-time adaptation

### 7.4 Reproducibility

All code and data processing scripts are available at:  
**GitHub repository:** [TBD: insert repository URL]

**File structure:**
- `message_extraction/`: PCAP parsing and ITCH/MDP decoding
- `mpid_latency/`: Core latency calculation engine
- `analysis/`: Statistical analysis and visualization notebooks
- `reports/`: This report and supplementary materials

**Dependencies:** Python 3.11+, NumPy, Pandas, Matplotlib, SciPy, [TBD: other libraries]

---

## References

Bartlett, R. P., & McCrary, J. (2019). *High-frequency trading and market structure.* Annual Review of Financial Economics, 11, 181-207.

Brogaard, J., Hendershott, T., & Riordan, R. (2014). *High-frequency trading and price discovery.* Review of Financial Studies, 27(8), 2267-2306.

Chordia, T., Sarkar, A., & Subrahmanyam, A. (2011). *Liquidity dynamics and cross-autocorrelations.* Journal of Financial and Quantitative Analysis, 46(3), 709-736.

Comerton-Forde, C., & Putniņš, T. J. (2015). *Dark trading and price discovery.* Journal of Financial Economics, 118(1), 70-92.

Hasbrouck, J. (2003). *Intraday price formation in U.S. equity index markets.* Journal of Finance, 58(6), 2375-2400.

Hasbrouck, J., & Saar, G. (2013). *Low-latency trading.* Journal of Financial Markets, 16(4), 646-679.

Hendershott, T., & Moulton, P. C. (2011). *Automation, speed, and stock market quality: The NYSE's Hybrid.* Journal of Financial Markets, 14(4), 568-604.

Menkveld, A. J. (2013). *High frequency trading and the new market makers.* Journal of Financial Markets, 16(4), 712-740.

---

## Appendix

### A. Data Schema Details

**CME MDP 3.0 LastTradeMsg (Binary Layout):**
```
Offset | Field Name        | Type   | Size | Description
-------|-------------------|--------|------|---------------------------
0      | sending_time      | uint64 | 8    | Nanosecond timestamp
8      | security_id       | uint32 | 4    | Instrument ID
12     | match_event_ind   | uint8  | 1    | Event indicator
13     | trade_price       | int64  | 8    | Price (decimal encoded)
21     | trade_qty         | uint32 | 4    | Quantity
25     | aggressor_side    | uint8  | 1    | 1=buy, 2=sell
...
```

**NASDAQ ITCH 5.0 Add Order (Type A):**
```
Offset | Field Name        | Type   | Size | Description
-------|-------------------|--------|------|---------------------------
0      | message_type      | char   | 1    | 'A'
1      | stock_locate      | uint16 | 2    | Stock identifier
3      | tracking_number   | uint16 | 2    | Tracking number
5      | timestamp         | uint48 | 6    | Nanoseconds since midnight
11     | order_ref         | uint64 | 8    | Order reference
19     | side              | char   | 1    | 'B' or 'S'
20     | shares            | uint32 | 4    | Share quantity
24     | stock             | char   | 8    | Stock symbol (padded)
32     | price             | uint32 | 4    | Price (1/10000 units)
36     | attribution       | char   | 4    | MPID (optional)
```

### B. Processing Pipeline Pseudocode

```python
def compute_latencies(es_trades, nasdaq_messages, symbols, mpids):
    """
    Compute first-action latencies from ES trades to NASDAQ MPID responses.
    
    Parameters:
    - es_trades: DataFrame with columns [timestamp_ns, price, qty, side]
    - nasdaq_messages: DataFrame with [timestamp_ns, mpid, symbol, type, ...]
    - symbols: List of symbols to analyze
    - mpids: List of MPIDs to analyze
    
    Returns:
    - DataFrame with [stimulus_time, mpid, symbol, latency_ns, response_type]
    """
    results = []
    
    # Filter NASDAQ messages to selected scope
    nasdaq_filtered = nasdaq_messages[
        (nasdaq_messages['mpid'].isin(mpids)) &
        (nasdaq_messages['symbol'].isin(symbols)) &
        (nasdaq_messages['type'].isin(['A', 'F', 'X', 'U', 'D']))
    ].sort_values('timestamp_ns')
    
    for _, es_trade in es_trades.iterrows():
        t_stimulus = es_trade['timestamp_ns']
        
        for symbol in symbols:
            for mpid in mpids:
                # Find first subsequent message
                subset = nasdaq_filtered[
                    (nasdaq_filtered['timestamp_ns'] > t_stimulus) &
                    (nasdaq_filtered['timestamp_ns'] <= t_stimulus + 10e9) &  # 10 sec window
                    (nasdaq_filtered['mpid'] == mpid) &
                    (nasdaq_filtered['symbol'] == symbol)
                ]
                
                if len(subset) > 0:
                    first_response = subset.iloc[0]
                    latency = first_response['timestamp_ns'] - t_stimulus
                    
                    results.append({
                        'stimulus_time': t_stimulus,
                        'mpid': mpid,
                        'symbol': symbol,
                        'latency_ns': latency,
                        'response_type': first_response['type'],
                        'response_time': first_response['timestamp_ns']
                    })
    
    return pd.DataFrame(results)
```

### C. Additional Tables and Figures

**Table A1: Data Coverage Summary**

| Date | ES Trades | NASDAQ Messages | MPID Messages | Matched Pairs |
|------|-----------|-----------------|---------------|---------------|
| [Date 1] | [TBD] | [TBD] | [TBD] | [TBD] |
| [Date 2] | [TBD] | [TBD] | [TBD] | [TBD] |
| ... | ... | ... | ... | ... |
| **Total** | **[TBD]** | **[TBD]** | **[TBD]** | **[TBD]** |

**Table A2: Symbol-MPID Interaction Matrix (Observation Counts)**

|  | MPID1 | MPID2 | MPID3 | ... | MPIDK |
|--|-------|-------|-------|-----|-------|
| **QQQ** | [TBD] | [TBD] | [TBD] | ... | [TBD] |
| **IWM** | [TBD] | [TBD] | [TBD] | ... | [TBD] |
| **TSLA** | [TBD] | [TBD] | [TBD] | ... | [TBD] |
| ... | ... | ... | ... | ... | ... |

---

**End of Report**

---

**Compilation Instructions (LaTeX/PDF Generation):**

To convert this Markdown report to a professional PDF:

1. **Using Pandoc with LaTeX:**
   ```bash
   pandoc report.md -o report.pdf \
       --pdf-engine=xelatex \
       --variable geometry:margin=1in \
       --variable fontsize=11pt \
       --variable documentclass=article \
       --number-sections \
       --toc \
       --bibliography=references.bib \
       --csl=chicago-author-date.csl
   ```

2. **Using R Markdown:**
   - Add YAML header:
   ```yaml
   ---
   title: "High-Frequency Liquidity Provider Response Latency to External Price Shocks"
   author: "[Your Name]"
   date: "December 20, 2025"
   output:
     pdf_document:
       toc: true
       number_sections: true
       fig_caption: true
       keep_tex: true
   bibliography: references.bib
   ---
   ```
   - Render: `rmarkdown::render("report.md")`

3. **Using Markdown to LaTeX (manual):**
   - Convert to `.tex` using Pandoc
   - Customize LaTeX preamble for journal submission requirements
   - Compile with `xelatex report.tex`

**Required LaTeX Packages:**
- `amsmath`, `amssymb` (for equations)
- `graphicx` (for figures)
- `hyperref` (for clickable references)
- `booktabs` (for professional tables)
- `natbib` or `biblatex` (for bibliography)

**Figure Placeholders:**  
Replace `![Caption](path)` with actual generated plots once analysis is complete. Ensure all figure files are in `outputs/` directory with exact filenames as referenced.

**Table Placeholders:**  
Fill in [TBD] values from analysis output. Consider generating tables programmatically using Pandas `.to_latex()` for consistency.

**Next Steps:**
1. Complete data processing pipeline
2. Run latency computation
3. Generate all figures and tables
4. Update all [TBD] placeholders with actual results
5. Write interpretation sections in Section 5 and 6
6. Proofread for consistency and clarity
7. Compile to PDF and review formatting
8. Submit to professor / prepare for publication
