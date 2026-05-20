#!/usr/bin/env python3
"""
A股+港股底部背离批量监控（沪深300 + 恒生指数）
A股：东方财富直连  港股：腾讯财经直连
"""

import requests
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random

# === 配置 ===
MAX_WORKERS = 8
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0
LOOKBACK_DAYS = 120
DIVERGENCE_WINDOW = 40

# 东方财富 A股日K
KLINE_URL_A = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
# 腾讯财经 港股日K
KLINE_URL_HK = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

# === 恒生指数成分股（硬编码） ===
HSI_STOCKS = [
    ("00001","长和"),("00002","中电控股"),("00003","香港中华煤气"),("00005","汇丰控股"),
    ("00006","电能实业"),("00011","恒生银行"),("00012","恒基地产"),("00016","新鸿基地产"),
    ("00017","新世界发展"),("00019","太古A"),("00027","银河娱乐"),("00066","港铁公司"),
    ("00083","信和置业"),("00101","恒隆地产"),("00175","吉利汽车"),("00241","阿里健康"),
    ("00267","中信股份"),("00268","金蝶国际"),("00285","比亚迪电子"),("00288","万洲国际"),
    ("00291","华润啤酒"),("00316","东方海外"),("00322","康师傅"),("00386","中石化"),
    ("00388","港交所"),("00669","创科实业"),("00688","中国海外"),("00700","腾讯控股"),
    ("00762","中国联通"),("00788","中国铁塔"),("00823","领展房产基金"),("00857","中国石油"),
    ("00868","信义光能"),("00881","中升控股"),("00883","中海油"),("00914","海螺水泥"),
    ("00939","建设银行"),("00941","中国移动"),("00960","龙湖集团"),("00968","信义玻璃"),
    ("00981","中芯国际"),("00992","联想集团"),("01038","长江基建"),("01044","恒安国际"),
    ("01088","中国神华"),("01093","石药集团"),("01099","国药控股"),("01109","华润置地"),
    ("01113","长实集团"),("01177","中国生物制药"),("01209","华润万象"),("01211","比亚迪"),
    ("01288","农业银行"),("01299","友邦保险"),("01378","中国宏桥"),("01398","工商银行"),
    ("01810","小米集团"),("01876","百威亚太"),("01928","金沙中国"),("01929","周大福"),
    ("01997","九龙仓置业"),("02007","碧桂园"),("02015","理想汽车"),("02018","瑞声科技"),
    ("02020","安踏体育"),("02269","药明生物"),("02313","申洲国际"),("02318","中国平安"),
    ("02319","蒙牛乳业"),("02331","李宁"),("02382","舜宇光学"),("02388","中银香港"),
    ("02628","中国人寿"),("02688","新奥能源"),("02899","紫金矿业"),("03690","美团"),
    ("03968","招商银行"),("03988","中国银行"),("06098","碧桂园服务"),("06618","京东健康"),
    ("06690","海尔智家"),("06862","海底捞"),("09618","京东集团"),("09626","哔哩哔哩"),
    ("09633","农夫山泉"),("09888","百度集团"),("09901","新东方"),("09961","携程集团"),
    ("09988","阿里巴巴"),("09999","网易"),
]

# === 指标计算 ===

