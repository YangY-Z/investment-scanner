---
name: portfolio-daily-report
description: Daily 10 AM portfolio analysis for long-term investor — scans holdings (格力/伊利/五粮液), checks technical signals, compares with market benchmarks, and generates adjustment suggestions.
version: 1.0.0
author: Hermes Agent
---

# Portfolio Daily Report — 持仓日报

Daily 10 AM analysis tailored for a long-term value investor holding 格力电器, 伊利股份, 五粮液, plus fund positions.

## Investor Profile

- **Style**: 长线价值投资，不频繁交易
- **Risk tolerance**: 中低，能承受 -10% 浮亏
- **Preferred signals**: RSI超卖 + 质量过关 → 加仓；RSI超买 + 盈利 → 减仓
- **Portfolio size**: ~¥130K 股票 + ~¥180K 基金

## Current Holdings

| 股票 | 股数 | 成本 | 类型 |
|---|---|---|---|
| 格力电器 000651 | 1400 | ¥39.54 | 家电龙头 |
| 伊利股份 600887 | 1200 | ¥26.77 | 消费刚需 |
| 五粮液 000858 | 400 | ¥91.88 | 白酒龙头 |

## Report Structure

Each daily report includes:

1. **Market overview** — 上证指数/沪深300 涨跌 + 市场温度
2. **Holding analysis** — 每只持仓的技术面(RSI/MACD/MA20/背离) + 操作建议
3. **Watchlist highlights** — 监控池中质量最优的背离信号
4. **Adjustment suggestions** — 具体的调仓/加减仓建议
5. **Risk alerts** — 止损预警、重大事件提醒

## Decision Rules

| 信号 | 操作 |
|---|---|
| RSI < 20 + 质量👍以上 | 🔥 加仓信号 |
| RSI < 30 + 横盘 | 👀 关注，不加 |
| RSI > 70 + 盈利 > 15% | 💰 减仓信号 |
| 跌破MA60 + RSI < 30 | ⚠️ 风险预警 |
| 无信号 | 持有不动 |
