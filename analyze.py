"""
系统化技术分析 - 12项框架
手写所有指标计算，无pandas-ta依赖，兼容Python 3.10+
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import warnings
import time
import random

warnings.filterwarnings("ignore")

REFERENCE_MAP = {
    "TSLA":  {"index": "QQQ",  "sector": "QQQ"},
    "BRK-B": {"index": "SPY",  "sector": "SPY"},
    "GLD":   {"index": "SPY",  "sector": "UUP"},
    "CCJ":   {"index": "SPY",  "sector": "URA"},
    "FCX":   {"index": "SPY",  "sector": "CPER"},
}

STOCK_POOL = ["BRK-B", "TSLA", "GLD", "CCJ", "FCX"]


def calc_rsi(close, period=14):
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast    = close.ewm(span=fast,   adjust=False).mean()
    ema_slow    = close.ewm(span=slow,   adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def calc_atr(high, low, close, period=14):
    tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(com=period-1, min_periods=period).mean()


def calc_bbands(close, period=20, std=2.0):
    mid   = close.rolling(period).mean()
    sigma = close.rolling(period).std()
    upper = mid + std * sigma
    lower = mid - std * sigma
    bw    = (upper - lower) / mid * 100
    return upper, mid, lower, bw


def fetch_data(ticker, period="2y"):
    for attempt in range(3):
        try:
            df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
            if df is not None and len(df) >= 60:
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                return df
        except Exception as e:
            print(f"  [{ticker}] 第{attempt+1}次失败: {e}")
            time.sleep(random.uniform(1, 3))
    return pd.DataFrame()


def calc_slope(series, window=5):
    if len(series) < window:
        return 0.0
    y = series.iloc[-window:].values
    x = np.arange(window)
    return np.polyfit(x, y, 1)[0] / series.iloc[-1] * 100


def slope_label(slope):
    if slope > 0.05:  return "向上"
    if slope < -0.05: return "向下"
    return "走平"


def find_swing_points(series, order=10):
    arr = series.values
    h_idx = argrelextrema(arr, np.greater, order=order)[0]
    l_idx = argrelextrema(arr, np.less,    order=order)[0]
    highs = [(series.index[i], round(arr[i], 2)) for i in h_idx[-4:]]
    lows  = [(series.index[i], round(arr[i], 2)) for i in l_idx[-4:]]
    return highs, lows


def structure_type(highs, lows):
    if len(highs) < 2 or len(lows) < 2:
        return "数据不足", "未确认"
    hh = highs[-1][1] > highs[-2][1]
    hl = lows[-1][1]  > lows[-2][1]
    if hh and hl:         return "上升结构(HH+HL)", "确认"
    if not hh and not hl: return "下降结构(LH+LL)", "确认"
    if not hh and hl:     return "收敛结构(LH+HL)", "等待方向"
    return "扩散结构(HH+LL)", "高波动不稳定"


def volume_analysis(df, window=10):
    recent    = df.iloc[-window:]
    up_days   = recent[recent["Close"] >= recent["Open"]]
    down_days = recent[recent["Close"] <  recent["Open"]]
    up_vol    = up_days["Volume"].mean()   if len(up_days)   > 0 else 0
    down_vol  = down_days["Volume"].mean() if len(down_days) > 0 else 1
    ratio     = up_vol / down_vol if down_vol > 0 else 1.0
    if ratio > 1.2:    c = "支持（上涨放量）"
    elif ratio >= 1.0: c = "中性偏多"
    elif ratio >= 0.8: c = "中性偏弱"
    else:              c = "警惕（上涨缩量）"
    return {"up_vol": round(up_vol/1e6,2), "down_vol": round(down_vol/1e6,2),
            "ratio": round(ratio,2), "conclusion": c}


def momentum_analysis(df):
    rsi_s = calc_rsi(df["Close"])
    macd_line, sig_line, hist = calc_macd(df["Close"])
    rsi_val  = round(float(rsi_s.iloc[-1]),  1)
    macd_val = round(float(macd_line.iloc[-1]), 3)
    hist_val = round(float(hist.iloc[-1]),    3)
    hist_prv = round(float(hist.iloc[-2]),    3) if len(hist)>1 else hist_val

    if rsi_val>70:    rl=f"{rsi_val}（超买区）"
    elif rsi_val>=55: rl=f"{rsi_val}（偏强）"
    elif rsi_val>=45: rl=f"{rsi_val}（中性）"
    elif rsi_val>=30: rl=f"{rsi_val}（偏弱）"
    else:             rl=f"{rsi_val}（超卖区）"

    ml  = f"{macd_val}（{'零轴上方多头' if macd_val>0 else '零轴下方空头'}）"
    hl  = f"{hist_val}（{'扩大' if abs(hist_val)>abs(hist_prv) else '收缩'}）"
    con = "支持" if macd_val>0 and rsi_val>=50 else ("警惕" if macd_val<0 and rsi_val<45 else "中性")

    return {"rsi": rl, "rsi_val": rsi_val, "macd": ml, "macd_val": macd_val,
            "histogram": hl, "hist_val": hist_val,
            "macd_series": macd_line, "signal_series": sig_line,
            "hist_series": hist, "rsi_series": rsi_s, "conclusion": con}


def volatility_analysis(df):
    atr_s = calc_atr(df["High"], df["Low"], df["Close"])
    upper, mid, lower, bw = calc_bbands(df["Close"])
    price   = float(df["Close"].iloc[-1])
    atr_val = round(float(atr_s.iloc[-1]), 2)
    bw_val  = round(float(bw.iloc[-1]),    2)
    bw_prv  = round(float(bw.iloc[-5]),    2) if len(bw)>5 else bw_val

    if bw_val > bw_prv*1.1:   vs, pi = "扩张", "降低仓位"
    elif bw_val < bw_prv*0.9: vs, pi = "收缩（可能酝酿突破）", "正常"
    else:                      vs, pi = "震荡", "正常"

    return {"atr": atr_val, "atr_pct": round(atr_val/price*100,2),
            "atr_series": atr_s, "vol_state": vs, "pos_impact": pi,
            "bb_upper": round(float(upper.iloc[-1]),2),
            "bb_lower": round(float(lower.iloc[-1]),2),
            "bw_val": bw_val,
            "bb_upper_series": upper, "bb_lower_series": lower, "bb_mid_series": mid}


def relative_strength(ticker, df, window=20):
    refs = REFERENCE_MAP.get(ticker, {"index": "SPY", "sector": "SPY"})
    ticker_ret = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-window]) - 1) * 100
    results = {}
    for role, ref_t in refs.items():
        try:
            ref_df = fetch_data(ref_t, period="3mo")
            if ref_df.empty:
                results[role] = "数据不足"; continue
            ref_ret = (float(ref_df["Close"].iloc[-1]) / float(ref_df["Close"].iloc[-window]) - 1) * 100
            diff = ticker_ret - ref_ret
            results[role] = (f"强（超额 +{round(diff,1)}%）" if diff>2 else
                             f"中性（{round(diff,1)}%）" if diff>-2 else
                             f"弱（落后 {round(diff,1)}%）")
            time.sleep(random.uniform(0.5, 1.5))
        except Exception:
            results[role] = "数据不足"
    rs_ok = any("强" in str(v) for v in results.values())
    return {"vs_index": results.get("index","数据不足"),
            "vs_sector": results.get("sector","数据不足"),
            "index_name": refs["index"], "sector_name": refs["sector"],
            "conclusion": "支持交易" if rs_ok else "不支持交易"}


def market_background(ticker):
    refs = REFERENCE_MAP.get(ticker, {"index":"SPY","sector":"SPY"})
    try:
        spy_df = fetch_data("SPY", period="3mo")
        time.sleep(random.uniform(0.5,1))
        if not spy_df.empty:
            spy_ma20  = spy_df["Close"].rolling(20).mean().iloc[-1]
            spy_price = float(spy_df["Close"].iloc[-1])
            bg = "支持" if spy_price > float(spy_ma20) else "不支持"
        else:
            bg = "数据不足"
    except Exception:
        bg = "数据不足"
    return {"market": bg, "sector": refs["sector"], "conclusion": bg}


def key_levels(df):
    return {
        "resistance":   round(float(df["High"].iloc[-60:].max()),  2),
        "support":      round(float(df["Low"].iloc[-20:].min()),   2),
        "confirm":      round(float(df["High"].iloc[-120:-60].max()),2),
        "invalidation": round(float(df["Low"].iloc[-60:].min()),   2),
    }


def trade_type(long_trend, mid_trend, struct_t, rsi_val, price, ma20):
    if "多头" in long_trend and "多头" in mid_trend and "上升" in struct_t:
        if price > ma20*1.05:
            return {"type":"突破追涨交易（注意追高风险）","suitable":"适合","wait":"是，等回踩确认"}
        if abs(price-ma20)/ma20 < 0.02:
            return {"type":"回调低吸交易","suitable":"适合","wait":"否，位置合适"}
        return {"type":"趋势延续交易","suitable":"适合","wait":"否"}
    if "空头" in long_trend or "空头" in mid_trend:
        return {"type":"观望","suitable":"不适合","wait":"是，等趋势确认"}
    if "收敛" in struct_t or "修复" in mid_trend:
        return {"type":"等待突破方向确认","suitable":"暂不适合","wait":"是"}
    return {"type":"观望","suitable":"暂不适合","wait":"是，等信号明确"}


def event_risk(ticker):
    try:
        cal = yf.Ticker(ticker).calendar
        if cal is not None and not cal.empty:
            ed = cal.iloc[0,0] if isinstance(cal, pd.DataFrame) else None
            if ed:
                delta = (pd.Timestamp(ed) - pd.Timestamp.now()).days
                if 0<=delta<=7:  return {"event":f"财报将在{delta}天后发布","risk":"高","action":"事件后再交易"}
                if 0<=delta<=14: return {"event":f"财报将在{delta}天后发布","risk":"中","action":"降低仓位"}
    except Exception:
        pass
    return {"event":"未检测到近期重大事件","risk":"低","action":"正常执行"}


def analyze_ticker(ticker):
    print(f"\n{'='*50}\n  分析中：{ticker}\n{'='*50}")
    df = fetch_data(ticker)
    if df.empty:
        return {"ticker": ticker, "error": "数据获取失败"}

    price = round(float(df["Close"].iloc[-1]), 2)
    print(f"  当前价格：{price}")

    df["MA20"]  = df["Close"].rolling(20).mean()
    df["MA60"]  = df["Close"].rolling(60).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    ma20  = round(float(df["MA20"].iloc[-1]),  2)
    ma60  = round(float(df["MA60"].iloc[-1]),  2)
    ma200 = round(float(df["MA200"].iloc[-1]), 2)
    s20   = calc_slope(df["MA20"].dropna())
    s60   = calc_slope(df["MA60"].dropna())
    s200  = calc_slope(df["MA200"].dropna())

    trading_cycle = {"cycle":"波段交易（日线为主）","conclusion":"基于日线数据，适合波段交易"}
    print("  [0] ✓")

    mkt = market_background(ticker)
    print("  [1] ✓")

    ma200_dev = round((price-ma200)/ma200*100, 2)
    long_trend = ("多头" if price>ma200 and s200>0.05 else
                  "中性偏多" if price>ma200 else
                  "方向选择区" if abs(price-ma200)/ma200<0.03 else "空头")
    print(f"  [2] {long_trend} ✓")

    mid_trend = ("强多头排列" if price>ma20 and ma20>ma60 and ma60>ma200 else
                 "多头修复"   if price>ma20 and ma20>ma60 else
                 "短线反弹"   if price>ma20 else
                 "中期调整"   if ma20<ma60  else "空头排列")
    print(f"  [3] {mid_trend} ✓")

    atr_raw   = calc_atr(df["High"], df["Low"], df["Close"])
    atr_now   = float(atr_raw.iloc[-1])
    swing_ord = max(5, min(int(atr_now/price*1000), 15))
    highs, lows = find_swing_points(df["Close"], order=swing_ord)
    struct_t, struct_c = structure_type(highs, lows)
    print(f"  [4] {struct_t} ✓")

    levels = key_levels(df)
    print("  [5] ✓")

    rs = relative_strength(ticker, df)
    print("  [6] ✓")

    vol = volume_analysis(df)
    print("  [7] ✓")

    mom = momentum_analysis(df)
    print("  [8] ✓")

    vol_state = volatility_analysis(df)
    print("  [9] ✓")

    trade = trade_type(long_trend, mid_trend, struct_t, mom["rsi_val"], price, ma20)
    print(f"  [10] {trade['type']} ✓")

    risk = {
        "entry": price,
        "short_stop":     round(float(df["Low"].iloc[-5:].min()),  2),  # 近5日最低
        "mid_stop":       round(float(df["Low"].iloc[-20:].min()), 2),  # 近20日最低
        "structure_stop": round(float(df["Low"].iloc[-60:].min()), 2),  # 近60日最低
        "target1":        levels["resistance"],
        "target2":        round(levels["resistance"] + (levels["resistance"]-levels["support"])*0.5, 2),
        "note":           "⚠️ 止损和目标位为规则近似值，需人工确认后使用",
        "conclusion":     "需人工确认",
    }
    print("  [11] ✓")

    evt = event_risk(ticker)
    print(f"  [12] {evt['risk']} ✓")

    return {
        "ticker": ticker, "price": price, "date": df.index[-1].strftime("%Y-%m-%d"), "df": df,
        "0_cycle": trading_cycle, "1_market": mkt,
        "2_long_trend": {"ma200":ma200,"deviation":ma200_dev,"slope":slope_label(s200),"conclusion":long_trend},
        "3_mid_trend":  {"ma20":ma20,"ma60":ma60,"slope20":slope_label(s20),"slope60":slope_label(s60),"conclusion":mid_trend},
        "4_structure":  {"highs":[(str(d.date()),v) for d,v in highs],
                         "lows": [(str(d.date()),v) for d,v in lows],
                         "type":struct_t,"conclusion":struct_c},
        "5_levels": levels, "6_rs": rs, "7_volume": vol,
        "8_momentum": mom, "9_volatility": vol_state,
        "10_trade": trade, "11_risk": risk, "12_event": evt,
    }


def analyze_all(tickers=None):
    if tickers is None:
        tickers = STOCK_POOL
    results = []
    for ticker in tickers:
        results.append(analyze_ticker(ticker))
        time.sleep(random.uniform(2, 4))
    return results


if __name__ == "__main__":
    r = analyze_all(["TSLA"])[0]
    print(f"\n✅ {r['ticker']} @ {r['price']}")
    print(f"   长期：{r['2_long_trend']['conclusion']}")
    print(f"   中期：{r['3_mid_trend']['conclusion']}")
