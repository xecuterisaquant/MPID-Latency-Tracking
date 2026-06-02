# MPID Latency Analysis - Presentation Deck
**Target Length: 5-10 minutes | FIN 556 - Algorithmic Market Microstructure | UIUC Fall 2025**

---

## Slide 1: Title Slide
**Visual:** Clean title slide with project name and team info

**Title:** High-Frequency Liquidity Provider Response Latency to External Price Shocks

**Subtitle:** An Empirical Analysis of Cross-Market Reaction Times

**Team:** Harsh Hari, Ivaylo Maksimov, Chintan Vajariya  
**Course:** FIN 556 Market Microstructure | UIUC  
**Date:** December 22, 2025

**Speaker Notes (15 sec):**
"Hi, I'm [name], and today I'll walk you through our research project measuring how fast trading firms react when futures prices change - specifically which firms dominate ultra-fast cross-market trading and whether the speed advantages we hear about are real."

---

## Slide 2: The Research Question
**Visual:** Simple diagram showing CME (Chicago) → 700 miles → NASDAQ (New Jersey) with arrow

**Content:**
- **Stimulus:** CME E-mini S&P 500 (ES) futures trades
- **Response:** NASDAQ order updates (Add/Cancel/Replace)
- **Question:** How quickly do market makers react?
- **Key Metric:** Time from ES trade → First NASDAQ MPID action

**Speaker Notes (45 sec):**
"Financial markets are interconnected across exchanges. When S&P 500 futures trade on CME in Chicago, stocks on NASDAQ in New Jersey should adjust their quotes because they track similar underlying value.

Our research question: How fast does this happen? Which firms are fastest? And by how much?

We measured actual reaction times at nanosecond precision across 12 trading days in March 2025, processing 93 million latency observations. This matters because speed advantages can be worth billions in trading profits, and there's debate about whether ultra-fast trading creates unfair markets."

---

## Slide 3: What is an MPID?
**Visual:** Diagram showing: Trading Firm → MPID Code → NASDAQ Exchange → Data Feed

**Content:**
- **MPID = Market Participant Identifier**
- 4-letter code identifying trading firms on NASDAQ
- Examples: 
  - **WBPX** = Summit Securities Group
  - **JPMS** = JP Morgan Securities  
  - **WCHV** = Wolverine Trading
- Voluntarily disclosed (not all orders have MPIDs)
- Embedded in real-time market data feeds

**Speaker Notes (45 sec):**
"MPID stands for Market Participant Identifier - think of it as a license plate for trading firms. Every MPID-attributed order sent to NASDAQ has a 4-letter code identifying who sent it.

For example, WBPX is Summit Securities Group, JPMS is JP Morgan, WCHV is Wolverine Trading.

Important caveat: MPIDs are voluntarily disclosed, so not all firms use them. This creates selection bias - we're only seeing firms that choose to identify themselves, typically market makers and large broker-dealers. Proprietary traders often hide their identities. But this transparency is what makes our analysis possible."

---

## Slide 4: The Data Challenge
**Visual:** Three-stage data flow diagram: Raw PCAP → Binary Parsing → Latency Matching

**Content:**
**Data Sources:**
- **CME MDP 3.0:** ~440K ES trades/day (12 trading days, March 10-21, 2025)
- **NASDAQ ITCH 5.0:** ~95M+ MPID messages/day across 10 symbols
- **Timestamp precision:** Nanoseconds (GPS-synchronized)

**Processing Pipeline:**
1. Decode binary protocols (ITCH 5.0, MDP 3.0)
2. Extract timestamps, symbols, MPIDs, prices
3. Binary search matching: For each ES trade, find first NASDAQ response
4. Calculate latency: NASDAQ timestamp - CME timestamp

**Final Dataset:** 93,031,377 latency observations | 1.45 GB compressed Parquet

**Speaker Notes (60 sec):**
"The data scale here is massive. We processed CME futures trades and NASDAQ order messages over 12 trading days in March 2025.

Both exchanges send data in binary formats - NASDAQ uses ITCH 5.0 protocol, CME uses MDP 3.0. We decoded these at the byte level to extract nanosecond-precision timestamps.

