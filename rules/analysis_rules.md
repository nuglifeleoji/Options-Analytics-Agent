# Professional Options Analysis Rules
**Version:** 1.0  
**Author:** Leo Ji  
**Purpose:** Specialized rules for professional options chain analysis

---

## 🎯 Analysis Philosophy

```yaml
approach: Data-driven and objective
methodology: Multi-dimensional analysis
output_format: Professional and actionable
confidence_level: Always disclosed
```

### Core Principles
1. **Evidence-Based**: All conclusions backed by data
2. **Context-Aware**: Consider market conditions
3. **Risk-Conscious**: Always assess downside
4. **Actionable**: Provide clear insights

---

## 📊 Analysis Framework

### Stage 1: Data Validation
```
Before ANY analysis:
1. Verify data quality
   - Minimum contracts: 300 (warn if less)
   - Optimal range: 500-800 contracts
   - Date coverage: Check expiration spread

2. Check data completeness
   - Both calls and puts present
   - Strike price distribution reasonable
   - No suspicious gaps

3. Identify data limitations
   - Polygon.io: Current month only
   - No historical comparison available
   - Single snapshot in time

4. Set expectations
   - What can be analyzed
   - What cannot be determined
   - Confidence levels
```

### Stage 2: Quantitative Analysis
```
Calculate key metrics:

1. Call/Put Ratio
   - Total calls / Total puts
   - Interpretation:
     • > 1.5: Bullish signal
     • 0.7-1.5: Neutral
     • < 0.7: Bearish signal

2. Strike Distribution
   - Range: Max strike - Min strike
   - Median strike
   - Mode strike (most common)
   - Strike clustering

3. Volume Concentration
   - Top 5 strikes by volume
   - Percentage of total volume
   - Identify key levels

4. Put/Call Skew
   - Compare put strikes vs call strikes
   - OTM vs ITM distribution
```

### Stage 3: Qualitative Analysis
```
Interpret the data:

1. Market Sentiment
   - Aggregate all signals
   - Assign confidence score (0-100%)
   - Classification:
     • Strongly Bullish: > 70% confidence
     • Bullish: 50-70%
     • Neutral: 30-50%
     • Bearish: 15-30%
     • Strongly Bearish: < 15%

2. Key Support/Resistance
   - High put volume = support
   - High call volume = resistance
   - Strike clustering = strong levels

3. Risk Assessment
   - Put concentration analysis
   - Hedging activity detection
   - Risk level: Low/Moderate/Elevated

4. Market Structure
   - Institutional vs retail positioning
   - Directional bias
   - Hedging vs speculation
```

### Stage 4: Synthesis & Reporting
```
Generate insights:

1. Executive Summary
   - 2-3 sentence overview
   - Key takeaway
   - Risk/reward assessment

2. Detailed Findings
   - All dimensions covered
   - Evidence for each claim
   - Data points cited

3. Recommendations
   - What to watch
   - Key levels to monitor
   - Risk considerations

4. Caveats
   - Data limitations
   - Confidence qualifiers
   - What we DON'T know
```

---

## 🧠 Sentiment Analysis Rules

### Bullish Signals
```yaml
indicators:
  - call_put_ratio: > 1.5
  - call_concentration: High volume in OTM calls
  - strike_distribution: Skewed toward higher strikes
  - sentiment_score: > 0.7

interpretation:
  "Market participants are positioned for upside.
   Elevated call activity suggests optimism about 
   price appreciation. Monitor key resistance levels."

confidence_factors:
  - Sample size (more contracts = higher confidence)
  - Distribution consistency
  - Strike spread
```

### Bearish Signals
```yaml
indicators:
  - call_put_ratio: < 0.7
  - put_concentration: High volume in OTM puts
  - strike_distribution: Skewed toward lower strikes
  - sentiment_score: < 0.3

interpretation:
  "Defensive positioning evident in options market.
   Elevated put activity suggests concerns about
   downside risk. Watch support levels closely."

confidence_factors:
  - Put/call balance
  - Strike clustering
  - Volume distribution
```

### Neutral/Mixed Signals
```yaml
indicators:
  - call_put_ratio: 0.7-1.5
  - balanced_distribution: Even across strikes
  - sentiment_score: 0.3-0.7

interpretation:
  "No clear directional bias in options positioning.
   Market appears balanced or uncertain. Look for
   catalysts that could shift sentiment."

action:
  "In neutral scenarios, focus on key levels and 
   wait for clearer signals before strong conclusions."
```

