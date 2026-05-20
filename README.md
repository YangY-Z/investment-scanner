# Investment Scanner — A+H 底部背离监控系统

自动化扫描沪深300 + 恒生指数成分股，检测 RSI/MACD 底部背离信号，并结合 ROE、毛利率、营收增速、现金流等财务指标进行质量评分排序。

## 核心逻辑

```
背离信号                    质量过滤
─────────────────          ─────────────
价格创新低              +    ROE > 15%
RSI/MACD 拒绝跟跌            毛利率 > 30%
                             营收增速 > 10%
       ↓                     现金流为正

  综合得分 = 技术面(60%) + 质量面(40%)
```

## 文件结构

| 文件 | 说明 |
|---|---|
| `SKILL.md` | 系统架构和评分规则 |
| `scripts/monitor_divergence.py` | 主扫描脚本 |
| `scripts/quality_scorer.py` | 质量评分脚本 |

## 使用方式

```bash
# 质量评分（每周一次）
python3 scripts/quality_scorer.py

# 背离扫描（每天收盘后）
python3 scripts/monitor_divergence.py
```

## 数据源

- A股日K：东方财富 API
- 港股日K：腾讯财经 API
- A股财报：akshare stock_yjbb_em（批量）
- 港股财报：akshare stock_financial_hk_analysis_indicator_em

## 依赖

```bash
pip install akshare numpy requests
```

## License

MIT
