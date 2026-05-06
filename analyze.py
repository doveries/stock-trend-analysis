"""
系统化技术分析 - 12项框架
股票池：BRK-B, TSLA, GLD, CCJ, FCX
"""

import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
from scipy.signal import argrelextrema
import warnings
import time
import random

warnings.filterwarnings("ignore")

# ── 参考标的映射 ──────────────────────────────────────────────
REFERENCE_MAP = {
    "TSLA":  {"index": "QQQ",  "sector": "QQQ"},
    "BRK-B": {"index": "SPY",  "sector": "SPY"},
    "GLD":   {"index": "SPY",  "sector": "UUP"},
    "CCJ":   {"index": "SPY",  "sector": "URA"},
    "FCX":   {"index": "SPY",  "sector": "CPER"},
}

STOCK_POOL = ["BRK-B", "TSLA", "GLD", "CCJ", "FCX"]


def fetch_data(ticker: str, period: str = "2y") -> pd.DataFrame:
    """拉取历史数据，失败重试"""
    for attempt in range(3):
        try:
            df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
            if df is not None and len(df) >= 60:
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                return df
        except Exception as e:
            print(f"  [{ticker}] 第{attempt+1}次拉取失败: {e}")
            time.sleep(random.uniform(1, 3))
    return pd.DataFrame()


def calc_slope(series: pd.Series, window: int = 5) -> float:
    """计算均线斜率（归一化）"""
    if len(series) < window:
        return 0.0
    y = series.iloc[-window:].values
    x = np.arange(window)
    slope = np.polyfit(x, y, 1)[0]
    return slope / series.iloc[-1] * 100  # 百分比斜率


def slope_label(slope: float) -> str:
    if slope > 0.05:
        return "向上"
    elif slope < -0.05:
        return "向下"
    else:
        return "走平"


def find_swing_points(series: pd.Series, order: int = 10):
    """识别摆动高低点"""
    arr = series.values
    highs_idx = argrelextrema(arr, np.greater, order=order)[0]
    lows_idx = argrelextrema(arr, np.less, order=order)[0]
    highs = [(series.index[i], round(arr[i], 2)) for i in highs_idx[-4:]]
    lows = [(series.index[i], round(arr[i], 2)) for i in lows_idx[-4:]]
    return highs, lows


def structure_type(highs, lows) -> tuple:
    """判断价格结构"""
    if len(highs) < 2 or len(lows) < 2:
        return "数据不足", "未确认"
    hh = highs[-1][1] > highs[-2][1]
    hl = lows[-1][1] > lows[-2][1]
    if hh and hl:
        return "上升结构(HH+HL)", "确认"
    elif not hh and not hl:
        return "下降结构(LH+LL)", "确认"
    elif not hh and hl:
        return "收敛结构(LH+HL)", "等待方向"
    else:
        return "扩散结构(HH+LL)", "高波动不稳定"


def volume_analysis(df: pd.DataFrame, window: int = 10) -> dict:
    """量价分析"""
    recent = df.iloc[-window:]
    up_days = recent[recent["Close"] >= recent["Open"]]
    down_days = recent[recent["Close"] < recent["Open"]]
    up_vol = up_days["Volume"].mean() if len(up_days) > 0 else 0
    down_vol = down_days["Volume"].mean() if len(down_days) > 0 else 1
    ratio = up_vol / down_vol if down_vol > 0 else 1.0

    if ratio > 1.2:
        conclusion = "支持（上涨放量）"
    elif ratio >= 1.0:
        conclusion = "中性偏多"
    elif ratio >= 0.8:
        conclusion = "中性偏弱"
    else:
        conclusion = "警惕（上涨缩量）"

    return {
        "up_vol": round(up_vol / 1e6, 2),
        "down_vol": round(down_vol / 1e6, 2),
        "ratio": round(ratio, 2),
        "conclusion": conclusion,
    }