def calc_rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0); loss = np.where(delta < 0, -delta, 0.0)
    ag = np.zeros(n); al = np.zeros(n); ag[0] = gain[0]; al[0] = loss[0]
    a = 1.0 / period
    for i in range(1, n): ag[i] = a*gain[i] + (1-a)*ag[i-1]; al[i] = a*loss[i] + (1-a)*al[i-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(al == 0, 100.0, ag / al)
    return 100.0 - 100.0 / (1.0 + rs)


def calc_macd(close: np.ndarray):
    n = len(close)
    ema12 = np.zeros(n); ema26 = np.zeros(n)
    ema12[0] = close[0]; ema26[0] = close[0]
    for i in range(1, n):
        ema12[i] = 2/13*close[i] + 11/13*ema12[i-1]
        ema26[i] = 2/27*close[i] + 25/27*ema26[i-1]
    dif = ema12 - ema26
    dea = np.zeros(n); dea[0] = dif[0]
    for i in range(1, n): dea[i] = 2/10*dif[i] + 8/10*dea[i-1]
    hist = 2 * (dif - dea)
    return dif, dea, hist


def find_local_lows(arr: np.ndarray, window: int = 3) -> list:
    n = len(arr); lows = []
    for i in range(window, n - window):
        if arr[i] <= arr[i-window:i].min() and arr[i] < arr[i+1:i+1+window].min():
            lows.append(i)
    return lows


def detect_divergence(close: np.ndarray, rsi: np.ndarray, hist: np.ndarray) -> dict | None:
    W = DIVERGENCE_WINDOW
    tail_c = close[-W:]; tail_r = rsi[-W:]; tail_h = hist[-W:]
    price_lows = find_local_lows(tail_c, window=3)
    if len(price_lows) < 2:
        return None
    left, right = price_lows[-2], price_lows[-1]
    if tail_c[right] >= tail_c[left]:
        return None
    signals = {}
    if tail_r[right] > tail_r[left]:
        signals["rsi"] = {"prev_p": round(float(tail_c[left]),2), "cur_p": round(float(tail_c[right]),2),
                          "prev_rsi": round(float(tail_r[left]),1), "cur_rsi": round(float(tail_r[right]),1)}
    if tail_h[right] > tail_h[left]:
        signals["macd"] = {"prev_p": round(float(tail_c[left]),2), "cur_p": round(float(tail_c[right]),2),
                           "prev_h": round(float(tail_h[left]),3), "cur_h": round(float(tail_h[right]),3)}
    return signals if signals else None


def fetch_a_share(code: str, session: requests.Session) -> dict | None:
    secid = f"1.{code}" if code.startswith("6") else f"0.{code}"
    params = {"secid": secid, "fields1": "f1,f2,f3,f4,f5,f6",
              "fields2": "f51,f52,f53,f54,f55,f56,f57",
              "klt": "101", "fqt": "1",
              "end": datetime.now().strftime("%Y%m%d"), "lmt": LOOKBACK_DAYS + 20}
    time.sleep(random.uniform(0, 0.15))
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(KLINE_URL_A, params=params, timeout=15)
            if resp.status_code != 200:
                if attempt < MAX_RETRIES-1:
                    time.sleep(RETRY_BACKOFF*(2**attempt)+random.uniform(0,1))
                    continue
                return None
            data = resp.json()
            if data.get("rc") != 0: return None
            kd = data.get("data")
            if not kd or not kd.get("klines"): return None
            records = []
            for line in kd["klines"]:
                p = line.split(",")
                if len(p) < 5: continue
                records.append({"date": p[0], "close": float(p[2]), "high": float(p[3]), "low": float(p[4])})
            if len(records) < 50: return None
            return {"code": code, "name": kd.get("name",""), "records": records, "market": "A"}
        except Exception:
            if attempt < MAX_RETRIES-1:
                time.sleep(RETRY_BACKOFF*(2**attempt)+random.uniform(0,1))
    return None


def fetch_hk_share(code: str, session: requests.Session) -> dict | None:
    url = KLINE_URL_HK
    params = {"param": f"hk{code},day,,,{LOOKBACK_DAYS+20},qfq"}
    time.sleep(random.uniform(0, 0.15))
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, params=params,
                               headers={"Referer": "https://gu.qq.com/"}, timeout=15)
            if resp.status_code != 200:
                if attempt < MAX_RETRIES-1:
                    time.sleep(RETRY_BACKOFF*(2**attempt)+random.uniform(0,1))
                    continue
                return None
            data = resp.json()
            kd = data.get("data", {}).get(f"hk{code}")
            if not kd or not kd.get("day"): return None
            klines = kd["day"]
            records = []
            for k in klines:
                if len(k) < 5: continue
                records.append({"date": k[0], "close": float(k[2]), "high": float(k[3]), "low": float(k[4])})
            if len(records) < 50: return None
            return {"code": code, "name": kd.get("qt",{}).get(code,"") if isinstance(kd.get("qt"),dict) else "",
                    "records": records, "market": "HK"}
        except Exception:
            if attempt < MAX_RETRIES-1:
                time.sleep(RETRY_BACKOFF*(2**attempt)+random.uniform(0,1))
    return None


def get_csi300_stocks():
    import akshare as ak
    cons = ak.index_stock_cons(symbol="000300")
    return [(c, n) for c, n in zip(cons["品种代码"], cons["品种名称"])]


def scan_stocks(stocks, fetcher, label, session):
    print(f"\n📋 {label}: {len(stocks)} 只")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetcher, code, session): name for code, name in stocks}
        results = []; failed = 0; done = 0
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0: print(f"  {label} 进度: {done}/{len(stocks)} ...")
            try:
                data = future.result(timeout=30)
                if data and len(data["records"]) >= 50: results.append(data)
                else: failed += 1
            except Exception: failed += 1
    elapsed = time.time() - t0
    print(f"  {label}: 成功 {len(results)}, 失败 {failed}, 耗时 {elapsed:.0f}s")
    return results