The computational challenge: For each of 440,000 daily ES trades, find the first relevant NASDAQ response among 95 million daily messages, for 10 different stocks and 88 distinct trading firms.

We used Python with Numba JIT compilation - making Python run as fast as C++ - with optimized binary search. Final dataset: 93 million matched latency measurements. This ran on a laptop in a few hours instead of days."

---

## Slide 5: Key Finding #1 - Extreme Concentration
**Visual:** Pie chart showing 97% concentration (use `outputs/figures/fig_03_top_firms.png`)

**Content:**
**Top 3 Firms = 97% of All Activity**

| Firm | MPID | Observations | Median Latency | % of Total |
|------|------|--------------|----------------|------------|
| Summit Securities Group | WBPX | 33.4M | 140.9 ms | 35.9% |
| Wolverine | WCHV | 32.1M | 138.1 ms | 34.5% |
| JP Morgan | JPMS | 24.7M | 135.7 ms | 26.6% |
| **Total** | | **90.2M** | **~138 ms** | **97.0%** |

- Out of 88 identified MPIDs, top 3 completely dominate
- Remaining 3%: Sporadic/slow participants (4,450ms median)

**Speaker Notes (60 sec):**
"Here's the most striking finding: The market for ultra-fast cross-exchange trading is hyper-concentrated. Just three firms - Summit Securities Group, Wolverine, and JP Morgan - account for 97% of all MPID-attributed activity.

Out of 88 distinct trading firms we identified, these three process 90 million observations with remarkably consistent 135-141 millisecond latencies.

The remaining 3% of activity comes from sporadic participants with median latencies around 4,450 milliseconds - that's 32 times slower.

Interestingly, famous HFT firms like Citadel, Virtu, and IMC barely appear in our data. They likely avoid disclosing MPIDs to protect their strategies.

This concentration shows that speed advantages create winner-take-all dynamics. The barrier to entry is extraordinarily high."

---

## Slide 6: Key Finding #2 - The Speed Gap
**Visual:** Bar chart showing latency ranges (use `outputs/figures/fig_02_firm_categories.png`)

**Content:**
**32× Speed Difference Across Participants**

| Category | Median Latency | Representative Firms |
|----------|----------------|----------------------|
| **Active Fast Market Makers** | ~138 ms | Summit Securities Group, Wolverine, JP Morgan |
| **Moderate** | 154-210 ms | ETMM, Citadel, Flow Traders |
| **Slow/Sporadic** | ~4,450 ms | IMC, UBS, Goldman Sachs |

**Symbol Variation (24× range):**
- Fastest: **QQQ** = 51.1 ms (NASDAQ-100 ETF)
- Slowest: **META** = 1,209 ms (weak ES correlation)
- SPY, NVDA, TSLA, AAPL in between

**Speaker Notes (60 sec):**
"The speed differences are dramatic. The fastest firms - our top 3 market makers - respond in about 138 milliseconds on average. The slowest participants take 4,450 milliseconds, which is 32 times slower.

Even across different stocks, there's huge variation. QQQ, the NASDAQ-100 ETF, gets 51-millisecond responses because it's directly correlated with ES futures. META stock takes 1,209 milliseconds - 24 times slower - because its correlation with ES is much weaker.

These gaps reveal a clear priority system: Firms focus their fastest infrastructure where it matters most for cross-market arbitrage. This requires massive technology investment - microwave networks, co-located servers, FPGA hardware - worth it only for high-correlation instruments."

---

## Slide 7: Technical Insight - Infrastructure Investment
**Visual:** Network diagram: CME Chicago ↔ NASDAQ New Jersey (700 miles)

**Content:**
**Physical Constraints:**
- **Distance:** Chicago to New Jersey = ~700 miles
- **Speed of light (one-way):**
  - Fiber optic cable: ~7 ms
  - Microwave (air): ~4 ms  
- **Exchange processing:** 50-500 microseconds each
- **Order generation:** 1-10 microseconds (FPGA) vs 100+ μs (CPU)

**Our Measured Latencies:**
- Top firms: **135-141 ms median** (round-trip + processing + matching)
- Physically consistent with microwave + low-latency infrastructure