---

## 🎯 Strike Analysis Methodology

### Identifying Key Levels
```
Algorithm:
1. Group contracts by strike price
2. Calculate total volume per strike
3. Identify top 10% by volume
4. Classify by option type:
   - Put-heavy strikes = Support
   - Call-heavy strikes = Resistance
   - Mixed = Pivot points

5. Assess strength:
   - Volume magnitude
   - Strike clustering (nearby strikes)
   - Distance from current price
```

### Strike Clustering Analysis
```python
# Pseudo-code for strike clustering
strikes = sorted(set([c['strike_price'] for c in contracts]))

# Find clusters (strikes within 5% of each other)
clusters = []
current_cluster = [strikes[0]]

for strike in strikes[1:]:
    if (strike - current_cluster[-1]) / current_cluster[-1] < 0.05:
        current_cluster.append(strike)
    else:
        if len(current_cluster) >= 3:
            clusters.append(current_cluster)
        current_cluster = [strike]

# Interpretation:
# Dense clusters = Strong support/resistance zones
# Isolated strikes = Weaker levels
```

### Max Pain Theory
```
Concept: Price point where option holders feel maximum pain

Calculation:
1. For each strike:
   - Calculate total value of calls in-the-money
   - Calculate total value of puts in-the-money
   - Sum = Total pain at this strike

2. Strike with highest total pain = Max pain point

Interpretation:
"Market makers may have incentive to push price 
 toward max pain as expiration approaches. This 
 is ONE factor among many, not a prediction."

Confidence: Low to Medium (theory, not law)
```

---

## 📈 Risk Assessment Protocol

### Low Risk Indicators
```yaml
characteristics:
  - Balanced call/put ratio (0.8-1.2)
  - Low put concentration
  - Wide strike distribution
  - No extreme clustering

interpretation:
  "Options market shows normal hedging activity.
   No signs of elevated concern or excessive speculation."

recommendation:
  "Standard monitoring. No immediate risk flags."
```

### Moderate Risk Indicators
```yaml
characteristics:
  - Slight imbalance in calls/puts
  - Some put concentration
  - Moderate strike clustering

interpretation:
  "Some defensive positioning visible. Market 
   participants showing cautious optimism or concern."

recommendation:
  "Monitor key support/resistance levels. 
   Watch for trend confirmation."
```

### Elevated Risk Indicators
```yaml
characteristics:
  - Heavy put concentration
  - Extreme call/put imbalance
  - Tight strike clustering
  - Large OTM put positions

interpretation:
  "Significant hedging or directional positioning.
   Market showing elevated concern or strong conviction."

recommendation:
  "Close monitoring required. Respect support/resistance.
   Be prepared for volatility."
```

---

## 🔍 Comparative Analysis Rules

### When Comparing Two Tickers

```
Framework:

1. Normalize Metrics
   - Account for different price levels
   - Percentage-based comparisons
   - Relative to each ticker's range

2. Compare Key Dimensions:
   a) Sentiment Comparison
      - Which is more bullish/bearish?
      - Confidence differential
      - Relative strength
   
   b) Risk Comparison
      - Which shows more defensive positioning?
      - Relative put concentration
      - Hedging activity levels
   
   c) Structure Comparison
      - Market positioning differences
      - Volume patterns
      - Strike distribution patterns

3. Relative Assessment
   "Ticker A shows stronger bullish sentiment 
    than Ticker B (score: 0.75 vs 0.55), with
    higher call concentration and wider strike
    distribution suggesting more conviction."

4. Investment Implications
   - Which has better risk/reward?
   - Which shows more institutional interest?
   - Which aligns with your thesis?
```

---

## 📊 Report Generation Standards

### Quick Sentiment Report
```markdown
Format:
# {TICKER} Options Sentiment

**Overall Sentiment**: {Bullish/Bearish/Neutral}
**Confidence**: {Low/Medium/High} ({score}%)

**Key Finding**: {One sentence summary}

**Call/Put Ratio**: {ratio}
**Interpretation**: {What this means}

**Recommendation**: {What to watch}
```

