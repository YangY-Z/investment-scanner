#!/usr/bin/env python3
"""
持仓日报 — 每日10点分析
覆盖: 格力/伊利/五粮液/美的 + 8只基金
"""

import requests, numpy as np
from datetime import datetime

HOLDINGS = [
    {"code": "000651", "name": "格力电器", "shares": 1400, "cost": 39.54, "qq": "sz000651"},
    {"code": "600887", "name": "伊利股份", "shares": 1200, "cost": 26.77, "qq": "sh600887"},
    {"code": "000858", "name": "五粮液",   "shares": 400,  "cost": 91.88, "qq": "sz000858"},
    {"code": "000333", "name": "美的集团", "shares": 100,  "cost": 71.10, "qq": "sz000333"},
]

FUNDS = [
    {"name": "上银慧元利债券A",      "amount": 42251,  "pnl": 718,   "type": "纯债"},
    {"name": "华泰柏瑞红利低波ETF",  "amount": 35980,  "pnl": -995,  "type": "指数"},
    {"name": "长城半导体混合A",      "amount": 30186,  "pnl": 6557,  "type": "股票"},
    {"name": "天弘红利低波100ETF",   "amount": 28840,  "pnl": 446,   "type": "指数"},
    {"name": "南方红利低波50ETF",    "amount": 15188,  "pnl": 82,    "type": "指数"},
    {"name": "摩根纳斯达克100 QDII", "amount": 10808,  "pnl": 455,   "type": "海外"},
    {"name": "国联日日盈货币C",      "amount": 10270,  "pnl": 270,   "type": "货基"},
    {"name": "华泰保兴尊睿债券A",    "amount": 10259,  "pnl": 259,   "type": "固收+"},
]

FUNDS_TOTAL = sum(f["amount"] for f in FUNDS)
FUNDS_PNL = sum(f["pnl"] for f in FUNDS)


def fetch_kline(qq_code):
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={qq_code},day,,,120,qfq"
    r = requests.get(url, headers={"Referer": "https://gu.qq.com/"}, timeout=15)
    return r.json()["data"][qq_code].get("qfqday") or r.json()["data"][qq_code].get("day") or []


def analyze(klines):
    close = np.array([float(k[2]) for k in klines], dtype=np.float64)
    high = np.array([float(k[3]) for k in klines])
    n = len(close)

    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta>0,delta,0.0); loss = np.where(delta<0,-delta,0.0)
    ag=np.zeros(n); al=np.zeros(n); ag[0]=gain[0]; al[0]=loss[0]
    for i in range(1,n): ag[i]=1/14*gain[i]+13/14*ag[i-1]; al[i]=1/14*loss[i]+13/14*al[i-1]
    rsi=100-100/(1+np.where(al==0,100.0,ag/al))

    ema12=np.zeros(n); ema26=np.zeros(n); ema12[0]=close[0]; ema26[0]=close[0]
    for i in range(1,n): ema12[i]=2/13*close[i]+11/13*ema12[i-1]; ema26[i]=2/27*close[i]+25/27*ema26[i-1]
    dif=ema12-ema26; dea=np.zeros(n); dea[0]=dif[0]
    for i in range(1,n): dea[i]=2/10*dif[i]+8/10*dea[i-1]
    hist=2*(dif-dea)

    return {
        "price": round(close[-1],2), "rsi": round(rsi[-1],1),
        "hist": round(hist[-1],3), "ma20": round(close[-20:].mean(),2),
        "ma60": round(close[-60:].mean(),2), "drawdown": round((1-close[-1]/high.max())*100,1),
    }


def get_index():
    try:
        url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000300,day,,,5,qfq"
        r = requests.get(url, headers={"Referer": "https://gu.qq.com/"}, timeout=15)
        k = r.json()["data"]["sh000300"]["day"]
        return round(float(k[-1][2]),2), round((float(k[-1][2])/float(k[-2][2])-1)*100,2)
    except: return None, None