def momentum_analysis(df: pd.DataFrame) -> dict:
    """动量分析：RSI + MACD"""
    rsi = ta.rsi(df["Close"], length=14)
    macd_df = ta.macd(df["Close"], fast=12, slow=26, signal=9)

    rsi_val = round(rsi.iloc[-1], 1) if rsi is not None and not rsi.empty else None
    if rsi_val is None:
        rsi_label = "数据不足"
    elif rsi_val > 70:
        rsi_label = f"{rsi_val}（超买区）"
    elif rsi_val >= 55:
        rsi_label = f"{rsi_val}（偏强）"
    elif rsi_val >= 45:
        rsi_label = f"{rsi_val}（中性）"
    elif rsi_val >= 30:
        rsi_label = f"{rsi_val}（偏弱）"
    else:
        rsi_label = f"{rsi_val}（超卖区）"

    macd_col = [c for c in macd_df.columns if c.startswith("MACD_") and "s" not in c.lower() and "h" not in c.lower()]
    sig_col = [c for c in macd_df.columns if "MACDs" in c]
    hist_col = [c for c in macd_df.columns if "MACDh" in c]

    macd_val = round(macd_df[macd_col[0]].iloc[-1], 3) if macd_col else None
    hist_val = round(macd_df[hist_col[0]].iloc[-1], 3) if hist_col else None
    hist_prev = round(macd_df[hist_col[0]].iloc[-2], 3) if hist_col and len(macd_df) > 1 else None

    if macd_val is None:
        macd_label = "数据不足"
        hist_label = "数据不足"
        conclusion = "数据不足"
    else:
        macd_label = f"{macd_val}（{'零轴上方多头' if macd_val > 0 else '零轴下方空头'}）"
        if hist_val is not None and hist_prev is not None:
            hist_label = f"{hist_val}（{'扩大' if abs(hist_val) > abs(hist_prev) else '收缩'}）"
        else:
            hist_label = str(hist_val)

        if macd_val > 0 and rsi_val and rsi_val >= 50:
            conclusion = "支持"
        elif macd_val < 0 and rsi_val and rsi_val < 45:
            conclusion = "警惕"
        else:
            conclusion = "中性"

    return {
        "rsi": rsi_label,
        "rsi_val": rsi_val,
        "macd": macd_label,
        "macd_val": macd_val,
        "histogram": hist_label,
        "hist_val": hist_val,
        "conclusion": conclusion,
    }


def volatility_analysis(df: pd.DataFrame) -> dict:
    """波动率分析：ATR + 布林带"""
    atr = ta.atr(df["High"], df["Low"], df["Close"], length=14)
    bb = ta.bbands(df["Close"], length=20, std=2)

    price = df["Close"].iloc[-1]
    atr_val = round(atr.iloc[-1], 2) if atr is not None else None
    atr_pct = round(atr_val / price * 100, 2) if atr_val else None

    bw_col = [c for c in bb.columns if "BBB" in c] if bb is not None else []
    bw_val = round(bb[bw_col[0]].iloc[-1], 2) if bw_col else None
    bw_prev = round(bb[bw_col[0]].iloc[-5], 2) if bw_col and len(bb) > 5 else None

    if bw_val and bw_prev:
        if bw_val > bw_prev * 1.1:
            vol_state = "扩张"
            pos_impact = "降低仓位"
        elif bw_val < bw_prev * 0.9:
            vol_state = "收缩（可能酝酿突破）"
            pos_impact = "正常"
        else:
            vol_state = "震荡"
            pos_impact = "正常"
    else:
        vol_state = "数据不足"
        pos_impact = "正常"

    # 获取布林带上下轨
    upper_col = [c for c in bb.columns if "BBU" in c] if bb is not None else []
    lower_col = [c for c in bb.columns if "BBL" in c] if bb is not None else []
    bb_upper = round(bb[upper_col[0]].iloc[-1], 2) if upper_col else None
    bb_lower = round(bb[lower_col[0]].iloc[-1], 2) if lower_col else None

    return {
        "atr": atr_val,
        "atr_pct": atr_pct,
        "vol_state": vol_state,
        "pos_impact": pos_impact,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bw_val": bw_val,
    }