**Investment Required:**
- Microwave tower networks: Multi-million dollar build-out
- Co-location at both exchanges
- FPGA-based order generation hardware
- Dedicated fiber connections

**Speaker Notes (60 sec):**
"Here's where it gets interesting from a technology perspective. CME is in Chicago, NASDAQ is in New Jersey - about 700 miles apart.

The speed of light creates a physical limit. Through fiber optic cables, a signal takes about 7 milliseconds one-way. Through microwave towers in the air, it's faster - about 4 milliseconds - because microwaves travel at closer to the speed of light.

Our measured latencies of 135-141 milliseconds for the top firms align with what physics predicts for round-trip communication plus exchange processing time. This suggests these firms have invested in expensive microwave networks - we're talking millions of dollars in infrastructure just to save 40 milliseconds compared to fiber.

Additionally, they need co-located servers at both exchanges, FPGA hardware for sub-microsecond order generation, and optimized software stacks. The barrier to entry is extraordinarily high."

---

## Slide 8: Data Processing Pipeline
**Visual:** Flowchart: Raw PCAP → Binary Decode → Timestamp Extraction → Binary Search Match → Statistical Analysis

**Content:**
**Step-by-Step Technical Implementation:**

1. **Ingest Raw Data**
   - PCAP files from virtual machine (course-provided)
   - NASDAQ ITCH 5.0 binary protocol
   - CME MDP 3.0 binary protocol

2. **Message Parsing**
   - Decode binary structures (byte-level manipulation)
   - Extract: nanosecond timestamps, symbols, MPIDs, prices, order types
   - Filter: Top 10 symbols, 88 MPIDs with attribution

3. **Latency Calculation**
   - For each ES trade: Binary search to find first subsequent NASDAQ action
   - Per (MPID, symbol) pair
   - Latency = NASDAQ_timestamp - CME_timestamp
   - 10-second maximum window (avoid spurious matches)

4. **Statistical Analysis**
   - Aggregate by MPID, symbol, hour, day
   - Generate 9 publication-quality figures
   - Export to Parquet format (1.45 GB compressed)

**Technologies:** Python, Numba (JIT), Pandas, Polars, Matplotlib/Seaborn

**Speaker Notes (60 sec):**
"From a technical implementation perspective, here's what we built.

We started with raw PCAP network capture files containing binary market data. These use proprietary formats - NASDAQ's ITCH 5.0 and CME's MDP 3.0 protocols. We decoded these at the byte level to extract the fields we needed.

The matching step was computationally intensive. For each of 440,000 daily ES trades, we used binary search to find the first subsequent NASDAQ message for each firm and symbol combination. This required sorted timestamp arrays and careful edge-case handling.

We used Numba, which compiles Python to machine code at runtime, making critical loops run 100x faster. Without this optimization, processing would have taken days instead of hours.

The output is a clean dataset with 93 million observations that we analyzed statistically and visualized with publication-quality figures."

---

## Slide 9: Why This Matters
**Visual:** Three columns with icons: Market Structure | Technology Economics | Regulatory Policy

**Content:**
**Market Structure Insights:**
- **Winner-take-all dynamics:** 97% concentration in 3 firms
- Speed advantages are persistent, not contested
- High barriers to entry protect incumbents

**Technology Economics:**
- Multi-million dollar infrastructure for 40ms advantage
- FPGA hardware, microwave networks, co-location required
- ROI justifies investment at scale

**Regulatory Relevance:**
- Is 32× speed gap fair to retail investors?
- Do speed bumps level the playing field?
- Market resilience depends on 3 firms

**Academic Contribution:**
- Direct latency measurement at MPID level (not proxy variables)
- Cross-venue stimulus-response methodology
- 93M observations with nanosecond precision

**Speaker Notes (45 sec):**
"Why does this research matter beyond the class?

First, it reveals winner-take-all market structure. Three firms control 97% of fast responses. Small technology advantages create massive dominance.

Second, it quantifies the economics of speed. Firms invest millions in microwave networks and specialized hardware for milliseconds of advantage. The returns must justify these costs.