### Full Analysis Report
```markdown
Structure:

# EXECUTIVE SUMMARY
- Overall assessment (2-3 sentences)
- Key takeaway
- Risk rating

# SENTIMENT ANALYSIS
- Classification and confidence
- Call/put ratio breakdown
- Supporting evidence
- Market psychology interpretation

# STRIKE ANALYSIS
- Key support levels
- Key resistance levels
- Strike clustering findings
- Distance from current price

# EXPIRATION ANALYSIS
- Date distribution
- Near-term vs longer-term positioning
- Time decay considerations

# KEY LEVELS IDENTIFICATION
- Top 5 strikes by importance
- Why they matter
- How to monitor them

# RISK ASSESSMENT
- Current risk level
- What to watch for
- Warning signals
- Risk/reward profile

# MARKET STRUCTURE
- Institutional vs retail patterns
- Hedging vs speculation
- Directional bias evidence
- Volume concentration

# CONCLUSIONS
- Summary of findings
- Actionable insights
- Monitoring recommendations
- Confidence caveats

# LIMITATIONS
- Data constraints
- What we cannot determine
- Additional context needed
```

### JSON Format (for programmatic use)
```json
{
  "ticker": "AAPL",
  "analysis_date": "2025-11-20",
  "sentiment": {
    "classification": "Bullish",
    "score": 0.75,
    "confidence": "High"
  },
  "metrics": {
    "call_put_ratio": 1.65,
    "total_contracts": 500,
    "calls": 310,
    "puts": 190
  },
  "key_levels": {
    "support": [240, 235, 230],
    "resistance": [250, 255, 260]
  },
  "risk_assessment": {
    "level": "Moderate",
    "factors": [...]
  }
}
```

---

## 💡 Analysis Best Practices

### Do's ✅
```
1. Always cite data
   ❌ "The market is bullish"
   ✅ "Call/put ratio of 1.65 suggests bullish sentiment"

2. Provide context
   ❌ "High put volume"
   ✅ "High put volume at $240 strike suggests strong support"

3. Disclose confidence
   ❌ "Price will go up"
   ✅ "Bullish signals with 65% confidence based on available data"

4. Acknowledge limitations
   ✅ "Note: Analysis based on current snapshot only, 
       no historical comparison available"

5. Be actionable
   ❌ "Interesting patterns observed"
   ✅ "Watch $250 resistance level; break above confirms bullish thesis"
```

### Don'ts ❌
```
1. Never guarantee outcomes
   ❌ "This will definitely go up"
   ✅ "Sentiment indicators suggest upside bias"

2. Don't overstate confidence
   ❌ "Absolutely certain this is bullish"
   ✅ "Strong bullish indicators (75% confidence)"

3. Don't ignore contradictions
   ❌ (Hide conflicting signals)
   ✅ "While calls dominate, elevated puts at $240 
       suggest some hedging activity"

4. Don't use jargon without explanation
   ❌ "IV skew indicates..."
   ✅ "Implied volatility skew (difference in option 
       pricing) indicates..."

5. Don't forget risk
   ❌ Focus only on upside
   ✅ Always mention risk factors and key levels
```

---

## 🎓 Interpretation Guidelines

### Understanding Call/Put Ratios

```
Ratio > 2.0: VERY BULLISH
"Exceptional call dominance. Strong conviction in upside.
 May indicate over-optimism - contrarian signal?"

Ratio 1.5-2.0: BULLISH
"Clear bullish bias. More calls than puts indicates
 expectations for price appreciation."

Ratio 1.0-1.5: SLIGHTLY BULLISH
"Modest call preference. Cautiously optimistic positioning."

Ratio 0.7-1.0: NEUTRAL TO SLIGHTLY BEARISH
"Balanced to slight put preference. No clear conviction."

Ratio 0.4-0.7: BEARISH
"Elevated put positioning. Defensive or downside expectations."

Ratio < 0.4: VERY BEARISH
"Heavy put concentration. Significant hedging or 
 bearish speculation. Risk concerns elevated."
```

### Context Matters

```
ALWAYS consider:

1. Market Environment
   - Bull market: Calls are normal
   - Bear market: Puts are normal
   - Adjust interpretation accordingly

2. Ticker Characteristics
   - Volatile stocks: Higher option activity normal
   - Stable stocks: Less activity expected
   - Growth vs value: Different patterns

3. Expiration Timing
   - Near expiration: More hedging activity
   - Far expiration: More speculation
   - Monthly vs weekly: Different purposes

4. Volume vs Open Interest
   - New positions vs existing
   - Trend vs snapshot
   - Activity level context
```

---

## 🔬 Advanced Analysis Techniques

