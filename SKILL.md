---
name: bottom-divergence-scanner
description: A+H stock bottom divergence monitoring system — scans CSI 300 + Hang Seng Index for RSI/MACD bullish divergence signals, cross-referenced with quality scores (ROE, gross margin, revenue growth, cash flow). Daily automated scans with weekly quality updates.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Bottom Divergence Scanner — A+H 底部背离监控系统

Automated monitoring system that scans CSI 300 (A-shares) + Hang Seng Index (HK stocks) for bottom divergence signals, ranked by quality metrics.

## Core Logic

```
Divergence Signal                Quality Filter
─────────────────                ──────────────
Price makes lower low     +      ROE > 15%
RSI/MACD makes higher low       Gross margin > 30%
                                 Revenue growth > 10%
        ↓                        Cash flow positive
                                 
  Combined Score = Tech(60%) + Quality(40%)
  
  ⭐70+  →  High confidence buy
  👍50-69 →  Worth watching  
  ⚠️30-49 →  Wait
  ❌<30  →  Skip (value trap)
```

## Architecture

```
Weekly (Sun 20:30):
  quality_scorer.py → quality_scores.json (369 stocks)

Daily (Mon-Fri 15:30):
  monitor_divergence.py → reads quality cache → ranked signals → push
```

## Data Sources

| Market | K-line API | Financial API |
|---|---|---|
| A-shares | East Money (push2his) | akshare stock_yjbb_em (batch) |
| HK stocks | Tencent Finance (ifzq) | akshare stock_financial_hk_analysis |

## Key Metrics Tracked

**Technical:** RSI(14), MACD(12/26/9), local lows detection (40-day window), divergence comparison

**Quality (0-100):**
- ROE (30pts): >20%=30, >15%=25, >10%=15, >5%=8
- Revenue Growth (20pts): >30%=20, >20%=16, >10%=12
- Profit Growth (20pts): same tiers
- Gross Margin (15pts): >60%=15, >40%=12, >25%=8
- Cash Flow Quality (15pts): CF/EPS ratio

## Limitations

- A-share quality uses Q1 quarterly data (ROE not annualized — banks unfairly penalized)
- HK quality uses latest annual report
- East Money API rate-limits after ~10 rapid scans; daily cron has no issue
- Only covers CSI 300 + HSI (~390 stocks)
- No volume confirmation built in

## Reference Scripts

See linked files:
- `scripts/monitor_divergence.py` — Main scanner
- `scripts/quality_scorer.py` — Quality scoring system