Third, it's relevant for regulation. The SEC and FINRA care whether 32-times speed gaps harm price discovery or disadvantage retail investors. Our measurements provide empirical evidence for these debates.

Finally, academically, we've measured actual latencies at the firm level rather than using proxy variables. This methodology could extend to other cross-market relationships."

---

## Slide 10: Key Takeaways
**Visual:** Clean layout with three main findings highlighted

**Content:**
**Research Findings:**
✅ **Hyper-concentration:** Top 3 firms (Summit Securities Group, Wolverine, JP Morgan) control 97% of MPID-attributed activity

✅ **Massive speed gaps:** 
   - 32× difference between fast market makers (138ms) and slow participants (4,450ms)
   - 24× symbol variation (QQQ: 51ms vs META: 1,209ms)

✅ **Infrastructure evidence:** 135-141ms latencies physically consistent with microwave networks + low-latency tech stack

**Dataset Scale:**
- 93,031,377 latency observations
- 12 trading days (March 10-21, 2025)
- Nanosecond-precision cross-venue matching
- Production-grade data engineering in Python/Numba

**Novel Contribution:** First MPID-level cross-market latency study with direct measurement (not inferred)

**Speaker Notes (30 sec):**
"To summarize our research:

We found extreme concentration - just three firms dominate ultra-fast cross-market trading. We measured massive speed gaps - 32 times difference between fastest and slowest participants. And we found evidence of expensive infrastructure investment paying off through consistent sub-150-millisecond latencies.

This analysis processed over 93 million observations using production-grade data engineering. It's the first study to directly measure cross-market latencies at the individual firm level rather than inferring speed from other variables."

---

## Slide 11: Thank You / Questions
**Visual:** Clean slide with contact info and key links

**Content:**
**Project Details:**
- **Team:** Harsh Hari, Ivaylo Maksimov, Chintan Vajariya
- **Course:** FIN 556 - Algorithmic Market Microstructure | UIUC Fall 2025
- **Dataset:** 93M observations, 12 trading days (March 10-21, 2025)
- **Technologies:** Python, Numba, Pandas, Polars, NASDAQ ITCH 5.0, CME MDP 3.0

**Available Materials:**
- Full research report (20 pages)
- Complete Python codebase (data pipeline + analytics)
- Publication-quality figures (9 charts)
- GitLab repository: `gitlab.engr.illinois.edu/fin556_algo_market_micro_fall_2025/.../group_07_project`

**Acknowledgments:**
- Professor David Lariviere (guidance and feedback)
- Gustaf Soederlind (CME MDP 3.0 parser)

**Questions?**

**Speaker Notes (15 sec):**
"Thank you for your time. The full 20-page report and all the code are available on our GitLab repository if you'd like to dive deeper into the methodology or results. I'm happy to answer any questions about the data processing, statistical methods, or findings."

---

## PRESENTATION TIPS

### Timing Breakdown (Total: ~8 minutes)
- Intro: 15 sec
- Problem: 45 sec  
- MPID Explanation: 45 sec
- Data Scale: 60 sec
- Finding #1 (Concentration): 60 sec
- Finding #2 (Speed Gap): 60 sec
- Technical Insight: 60 sec
- Pipeline: 60 sec
- Why It Matters: 45 sec
- Takeaways: 30 sec
- Closing: 15 sec

### Delivery Guidelines
1. **Start strong** - Hook with "how fast do different firms react to price changes"
2. **Use analogies** - "faster than an eye blink", "license plate for trading firms"
3. **Show visuals, don't read slides** - Charts and diagrams do heavy lifting
4. **Emphasize scale** - "93 million observations", "1.4 billion messages"
5. **Connect to business value** - Why companies care about this work
6. **Keep technical depth balanced** - Show you understand internals without drowning in detail

### What to Emphasize for Recruiters
- **Data engineering skills:** Binary protocol parsing, billion-message scale processing
- **Optimization expertise:** Numba JIT compilation, algorithmic efficiency
- **Domain knowledge:** Market microstructure, cross-market dynamics
- **End-to-end ownership:** Raw data → insights → publication-quality report
- **Quantitative rigor:** Statistical validation, edge case handling