def analyze_results(results):
    hits = []
    for r in results:
        close = np.array([d["close"] for d in r["records"]], dtype=np.float64)
        if np.isnan(close).any() or len(close) < 50: continue
        rsi_arr = calc_rsi(close)
        _, _, hist_arr = calc_macd(close)
        signal = detect_divergence(close, rsi_arr, hist_arr)
        if signal:
            hits.append({"code": r["code"], "name": r["name"], "market": r["market"],
                         "price": round(float(close[-1]),2),
                         "rsi": round(float(rsi_arr[-1]),1), "signal": signal})
    return hits


def load_quality_scores():
    import json, os
    cache = os.path.expanduser("~/./cache/quality_scores.json")
    if not os.path.exists(cache): return {}
    try:
        with open(cache) as f:
            data = json.load(f)
        return data.get("scores", {})
    except Exception: return {}


def main():
    print(f"🔍 底部背离扫描 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"⚡ A股东方财富 · 港股腾讯财经 · {MAX_WORKERS}并发")
    print("=" * 65)

    quality = load_quality_scores()
    if quality:
        print(f"📊 质量评分: {len(quality)} 只")

    all_hits = []

    try:
        a_stocks = get_csi300_stocks()
        session_a = requests.Session()
        session_a.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"})
        a_results = scan_stocks(a_stocks, fetch_a_share, "沪深300", session_a)
        session_a.close()
        hits_a = analyze_results(a_results)
        all_hits.extend(hits_a)
    except Exception as e:
        print(f"❌ 沪深300扫描失败: {e}")

    try:
        session_hk = requests.Session()
        hk_results = scan_stocks(HSI_STOCKS, fetch_hk_share, "恒生指数", session_hk)
        session_hk.close()
        hits_hk = analyze_results(hk_results)
        all_hits.extend(hits_hk)
    except Exception as e:
        print(f"❌ 恒生指数扫描失败: {e}")

    print(f"\n{'='*65}")
    a_sig = len([h for h in all_hits if h['market']=='A'])
    hk_sig = len([h for h in all_hits if h['market']=='HK'])
    print(f"🎯 扫描完成  A股:{a_sig}  港股:{hk_sig}  总计:{len(all_hits)}")
    print("=" * 65)

    if not all_hits:
        print("\n✅ 未检测到底背离信号。")
        return

    for h in all_hits:
        q = quality.get(h["code"], {})
        h["quality_score"] = q.get("score", 0)
        h["quality_label"] = q.get("label", "❓无数据")
        h["roe"] = q.get("roe")
        h["gross_margin"] = q.get("gross_margin")
        h["rev_growth"] = q.get("rev_growth")

    def combined_score(h):
        sig = h["signal"]
        tech = 100 if ("rsi" in sig and "macd" in sig) else (60 if "rsi" in sig else 30)
        return tech * 0.6 + h.get("quality_score", 0) * 0.4

    all_hits.sort(key=combined_score, reverse=True)

    print(f"\n⚠️  发现 {len(all_hits)} 只底部背离股票：\n")
    for h in all_hits:
        sig = h["signal"]
        has_rsi = "rsi" in sig; has_macd = "macd" in sig
        tech_tag = "RSI+MACD" if has_rsi and has_macd else ("RSI" if has_rsi else "MACD")
        mkt = "[HK]" if h["market"] == "HK" else "[A]"
        currency = "HK$" if h["market"] == "HK" else "¥"
        qlabel = h.get("quality_label", "")
        qscore = h.get("quality_score", 0)

        q_detail = ""
        if h["market"] == "A":
            parts = []
            if h.get("roe") is not None: parts.append(f"ROE={h['roe']}%")
            if h.get("gross_margin") is not None: parts.append(f"毛利={h['gross_margin']}%")
            if h.get("rev_growth") is not None: parts.append(f"营收={h['rev_growth']}%")
            q_detail = " | ".join(parts)

        print(f"  {tech_tag} {mkt} {h['name']}({h['code']})  "
              f"{currency}{h['price']}  RSI={h['rsi']}  [{qlabel} {qscore}分]")
        if q_detail:
            print(f"     📊 {q_detail}")
        if has_rsi:
            s = sig["rsi"]
            print(f"     RSI背离: {currency}{s['prev_p']}({s['prev_rsi']}) → {currency}{s['cur_p']}({s['cur_rsi']}) Δ={s['cur_rsi']-s['prev_rsi']:+.1f}")
        if has_macd:
            s = sig["macd"]
            print(f"     MACD背离: {currency}{s['prev_p']}({s['prev_h']}) → {currency}{s['cur_p']}({s['cur_h']})")
        print()

    print("💡 底部背离是潜在反转信号，建议结合成交量确认。")


if __name__ == "__main__":
    main()