def relative_strength(ticker: str, df: pd.DataFrame, window: int = 20) -> dict:
    """相对强弱分析"""
    refs = REFERENCE_MAP.get(ticker, {"index": "SPY", "sector": "SPY"})
    results = {}
    ticker_ret = (df["Close"].iloc[-1] / df["Close"].iloc[-window] - 1) * 100

    for role, ref_ticker in refs.items():
        try:
            ref_df = fetch_data(ref_ticker, period="3mo")
            if ref_df.empty:
                results[role] = "数据不足"
                continue
            ref_ret = (ref_df["Close"].iloc[-1] / ref_df["Close"].iloc[-window] - 1) * 100
            diff = ticker_ret - ref_ret
            if diff > 2:
                label = f"强（超额 +{round(diff,1)}%）"
            elif diff > -2:
                label = f"中性（{round(diff,1)}%）"
            else:
                label = f"弱（落后 {round(diff,1)}%）"
            results[role] = label
            time.sleep(random.uniform(0.5, 1.5))
        except Exception:
            results[role] = "数据不足"

    rs_conclusion = "支持交易" if "强" in str(results.get("index", "")) or "强" in str(results.get("sector", "")) else "不支持交易"
    return {
        "vs_index": results.get("index", "数据不足"),
        "vs_sector": results.get("sector", "数据不足"),
        "index_name": refs["index"],
        "sector_name": refs["sector"],
        "conclusion": rs_conclusion,
    }


def market_background(ticker: str, df: pd.DataFrame) -> dict:
    """市场/行业背景"""
    refs = REFERENCE_MAP.get(ticker, {"index": "SPY", "sector": "SPY"})
    spy_df = fetch_data("SPY", period="3mo")
    time.sleep(random.uniform(0.5, 1))

    if not spy_df.empty:
        spy_ma20 = spy_df["Close"].rolling(20).mean().iloc[-1]
        spy_price = spy_df["Close"].iloc[-1]
        market_bg = "支持" if spy_price > spy_ma20 else "不支持"
    else:
        market_bg = "数据不足"

    return {
        "market": market_bg,
        "sector": refs["sector"],
        "conclusion": market_bg,
    }


def key_levels(df: pd.DataFrame, highs, lows, vol_data: dict) -> dict:
    """关键价格位"""
    price = df["Close"].iloc[-1]
    ma20 = df["Close"].rolling(20).mean().iloc[-1]
    ma60 = df["Close"].rolling(60).mean().iloc[-1]
    ma200 = df["Close"].rolling(200).mean().iloc[-1]

    # 阻力：近期高点
    recent_high = df["High"].iloc[-60:].max()
    resistance = round(max(recent_high, ma200 if ma200 > price else price * 1.05), 2)

    # 支撑：近期低点
    recent_low = df["Low"].iloc[-20:].min()
    support = round(min(recent_low, ma20 if ma20 < price else price * 0.95), 2)

    # 确认位：前高
    confirm = round(df["High"].iloc[-120:-60].max(), 2)

    # 失效位：近60日低点
    invalidation = round(df["Low"].iloc[-60:].min(), 2)

    return {
        "resistance": resistance,
        "support": support,
        "confirm": confirm,
        "invalidation": invalidation,
    }


def trade_type(long_trend: str, mid_trend: str, structure: str, rsi_val, price: float, ma20: float, ma60: float) -> dict:
    """判断交易类型"""
    if "多头" in long_trend and "多头" in mid_trend and "上升" in structure:
        if price > ma20 * 1.05:
            t_type = "突破追涨交易（注意追高风险）"
            wait = "是，等回踩确认"
        elif abs(price - ma20) / ma20 < 0.02:
            t_type = "回调低吸交易"
            wait = "否，位置合适"
        else:
            t_type = "趋势延续交易"
            wait = "否"
        suitable = "适合"
    elif "空头" in long_trend or "空头" in mid_trend:
        t_type = "观望"
        suitable = "不适合"
        wait = "是，等趋势确认"
    elif "收敛" in structure or "修复" in mid_trend:
        t_type = "等待突破方向确认"
        suitable = "暂不适合"
        wait = "是"
    else:
        t_type = "观望"
        suitable = "暂不适合"
        wait = "是，等信号明确"

    return {"type": t_type, "suitable": suitable, "wait": wait}