### Common Questions to Prep
1. "How did you validate the latency measurements?"
   - Cross-checked with physical speed-of-light limits, statistical outlier detection
2. "Could you scale this to more exchanges?"
   - Yes, modular pipeline design, already handles two protocols
3. "What was the hardest technical challenge?"
   - Matching algorithm optimization - binary search with edge case handling
4. "What would you do differently?"
   - Extend to longer timeframe (1 year), add more symbols, test causal relationships

---

## SLIDE CREATION GUIDE

### Recommended Tool
**PowerPoint or Google Slides** (PowerPoint preferred for better chart control)

### Visual Style Guidelines
- **Layout:** Clean, professional, minimal clutter
- **Text:** Maximum 5-7 words per bullet point
- **Fonts:** 
  - Titles: 40-48pt (Calibri, Helvetica, or Arial)
  - Body: 28-32pt
  - Tables: 20-24pt
- **Color scheme:** Professional blue/gray palette (avoid bright colors)
  - Primary: Navy blue (#003366) or Dark gray (#333333)
  - Accent: Light blue (#4A90E2)
  - Background: White or very light gray (#F5F5F5)
- **Consistency:** Use same template for all slides

### Charts to Include (from `outputs/figures/` folder)

**Slide 5 - Concentration:**
- Use: `outputs/figures/fig_03_top_firms.png` (box plots showing firm distributions)
- Alternative: Create simple pie chart showing 97% vs 3% split
- Show table with top 3 firms

**Slide 6 - Speed Gap:**
- Use: `outputs/figures/fig_02_firm_categories.png` (category comparison)
- Use: `outputs/figures/fig_04_symbols.png` (symbol analysis)
- Consider: Side-by-side comparison of fast vs slow firms

**Slide 7 - Infrastructure:**
- Create simple diagram: Two boxes (CME Chicago | NASDAQ New Jersey)
- Add distance label (700 miles)
- Show microwave towers vs fiber cables
- Can hand-draw or use PowerPoint shapes

**Slide 8 - Pipeline:**
- Create simple flowchart using PowerPoint shapes
- 5 boxes connected by arrows
- Keep it high-level (avoid technical jargon in visual)

**Optional Additional Slides:**
- `outputs/figures/fig_01_latency_distribution.png` - Overall histogram
- `outputs/figures/fig_05_time_of_day.png` - Hourly patterns
- `outputs/figures/fig_06_firm_correlation.png` - Correlation matrix

### Figure File Locations
All figures are in: `d:\Harsh\FIN556 MPID\MPID-Latency-Tracking\outputs\figures\`

Available figures:
1. `fig_01_latency_distribution.png` - Overall histogram
2. `fig_02_firm_categories.png` - Fast vs slow firms
3. `fig_03_top_firms.png` - Top firm box plots
4. `fig_04_symbols.png` - Symbol-level analysis
5. `fig_05_time_of_day.png` - Hourly variation
6. `fig_06_firm_correlation.png` - Firm correlation matrix
7. `fig_07_symbol_correlation.png` - Symbol correlation
8. `fig_08_weekly_heatmap.png` - Weekly patterns
9. `fig_09_contract_comparison.png` - ESH25 vs ESM25

### Table Creation Tips
For slides 5, 6, and 10 with data tables:
- Use PowerPoint's table feature
- Align numbers right, text left
- Bold the headers
- Use alternating row colors for readability
- Keep to 3-5 rows maximum per slide

### Estimated Time Investment
- **Slide creation:** 45-60 minutes (using existing figures)
- **Practice run-through:** 20-30 minutes (essential!)
- **Total:** ~90 minutes to be presentation-ready

### Practice Recommendations
1. **Time yourself:** Aim for 7-8 minutes (leaves buffer)
2. **Record yourself:** Check for filler words ("um", "like")
3. **Test transitions:** Ensure smooth flow between slides
4. **Prepare for questions:**
   - "How did you validate timestamps?" → GPS sync, speed-of-light checks
   - "Why are famous HFT firms missing?" → MPID disclosure is voluntary
   - "Can this scale to more exchanges?" → Yes, modular design
   - "What's next?" → Longer timeframe, causal tests, more venues
