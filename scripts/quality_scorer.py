#!/usr/bin/env python3
"""
A股+港股质量评分器 — 每周更新
A股: stock_yjbb_em 批量获取
港股: stock_financial_hk_analysis_indicator_em 逐只获取
"""

import akshare as ak
import json
import os
import time
import random
from datetime import datetime, date

CACHE_FILE = os.path.expanduser("~/./cache/quality_scores.json")

# 恒生指数成分股
HSI_STOCKS = [
    ("00001","长和"),("00002","中电控股"),("00003","中华煤气"),("00005","汇丰控股"),
    ("00006","电能实业"),("00011","恒生银行"),("00012","恒基地产"),("00016","新鸿基地产"),
    ("00017","新世界"),("00019","太古A"),("00027","银河娱乐"),("00066","港铁"),
    ("00083","信和置业"),("00101","恒隆地产"),("00175","吉利汽车"),("00241","阿里健康"),
    ("00267","中信股份"),("00268","金蝶国际"),("00285","比亚迪电子"),("00288","万洲国际"),
    ("00291","华润啤酒"),("00316","东方海外"),("00322","康师傅"),("00386","中石化"),
    ("00388","港交所"),("00669","创科实业"),("00688","中国海外"),("00700","腾讯"),
    ("00762","中国联通"),("00788","中国铁塔"),("00823","领展"),("00857","中国石油"),
    ("00868","信义光能"),("00881","中升控股"),("00883","中海油"),("00914","海螺水泥"),
    ("00939","建设银行"),("00941","中国移动"),("00960","龙湖集团"),("00968","信义玻璃"),
    ("00981","中芯国际"),("00992","联想集团"),("01038","长江基建"),("01044","恒安国际"),
    ("01088","中国神华"),("01093","石药集团"),("01099","国药控股"),("01109","华润置地"),
    ("01113","长实集团"),("01177","中国生物制药"),("01209","华润万象"),("01211","比亚迪"),
    ("01288","农业银行"),("01299","友邦保险"),("01378","中国宏桥"),("01398","工商银行"),
    ("01810","小米"),("01876","百威亚太"),("01928","金沙中国"),("01929","周大福"),
    ("01997","九龙仓置业"),("02007","碧桂园"),("02015","理想汽车"),("02018","瑞声科技"),
    ("02020","安踏体育"),("02269","药明生物"),("02313","申洲国际"),("02318","中国平安"),
    ("02319","蒙牛乳业"),("02331","李宁"),("02382","舜宇光学"),("02388","中银香港"),
    ("02628","中国人寿"),("02688","新奥能源"),("02899","紫金矿业"),("03690","美团"),
    ("03968","招商银行"),("03988","中国银行"),("06098","碧桂园服务"),("06618","京东健康"),
    ("06690","海尔智家"),("06862","海底捞"),("09618","京东"),("09626","哔哩哔哩"),
    ("09633","农夫山泉"),("09888","百度"),("09901","新东方"),("09961","携程"),
    ("09988","阿里巴巴"),("09999","网易"),
]

# === 评分规则 ===

def safe_float(v):
    try:
        f = float(v)
        return f if f == f else None
    except (ValueError, TypeError):
        return None

def score_roe(roe):
    if roe is None: return 0
    if roe >= 20: return 30
    if roe >= 15: return 25
    if roe >= 10: return 15
    if roe >= 5: return 8
    return 0

def score_revenue_growth(g):
    if g is None: return 0
    if g >= 30: return 20
    if g >= 20: return 16
    if g >= 10: return 12
    if g >= 0: return 6
    return 2

def score_profit_growth(g):
    if g is None: return 0
    if g >= 30: return 20
    if g >= 20: return 16
    if g >= 10: return 12
    if g >= 0: return 6
    return 0

def score_gross_margin(m):
    if m is None: return 0
    if m >= 60: return 15
    if m >= 40: return 12
    if m >= 25: return 8
    if m >= 10: return 4
    return 1

def score_cash_flow(cf_ps, eps):
    if not eps or eps == 0 or cf_ps is None: return 5
    ratio = cf_ps / abs(eps)
    if ratio >= 1.0: return 15
    if ratio >= 0.8: return 12
    if ratio >= 0.5: return 8
    if ratio > 0: return 4
    return 0

def quality_label(score):
    if score >= 70: return "⭐优质"
    if score >= 50: return "👍良好"
    if score >= 30: return "⚠️一般"
    return "❌差"