def event_risk(ticker: str) -> dict:
    """事件风险检测：检查未来7天财报"""
    try:
        stock = yf.Ticker(ticker)
        cal = stock.calendar
        if cal is not None and not cal.empty:
            earnings_date = cal.iloc[0, 0] if isinstance(cal, pd.DataFrame) else None
            if earnings_date:
                import datetime
                today = pd.Timestamp.now()
                delta = (pd.Timestamp(earnings_date) - today).days
                if 0 <= delta <= 7:
                    return {"event": f"财报将在 {delta} 天后发布", "risk": "高", "action": "事件后再交易"}
                elif 0 <= delta <= 14:
                    return {"event": f"财报将在 {delta} 天后发布", "risk": "中", "action": "降低仓位"}
    except Exception:
        pass
    return {"event": "未检测到近期重大事件", "risk": "低", "action": "正常执行"}


def analyze_ticker(ticker: str) -> dict:
    """主分析函数：对单个标的运行12项框架"""
    print(f"\n{'='*50}")
    print(f"  分析中：{ticker}")
    print(f"{'='*50}")

    df = fetch_data(ticker)
    if df.empty:
        return {"ticker": ticker, "error": "数据获取失败"}

    price = round(df["Close"].iloc[-1], 2)
    print(f"  当前价格：{price}")

    # ── 均线计算 ────────────────────────────────────────────
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    ma20 = round(df["MA20"].iloc[-1], 2)
    ma60 = round(df["MA60"].iloc[-1], 2)
    ma200 = round(df["MA200"].iloc[-1], 2)

    slope20 = calc_slope(df["MA20"].dropna())
    slope60 = calc_slope(df["MA60"].dropna())
    slope200 = calc_slope(df["MA200"].dropna())

    # ── 0. 交易周期 ─────────────────────────────────────────
    trading_cycle = {
        "cycle": "波段交易（日线为主）",
        "conclusion": "分析基于日线数据，适合波段交易周期"
    }
    print(f"  [0] 交易周期 ✓")

    # ── 1. 市场/行业背景 ────────────────────────────────────
    print(f"  [1] 市场背景...")
    mkt = market_background(ticker, df)
    print(f"  [1] ✓")

    # ── 2. 长期趋势 ─────────────────────────────────────────
    ma200_dev = round((price - ma200) / ma200 * 100, 2)
    if price > ma200 and slope200 > 0.05:
        long_trend = "多头"
    elif price > ma200:
        long_trend = "中性偏多"
    elif abs(price - ma200) / ma200 < 0.03:
        long_trend = "方向选择区"
    else:
        long_trend = "空头"
    print(f"  [2] 长期趋势：{long_trend} ✓")

    # ── 3. 中期趋势 ─────────────────────────────────────────
    if price > ma20 and ma20 > ma60 and ma60 > ma200:
        mid_trend = "强多头排列"
    elif price > ma20 and ma20 > ma60:
        mid_trend = "多头修复"
    elif price > ma20 and ma60 < 0:
        mid_trend = "短线反弹"
    elif ma20 < ma60:
        mid_trend = "中期调整"
    else:
        mid_trend = "空头排列"
    print(f"  [3] 中期趋势：{mid_trend} ✓")

    # ── 4. 价格结构 ─────────────────────────────────────────
    atr_val_raw = ta.atr(df["High"], df["Low"], df["Close"], length=14)
    atr_now = atr_val_raw.iloc[-1] if atr_val_raw is not None else price * 0.02
    swing_order = max(5, int(atr_now / price * 1000))
    swing_order = min(swing_order, 15)
    highs, lows = find_swing_points(df["Close"], order=swing_order)
    struct_type, struct_conclusion = structure_type(highs, lows)
    print(f"  [4] 价格结构：{struct_type} ✓")

    # ── 5. 关键位置 ─────────────────────────────────────────
    levels = key_levels(df, highs, lows, {})
    print(f"  [5] 关键位置 ✓")

    # ── 6. 相对强弱 ─────────────────────────────────────────
    print(f"  [6] 相对强弱...")
    rs = relative_strength(ticker, df)
    print(f"  [6] ✓")

    # ── 7. 量价确认 ─────────────────────────────────────────
    vol = volume_analysis(df)
    print(f"  [7] 量价确认 ✓")

    # ── 8. 动量状态 ─────────────────────────────────────────
    mom = momentum_analysis(df)
    print(f"  [8] 动量状态 ✓")

    # ── 9. 波动率状态 ────────────────────────────────────────
    vol_state = volatility_analysis(df)
    print(f"  [9] 波动率 ✓")

    # ── 10. 交易类型 ─────────────────────────────────────────
    trade = trade_type(long_trend, mid_trend, struct_type, mom["rsi_val"], price, ma20, ma60)
    print(f"  [10] 交易类型：{trade['type']} ✓")

    # ── 11. 风险与赔率（方案B：只列参考位） ──────────────────
    risk = {
        "entry": price,
        "short_stop": levels["support"],
        "mid_stop": round(df["Low"].iloc[-20:].min(), 2),
        "structure_stop": levels["invalidation"],
        "target1": levels["resistance"],
        "target2": round(levels["resistance"] + (levels["resistance"] - levels["support"]) * 0.5, 2),
        "note": "⚠️ 止损和目标位为规则近似值，需人工确认后使用",
        "conclusion": "需人工确认"
    }
    print(f"  [11] 风险赔率 ✓")

    # ── 12. 事件风险 ─────────────────────────────────────────
    evt = event_risk(ticker)
    print(f"  [12] 事件风险：{evt['risk']} ✓")

    return {
        "ticker": ticker,
        "price": price,
        "date": df.index[-1].strftime("%Y-%m-%d"),
        "0_cycle": trading_cycle,
        "1_market": mkt,
        "2_long_trend": {
            "ma200": ma200,
            "deviation": ma200_dev,
            "slope": slope_label(slope200),
            "conclusion": long_trend,
        },
        "3_mid_trend": {
            "ma20": ma20,
            "ma60": ma60,
            "slope20": slope_label(slope20),
            "slope60": slope_label(slope60),
            "conclusion": mid_trend,
        },
        "4_structure": {
            "highs": [(str(d.date()), v) for d, v in highs],
            "lows": [(str(d.date()), v) for d, v in lows],
            "type": struct_type,
            "conclusion": struct_conclusion,
        },
        "5_levels": levels,
        "6_rs": rs,
        "7_volume": vol,
        "8_momentum": mom,
        "9_volatility": vol_state,
        "10_trade": trade,
        "11_risk": risk,
        "12_event": evt,
        "df": df,  # 供图表使用，不进邮件
    }


def analyze_all(tickers: list = None) -> list:
    """批量分析"""
    if tickers is None:
        tickers = STOCK_POOL
    results = []
    for ticker in tickers:
        result = analyze_ticker(ticker)
        results.append(result)
        time.sleep(random.uniform(2, 4))
    return results


if __name__ == "__main__":
    results = analyze_all(["TSLA"])
    r = results[0]
    print(f"\n✅ 分析完成：{r['ticker']} @ {r['price']}")
    print(f"   长期趋势：{r['2_long_trend']['conclusion']}")
    print(f"   中期趋势：{r['3_mid_trend']['conclusion']}")
    print(f"   价格结构：{r['4_structure']['type']}")
    print(f"   动量结论：{r['8_momentum']['conclusion']}")