def main():
    now = datetime.now()
    print(f"📊 持仓日报 — {now.strftime('%Y年%m月%d日 %H:%M')}")
    print("=" * 60)

    idx_p, idx_c = get_index()
    if idx_p:
        print(f"\n📈 沪深300: {idx_p}  {'+' if idx_c>0 else ''}{idx_c}%")
        if idx_c > 1: mood = "🟢 市场强势"
        elif idx_c > 0: mood = "🟢 温和上涨"
        elif idx_c > -1: mood = "⚪ 横盘"
        else: mood = "🔴 下跌"
        print(f"   市场情绪: {mood}")

    total_stock = 0; total_pnl = 0

    print(f"\n{'─'*60}")
    print(f"{'股票':<8} {'现价':>8} {'RSI':>6} {'盈亏':>9} {'状态':<12} {'建议':<10}")
    print(f"{'─'*60}")

    for h in HOLDINGS:
        kl = fetch_kline(h["qq"])
        if not kl: continue
        a = analyze(kl)
        v = a["price"]*h["shares"]; p = (a["price"]-h["cost"])*h["shares"]
        pp = (a["price"]/h["cost"]-1)*100
        total_stock += v; total_pnl += p

        r = a["rsi"]
        if r<20: st="🔴极度超卖"
        elif r<30: st="🟡超卖"
        elif r>80: st="🔴极度超买"
        elif r>70: st="🟡超买"
        else: st="⚪正常"

        if r<20 and pp<-5: adv="🔥加仓"
        elif r<30 and a["price"]>a["ma20"]: adv="👀观察"
        elif r<30: adv="⏳等待"
        elif r>70 and pp>15: adv="💰减仓"
        elif r>60 and a["price"]>a["ma20"]: adv="🟢持有"
        else: adv="持有"

        print(f"{h['name']:<8} ¥{a['price']:<7.2f} {r:<5.1f} {p:>+9.0f} {st:<12} {adv:<10}")
        print(f"  MA20=¥{a['ma20']}  MA60=¥{a['ma60']}  回撤={a['drawdown']}%  MACD={a['hist']}")

    print(f"{'─'*60}")
    ta = total_stock + FUNDS_TOTAL
    tp = total_pnl + FUNDS_PNL
    print(f"股票: ¥{total_stock:,}  基金: ¥{FUNDS_TOTAL:,}  总资产: ¥{ta:,}")
    print(f"股票盈亏: ¥{total_pnl:+,}  基金盈亏: ¥{FUNDS_PNL:+,}  总盈亏: ¥{tp:+,}")

    print(f"\n📊 基金:")
    for f in FUNDS:
        print(f"  {f['name']:<24} ¥{f['amount']:>8,}  {f['pnl']:>+6}  [{f['type']}]")
    print(f"  {'合计':<24} ¥{FUNDS_TOTAL:>8,}  {FUNDS_PNL:>+6}")

    print(f"\n📋 建议:")
    sug = []
    for h in HOLDINGS:
        kl = fetch_kline(h["qq"])
        if not kl: continue
        a = analyze(kl); pp = (a["price"]/h["cost"]-1)*100
        if a["rsi"]<25 and pp<-5:
            sug.append(f"🔥 {h['name']}: RSI={a['rsi']}超卖+亏损{pp:.1f}%，可加仓")
        elif a["rsi"]>70 and pp>15:
            sug.append(f"💰 {h['name']}: RSI={a['rsi']}超买+盈利{pp:.1f}%，可减仓")

    if sug:
        for s in sug: print(f"  {s}")
    else:
        print("  今日无操作建议，持有不动。")

    print(f"\n⚠️ 风险:")
    has_risk = False
    for h in HOLDINGS:
        kl = fetch_kline(h["qq"])
        if not kl: continue
        a = analyze(kl)
        if a["price"]<a["ma60"] and a["rsi"]<30:
            print(f"  {h['name']}: 跌破MA60+超卖，止损 ¥{h['cost']*0.9:.2f}")
            has_risk = True
        elif a["drawdown"]>20:
            print(f"  {h['name']}: 回撤{a['drawdown']}%，深度套牢")
            has_risk = True
    if not has_risk:
        print("  无重大风险。")

    print(f"\n{'='*60}")
    print(f"风格: 长线价值 | 明天10:00再见")


if __name__ == "__main__":
    main()