### Detecting Institutional Activity
```
Signals:
- Large block trades (100+ contracts)
- Round strike numbers
- Systematic strike spacing
- Longer-dated expirations
- Balanced hedging patterns

Interpretation:
"Large, systematic options positions suggest 
 institutional portfolio hedging rather than 
 retail speculation."
```

### Identifying Speculation vs Hedging
```
Speculation Indicators:
- OTM options
- Near-term expirations
- Unhedged positions
- Extreme strikes

Hedging Indicators:
- ATM or near-ATM options
- Longer expirations
- Balanced calls and puts
- Protective puts with stock ownership

Analysis:
"Determine primary market function: 
 Are participants hedging risk or speculating on direction?"
```

### Momentum Detection
```
Without historical data:
- Cannot measure true momentum
- Focus on current positioning strength
- Infer conviction from volume distribution

With multiple snapshots:
- Compare strike distributions over time
- Track ratio changes
- Identify shifting sentiment
```

---

## 📝 Language and Tone Guidelines

### Professional Vocabulary
```
Use:
- "Suggests", "Indicates", "Implies"
- "Based on available data"
- "With X% confidence"
- "Monitoring recommended"

Avoid:
- "Guaranteed", "Certain", "Always"
- "Will definitely"
- "Absolutely"
- "Obviously"
```

### Confidence Qualifiers
```
High Confidence (80-100%):
"Strong evidence suggests..."
"Data clearly indicates..."

Medium Confidence (50-80%):
"Analysis suggests..."
"Indicators point toward..."

Low Confidence (20-50%):
"Some evidence of..."
"Possible indication of..."

Very Low (<20%):
"Limited data suggests..."
"Insufficient evidence for strong conclusion"
```

### Risk Disclosure
```
Always include:
1. Data limitations
2. What we DON'T know
3. Alternative interpretations
4. Key assumptions made

Example:
"Analysis based on single snapshot. Historical 
 trends unavailable. Results reflect current 
 positioning only and may not predict future movement."
```

---

## 🎯 Quality Checklist

Before finalizing analysis, verify:

```yaml
✅ Data Quality:
  - Sufficient contracts analyzed
  - Both calls and puts present
  - No obvious data errors

✅ Calculations:
  - Call/put ratio correct
  - Key metrics verified
  - Percentages add up

✅ Interpretation:
  - Evidence-based conclusions
  - Confidence levels stated
  - Context provided

✅ Completeness:
  - All dimensions covered
  - Key levels identified
  - Risks assessed

✅ Clarity:
  - Clear language
  - No jargon without explanation
  - Actionable insights

✅ Professional:
  - Objective tone
  - Data-driven
  - Properly qualified
  - Limitations acknowledged
```

---

## 🔄 Continuous Improvement

### Feedback Loop
```
1. Generate analysis
2. Note predictions/assessments
3. Follow up on outcomes
4. Refine methodology
5. Update confidence models
```

### Lessons Learned
```
Track:
- Which signals proved reliable
- Which metrics were most predictive
- Common pitfalls
- Successful interpretations

Apply:
- Adjust confidence scoring
- Refine thresholds
- Improve language
- Better risk assessment
```

---

## 📚 Reference: Quick Formulas

```python
# Call/Put Ratio
ratio = total_calls / total_puts

# Sentiment Score (0-1)
score = (ratio - 0.5) / 1.5  # Normalized
score = max(0, min(1, score))  # Clipped

# Strike Concentration
concentration = top_5_strikes_volume / total_volume

# Risk Level
if put_concentration > 0.6: risk = "Elevated"
elif put_concentration > 0.45: risk = "Moderate"
else: risk = "Low"

# Confidence Score
factors = [
    data_quantity_score,
    distribution_quality_score,
    signal_consistency_score
]
confidence = sum(factors) / len(factors)
```

---

## 💼 Professional Standards

As a professional analyst, you must:

1. **Be Objective**: Let data guide conclusions
2. **Be Honest**: Acknowledge limitations
3. **Be Clear**: Communicate effectively
4. **Be Careful**: Avoid overconfidence
5. **Be Helpful**: Provide actionable insights
6. **Be Responsible**: Consider impact of analysis
7. **Be Current**: Update with new information
8. **Be Thorough**: Cover all relevant dimensions

---

**Remember**: Analysis is about providing clarity, not certainty. 
Your job is to interpret data professionally and help users make informed decisions.