def score_a_shares():
    print("\n📊 A股 — 沪深300")
    try:
        cons = ak.index_stock_cons(symbol="000300")
        csi_codes = set(cons["品种代码"].tolist())
        print(f"  成分股: {len(csi_codes)} 只")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return {}

    today = date.today()
    for m, d in [(12,31), (9,30), (6,30), (3,31)]:
        q_end = date(today.year, m, d)
        if q_end <= today:
            report_date = q_end.strftime("%Y%m%d")
            break
    else:
        report_date = f"{today.year-1}1231"

    try:
        df = ak.stock_yjbb_em(date=report_date)
        print(f"  财报数据: {len(df)} 只")
    except Exception as e:
        print(f"  ❌ 财报获取失败: {e}")
        return {}

    scores = {}
    for _, row in df.iterrows():
        code = str(row["股票代码"]).zfill(6)
        if code not in csi_codes:
            continue
        name = row.get("股票简称", "")
        eps = safe_float(row.get("每股收益"))
        roe = safe_float(row.get("净资产收益率"))
        rev_g = safe_float(row.get("营业总收入-同比增长"))
        profit_g = safe_float(row.get("净利润-同比增长"))
        gm = safe_float(row.get("销售毛利率"))
        cf_ps = safe_float(row.get("每股经营现金流量"))

        total = (score_roe(roe) + score_revenue_growth(rev_g) +
                 score_profit_growth(profit_g) + score_gross_margin(gm) +
                 score_cash_flow(cf_ps, eps))

        scores[code] = {
            "name": name, "score": int(total), "label": quality_label(total),
            "roe": round(roe,1) if roe else None,
            "rev_growth": round(rev_g,1) if rev_g else None,
            "profit_growth": round(profit_g,1) if profit_g else None,
            "gross_margin": round(gm,1) if gm else None,
            "cf_ratio": round(cf_ps/eps,2) if (cf_ps and eps and eps!=0) else None,
            "market": "A",
        }
    return scores


def score_hk_shares():
    print("\n📊 港股 — 恒生指数")
    print(f"  成分股: {len(HSI_STOCKS)} 只")

    scores = {}
    success = 0
    for i, (code, name) in enumerate(HSI_STOCKS):
        try:
            df = ak.stock_financial_hk_analysis_indicator_em(symbol=code)
            if df.empty: continue
            latest = df[df["DATE_TYPE_CODE"] == "001"].iloc[0]
            eps = safe_float(latest.get("BASIC_EPS"))
            roe = safe_float(latest.get("ROE_AVG"))
            rev_g = safe_float(latest.get("OPERATE_INCOME_YOY"))
            profit_g = safe_float(latest.get("HOLDER_PROFIT_YOY"))
            gm = safe_float(latest.get("GROSS_PROFIT_RATIO"))
            cf_ps = safe_float(latest.get("PER_NETCASH_OPERATE"))

            total = (score_roe(roe) + score_revenue_growth(rev_g) +
                     score_profit_growth(profit_g) + score_gross_margin(gm) +
                     score_cash_flow(cf_ps, eps))

            scores[code] = {
                "name": name, "score": int(total), "label": quality_label(total),
                "roe": round(roe,1) if roe else None,
                "rev_growth": round(rev_g,1) if rev_g else None,
                "profit_growth": round(profit_g,1) if profit_g else None,
                "gross_margin": round(gm,1) if gm else None,
                "cf_ratio": round(cf_ps/eps,2) if (cf_ps and eps and eps!=0) else None,
                "market": "HK",
            }
            success += 1
        except Exception:
            pass
        if i % 20 == 19:
            print(f"  进度: {i+1}/{len(HSI_STOCKS)} ...")
        time.sleep(random.uniform(0.3, 0.8))

    print(f"  成功: {success}/{len(HSI_STOCKS)}")
    return scores


def main():
    print(f"📊 A+H 质量评分 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    all_scores = {}
    all_scores.update(score_a_shares())
    all_scores.update(score_hk_shares())

    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    output = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": len(all_scores),
        "scores": all_scores,
    }
    with open(CACHE_FILE, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    labels = {}
    for s in all_scores.values():
        lbl = s["label"]
        labels[lbl] = labels.get(lbl, 0) + 1

    a_count = sum(1 for s in all_scores.values() if s.get("market")=="A")
    hk_count = sum(1 for s in all_scores.values() if s.get("market")=="HK")

    print(f"\n✅ 评分完成: {len(all_scores)} 只 (A股: {a_count}, 港股: {hk_count})")
    for lbl, cnt in sorted(labels.items(), reverse=True):
        print(f"  {lbl}: {cnt} 只")
    print(f"💾 缓存: {CACHE_FILE}")


if __name__ == "__main__":
    main()
