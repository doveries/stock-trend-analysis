"""
系统化技术分析 - 12项框架 v2.1
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

# ── 参考标的映射（按资产类型区分基准）────────────────────────
REFERENCE_MAP = {
    "TSLA":  {"index": "QQQ",  "sector": "XLY"},   # 纳指 + 消费板块
    "BRK-B": {"index": "SPY",  "sector": "XLF"},   # 标普 + 金融板块
    "GLD":   {"index": "UUP",  "sector": "SLV"},   # 美元 + 白银
    "CCJ":   {"index": "SPY",  "sector": "URA"},   # 标普 + 铀矿ETF
    "FCX":   {"index": "SPY",  "sector": "CPER"},  # 标普 + 铜ETF
    "SPY":   {"index": "SPY",  "sector": "SPY",  "is_benchmark": True},
    "QQQ":   {"index": "SPY",  "sector": "QQQ",  "is_benchmark": True},
}

STOCK_POOL = ["SPY", "QQQ", "BRK-B", "TSLA", "GLD", "CCJ", "FCX"]

ALL_REF_TICKERS = list(set(
    v for refs in REFERENCE_MAP.values()
    for k, v in refs.items() if k != "is_benchmark"
) | {"SPY"})


# ── 指标计算 ─────────────────────────────────────────────────

def calc_rsi(close, period=14):
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast    = close.ewm(span=fast,   adjust=False).mean()
    ema_slow    = close.ewm(span=slow,   adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def calc_atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(com=period-1, min_periods=period).mean()


def calc_bbands(close, period=20, std=2.0):
    mid   = close.rolling(period).mean()
    sigma = close.rolling(period).std()
    upper = mid + std * sigma
    lower = mid - std * sigma
    bw    = (upper - lower) / mid * 100
    return upper, mid, lower, bw


# ── 数据获取 ─────────────────────────────────────────────────

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


def fetch_all_ref_data():
    cache = {}
    print(f"  预拉取参考数据：{ALL_REF_TICKERS}")
    for ticker in ALL_REF_TICKERS:
        df = fetch_data(ticker, period="3mo")
        if not df.empty:
            cache[ticker] = df
        time.sleep(random.uniform(0.5, 1.2))
    return cache


# ── 工具函数 ─────────────────────────────────────────────────

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
    arr   = series.values
    h_idx = argrelextrema(arr, np.greater, order=order)[0]
    l_idx = argrelextrema(arr, np.less,    order=order)[0]
    highs = [(series.index[i], round(arr[i], 2)) for i in h_idx[-4:]]
    lows  = [(series.index[i], round(arr[i], 2)) for i in l_idx[-4:]]
    return highs, lows


def analyze_breakout(df, highs, lows, atr_val):
    """
    创前高突破分析
    基于ChatGPT框架 + 我们的均线兜底规则
    返回结构状态和突破质量
    """
    close      = df["Close"]
    volume     = df["Volume"]
    price      = float(close.iloc[-1])
    close_1d   = float(close.iloc[-1])   # 最新收盘价
    close_2d   = float(close.iloc[-2]) if len(close) > 1 else price

    # 所有已识别摆动高点的最高值
    max_swing_high = max([v for _, v in highs]) if highs else 0

    # 近252日最高价（历史高位判断）
    high_252 = float(df["High"].iloc[-252:].max())

    # ── 是否创前高 ────────────────────────────────────────────
    broke_swing_high  = close_1d > max_swing_high           # 突破摆动高点
    near_52w_high     = price >= high_252 * 0.98            # 接近52周高位
    is_all_time_area  = price >= high_252 * 0.99            # 历史高位区域

    if not broke_swing_high:
        return None  # 没有创前高，用原始结构判断

    # ── 突破质量评分（5项取2） ────────────────────────────────
    score = 0
    details = []

    # 1) 收盘站上前高
    if close_1d > max_swing_high:
        score += 1
        details.append("收盘突破✓")

    # 2) 连续2日收盘站上
    two_day_confirm = close_1d > max_swing_high and close_2d > max_swing_high
    if two_day_confirm:
        score += 1
        details.append("连续2日确认✓")

    # 3) 突破幅度 > 0.5×ATR
    breakout_amp = close_1d - max_swing_high
    if breakout_amp > 0.5 * atr_val:
        score += 1
        details.append(f"突破幅度{round(breakout_amp,2)}>0.5ATR✓")

    # 4) 成交量 > 20日均量×1.2
    vol_ma20   = float(volume.iloc[-20:].mean())
    vol_today  = float(volume.iloc[-1])
    if vol_today > vol_ma20 * 1.2:
        score += 1
        details.append("放量突破✓")

    # 5) RSI未极端过热（<80）
    rsi_series = calc_rsi(close)
    rsi_now    = float(rsi_series.iloc[-1])
    if rsi_now < 80:
        score += 1
        details.append(f"RSI={rsi_now:.0f}<80✓")

    # 检测假突破：近3日是否跌回前高下方
    recent_close_min = float(close.iloc[-3:].min())
    fake_breakout = (recent_close_min < max_swing_high) and (close_1d > max_swing_high)

    # ── 输出结构状态 ──────────────────────────────────────────
    if fake_breakout:
        struct_type = "假突破风险"
        struct_concl = "近3日曾跌回前高下方，突破存疑"
    elif score >= 3 and two_day_confirm:
        struct_type = "突破确认" if not is_all_time_area else "历史新高·突破确认"
        struct_concl = f"质量评分{score}/5，{', '.join(details)}"
    elif score >= 2:
        struct_type = "突破待确认" if not is_all_time_area else "历史新高·待确认"
        struct_concl = f"质量评分{score}/5，{', '.join(details)}，建议等回踩确认"
    else:
        struct_type = "突破存疑" if not is_all_time_area else "历史新高·突破存疑"
        struct_concl = f"质量评分{score}/5，量能或幅度不足，谨慎追高"

    return {
        "breakout":          True,
        "max_swing_high":    max_swing_high,
        "is_all_time_area":  is_all_time_area,
        "near_52w_high":     near_52w_high,
        "score":             score,
        "details":           details,
        "fake_breakout":     fake_breakout,
        "struct_type":       struct_type,
        "struct_conclusion": struct_concl,
        "breakout_amp":      round(breakout_amp, 2),
        "atr_val":           round(atr_val, 2),
    }


def structure_type_original(highs, lows):
    """原始摆动点结构判断"""
    if len(highs) < 2 or len(lows) < 2:
        return "数据不足", "未确认"
    hh = highs[-1][1] > highs[-2][1]
    hl = lows[-1][1]  > lows[-2][1]
    if hh and hl:         return "上升结构(HH+HL)", "确认"
    if not hh and not hl: return "下降结构(LH+LL)", "确认"
    if not hh and hl:     return "收敛结构(LH+HL)", "等待方向"
    return "扩散结构(HH+LL)", "高波动不稳定"


# ── 各项分析 ─────────────────────────────────────────────────

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
    return {
        "up_vol":   round(up_vol / 1e6, 2),
        "down_vol": round(down_vol / 1e6, 2),
        "ratio":    round(ratio, 2),
        "conclusion": c,
        "vol_ma20": round(float(df["Volume"].iloc[-20:].mean()) / 1e6, 2),
    }


def momentum_analysis(df):
    rsi_s = calc_rsi(df["Close"])
    macd_line, sig_line, hist = calc_macd(df["Close"])
    rsi_val  = round(float(rsi_s.iloc[-1]),     1)
    macd_val = round(float(macd_line.iloc[-1]), 3)
    hist_val = round(float(hist.iloc[-1]),       3)
    hist_prv = round(float(hist.iloc[-2]),       3) if len(hist) > 1 else hist_val

    if rsi_val > 70:    rl = f"{rsi_val}（超买区）"
    elif rsi_val >= 55: rl = f"{rsi_val}（偏强）"
    elif rsi_val >= 45: rl = f"{rsi_val}（中性）"
    elif rsi_val >= 30: rl = f"{rsi_val}（偏弱）"
    else:               rl = f"{rsi_val}（超卖区）"

    ml  = f"{macd_val}（{'零轴上方多头' if macd_val > 0 else '零轴下方空头'}）"
    hl  = f"{hist_val}（{'扩大' if abs(hist_val) > abs(hist_prv) else '收缩'}）"
    con = ("支持" if macd_val > 0 and rsi_val >= 50 else
           "警惕" if macd_val < 0 and rsi_val < 45  else "中性")

    return {
        "rsi": rl, "rsi_val": rsi_val, "macd": ml, "macd_val": macd_val,
        "histogram": hl, "hist_val": hist_val,
        "macd_series": macd_line, "signal_series": sig_line,
        "hist_series": hist, "rsi_series": rsi_s, "conclusion": con,
    }


def volatility_analysis(df):
    atr_s = calc_atr(df["High"], df["Low"], df["Close"])
    upper, mid, lower, bw = calc_bbands(df["Close"])
    price   = float(df["Close"].iloc[-1])
    atr_val = round(float(atr_s.iloc[-1]), 2)
    bw_val  = round(float(bw.iloc[-1]),    2)
    bw_prv  = round(float(bw.iloc[-5]),    2) if len(bw) > 5 else bw_val

    if bw_val > bw_prv * 1.1:   vs, pi = "扩张", "降低仓位"
    elif bw_val < bw_prv * 0.9: vs, pi = "收缩（可能酝酿突破）", "正常"
    else:                        vs, pi = "震荡", "正常"

    return {
        "atr": atr_val, "atr_pct": round(atr_val / price * 100, 2),
        "atr_series": atr_s, "vol_state": vs, "pos_impact": pi,
        "bb_upper": round(float(upper.iloc[-1]), 2),
        "bb_lower": round(float(lower.iloc[-1]), 2),
        "bw_val": bw_val,
        "bb_upper_series": upper, "bb_lower_series": lower, "bb_mid_series": mid,
    }


def relative_strength(ticker, df, ref_cache, window=20):
    """按资产类型选择合适的基准，SPY/QQQ特殊处理"""
    refs = REFERENCE_MAP.get(ticker, {"index": "SPY", "sector": "SPY"})
    is_benchmark = refs.get("is_benchmark", False)

    # SPY/QQQ作为基准资产，不做自比
    if is_benchmark:
        if ticker == "SPY":
            # SPY和QQQ比
            other = "QQQ"
            other_df = ref_cache.get(other)
            if other_df is not None and not other_df.empty:
                t_ret = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-window]) - 1) * 100
                o_ret = (float(other_df["Close"].iloc[-1]) / float(other_df["Close"].iloc[-window]) - 1) * 100
                diff  = t_ret - o_ret
                label = (f"强于QQQ +{round(diff,1)}%" if diff > 1 else
                         f"弱于QQQ {round(diff,1)}%"  if diff < -1 else
                         f"与QQQ持平 {round(diff,1)}%")
            else:
                label = "数据不足"
            return {
                "vs_index":    "基准资产（标普500指数）",
                "vs_sector":   label,
                "index_name":  "基准",
                "sector_name": "QQQ",
                "conclusion":  "基准资产·不适用相对强弱",
                "is_benchmark": True,
            }
        elif ticker == "QQQ":
            # QQQ和SPY比
            spy_df = ref_cache.get("SPY")
            if spy_df is not None and not spy_df.empty:
                t_ret = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-window]) - 1) * 100
                s_ret = (float(spy_df["Close"].iloc[-1]) / float(spy_df["Close"].iloc[-window]) - 1) * 100
                diff  = t_ret - s_ret
                label = (f"强于SPY +{round(diff,1)}%" if diff > 1 else
                         f"弱于SPY {round(diff,1)}%"  if diff < -1 else
                         f"与SPY持平 {round(diff,1)}%")
            else:
                label = "数据不足"
            return {
                "vs_index":    "基准资产（纳斯达克指数）",
                "vs_sector":   label,
                "index_name":  "基准",
                "sector_name": "SPY",
                "conclusion":  "基准资产·仅供参考",
                "is_benchmark": True,
            }

    # 普通标的：用各自对应的基准
    ticker_ret = (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-window]) - 1) * 100
    results = {}
    for role, ref_t in {"index": refs["index"], "sector": refs["sector"]}.items():
        ref_df = ref_cache.get(ref_t)
        if ref_df is None or ref_df.empty:
            results[role] = "数据不足"
            continue
        try:
            ref_ret = (float(ref_df["Close"].iloc[-1]) / float(ref_df["Close"].iloc[-window]) - 1) * 100
            diff = ticker_ret - ref_ret
            results[role] = (f"强（超额 +{round(diff,1)}%）" if diff > 2 else
                             f"中性（{round(diff,1)}%）"      if diff > -2 else
                             f"弱（落后 {round(diff,1)}%）")
        except Exception:
            results[role] = "数据不足"

    rs_ok = any("强" in str(v) for v in results.values())
    return {
        "vs_index":    results.get("index",  "数据不足"),
        "vs_sector":   results.get("sector", "数据不足"),
        "index_name":  refs["index"],
        "sector_name": refs["sector"],
        "conclusion":  "支持交易" if rs_ok else "不支持交易",
        "is_benchmark": False,
    }


def market_background(ticker, ref_cache):
    refs   = REFERENCE_MAP.get(ticker, {"index": "SPY", "sector": "SPY"})
    spy_df = ref_cache.get("SPY")
    if spy_df is not None and not spy_df.empty:
        spy_ma20  = spy_df["Close"].rolling(20).mean().iloc[-1]
        spy_price = float(spy_df["Close"].iloc[-1])
        bg = "支持" if spy_price > float(spy_ma20) else "不支持"
    else:
        bg = "数据不足"
    return {"market": bg, "sector": refs.get("sector", "SPY"), "conclusion": bg}


def key_levels(df):
    resistance   = round(float(df["High"].iloc[-60:].max()),    2)
    support      = round(float(df["Low"].iloc[-20:].min()),     2)
    confirm      = round(float(df["High"].iloc[-120:-60].max()),2)
    invalidation = round(float(df["Low"].iloc[-60:].min()),     2)
    if support == invalidation:
        support = round(float(df["Low"].iloc[-10:].min()), 2)
    return {
        "resistance":   resistance,
        "support":      support,
        "confirm":      confirm,
        "invalidation": invalidation,
    }


def calc_risk_reward(price, atr_val, levels, breakout_info=None):
    """
    计算风险赔率
    - 历史新高：用ATR法计算目标
    - 普通标的：用阻力位法
    - 加入硬门槛检查
    """
    short_stop     = round(price - atr_val * 1.0, 2)
    mid_stop       = levels["support"]
    structure_stop = levels["invalidation"]

    # 目标价：历史新高用ATR法，否则用阻力位
    if breakout_info and breakout_info.get("is_all_time_area"):
        target1 = round(price + 2 * atr_val, 2)
        target2 = round(price + 4 * atr_val, 2)
        target_method = "ATR倍数法（历史新高区域）"
    else:
        target1 = levels["resistance"]
        target2 = round(levels["resistance"] + (levels["resistance"] - mid_stop) * 0.5, 2)
        target_method = "阻力位法"

    # 目标一有效性检查：距离 < 0.5×ATR 则无效
    t1_dist = target1 - price
    t2_dist = target2 - price
    risk    = price - short_stop

    t1_invalid = t1_dist < 0.5 * atr_val
    t1_rr = round(t1_dist / risk, 2) if risk > 0 else 0
    t2_rr = round(t2_dist / risk, 2) if risk > 0 else 0

    # 硬门槛判断
    if t1_invalid:
        rr_conclusion = "目标一无效（距离不足0.5ATR）"
        rr_pass = False
    elif t1_rr < 1.0:
        rr_conclusion = "赔率不合格（目标一<1:1）"
        rr_pass = False
    elif t2_rr < 2.0:
        rr_conclusion = "赔率偏低（目标二<2:1），建议等待更好位置"
        rr_pass = False
    else:
        rr_conclusion = f"赔率合格（目标一{t1_rr}:1 / 目标二{t2_rr}:1）"
        rr_pass = True

    return {
        "entry":          price,
        "short_stop":     short_stop,
        "mid_stop":       mid_stop,
        "structure_stop": structure_stop,
        "target1":        target1,
        "target2":        target2,
        "target_method":  target_method,
        "t1_rr":          t1_rr,
        "t2_rr":          t2_rr,
        "t1_invalid":     t1_invalid,
        "rr_pass":        rr_pass,
        "conclusion":     rr_conclusion,
        "note":           "⚠️ 止损和目标位为规则近似值，需人工确认后使用",
    }


def trade_type(long_trend, mid_trend, struct_t, rsi_val, price, ma20, rr_pass):
    """交易类型判断，受盈亏比硬门槛约束"""
    # 赔率不通过，禁止输出买入/试多
    if not rr_pass:
        if "多头" in long_trend:
            return {
                "type":     "观望（赔率不足）",
                "suitable": "暂不适合",
                "wait":     "是，等待更好位置或回踩",
                "rr_block": True,
            }
        return {"type": "不交易", "suitable": "不适合", "wait": "是", "rr_block": True}

    if "多头" in long_trend and "多头" in mid_trend and "上升" in struct_t:
        if price > ma20 * 1.05:
            return {"type": "突破追涨", "suitable": "适合", "wait": "是，等回踩确认", "rr_block": False}
        if abs(price - ma20) / ma20 < 0.02:
            return {"type": "回调低吸", "suitable": "适合", "wait": "否，位置合适", "rr_block": False}
        return {"type": "趋势延续", "suitable": "适合", "wait": "否", "rr_block": False}

    if "突破" in struct_t:
        return {"type": "突破交易", "suitable": "适合", "wait": "是，等收盘确认", "rr_block": False}

    if "空头" in long_trend or "空头" in mid_trend:
        return {"type": "不交易", "suitable": "不适合", "wait": "是，等趋势确认", "rr_block": False}

    if "收敛" in struct_t or "修复" in mid_trend:
        return {"type": "等待突破方向确认", "suitable": "暂不适合", "wait": "是", "rr_block": False}

    return {"type": "观望", "suitable": "暂不适合", "wait": "是，等信号明确", "rr_block": False}


def event_risk(ticker):
    """事件风险：明确标注检测局限性"""
    detected = False
    event_str = ""
    risk_level = "低"
    action = "正常执行"

    try:
        cal = yf.Ticker(ticker).calendar
        if cal is not None and not cal.empty:
            ed = cal.iloc[0, 0] if isinstance(cal, pd.DataFrame) else None
            if ed:
                delta = (pd.Timestamp(ed) - pd.Timestamp.now()).days
                if 0 <= delta <= 7:
                    event_str = f"财报将在{delta}天后发布"
                    risk_level = "高"
                    action = "事件后再交易"
                    detected = True
                elif 0 <= delta <= 14:
                    event_str = f"财报将在{delta}天后发布"
                    risk_level = "中"
                    action = "降低仓位"
                    detected = True
    except Exception:
        pass

    if not detected:
        event_str = "系统未检测到已知财报事件"

    return {
        "event":       event_str,
        "risk":        risk_level,
        "action":      action,
        # 明确标注局限性，不说"低风险"
        "disclaimer":  "⚠️ 系统仅检测财报日期，FOMC/CPI/期权到期等宏观事件需人工确认",
    }


# ── 主分析函数 ───────────────────────────────────────────────

def analyze_ticker(ticker, ref_cache):
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

    # 0. 周期
    trading_cycle = {"cycle": "波段交易（日线为主）", "conclusion": "基于日线数据，适合波段交易"}
    print("  [0] ✓")

    # 1. 市场背景
    mkt = market_background(ticker, ref_cache)
    print("  [1] ✓")

    # 2. 长期趋势
    ma200_dev  = round((price - ma200) / ma200 * 100, 2)
    long_trend = ("多头"       if price > ma200 and s200 > 0.05 else
                  "中性偏多"   if price > ma200 else
                  "方向选择区" if abs(price - ma200) / ma200 < 0.03 else "空头")
    print(f"  [2] {long_trend} ✓")

    # 3. 中期趋势
    mid_trend = ("强多头排列" if price > ma20 and ma20 > ma60 and ma60 > ma200 else
                 "多头修复"   if price > ma20 and ma20 > ma60 else
                 "短线反弹"   if price > ma20 else
                 "中期调整"   if ma20 < ma60  else "空头排列")
    print(f"  [3] {mid_trend} ✓")

    # 4. 价格结构（含创前高处理）
    atr_raw   = calc_atr(df["High"], df["Low"], df["Close"])
    atr_val   = float(atr_raw.iloc[-1])
    swing_ord = max(5, min(int(atr_val / price * 1000), 15))
    highs, lows = find_swing_points(df["Close"], order=swing_ord)

    breakout_info = analyze_breakout(df, highs, lows, atr_val)

    if breakout_info:
        struct_t = breakout_info["struct_type"]
        struct_c = breakout_info["struct_conclusion"]
    else:
        # 均线兜底：均线多头时不允许输出"下降结构确认"
        struct_t, struct_c = structure_type_original(highs, lows)
        if ("下降结构" in struct_t and "确认" in struct_c and
                "多头" in long_trend and "多头" in mid_trend):
            struct_t = "结构冲突·均线优先"
            struct_c = "均线多头排列与摆动点结构冲突，以均线判断为准，需人工复核"

    print(f"  [4] {struct_t} ✓")

    # 5. 关键位置
    levels = key_levels(df)
    print("  [5] ✓")

    # 6. 相对强弱
    rs = relative_strength(ticker, df, ref_cache)
    print("  [6] ✓")

    # 7. 量价
    vol = volume_analysis(df)
    print("  [7] ✓")

    # 8. 动量
    mom = momentum_analysis(df)
    print("  [8] ✓")

    # 9. 波动率
    vol_state = volatility_analysis(df)
    print("  [9] ✓")

    # 11. 风险赔率（先算，再决定交易类型）
    risk = calc_risk_reward(price, atr_val, levels, breakout_info)
    print("  [11] ✓")

    # 10. 交易类型（受赔率约束）
    trade = trade_type(long_trend, mid_trend, struct_t,
                       mom["rsi_val"], price, ma20, risk["rr_pass"])
    print(f"  [10] {trade['type']} ✓")

    # 12. 事件风险
    evt = event_risk(ticker)
    print(f"  [12] {evt['risk']} ✓")

    return {
        "ticker": ticker, "price": price,
        "date":   df.index[-1].strftime("%Y-%m-%d"),
        "df":     df,
        "0_cycle":      trading_cycle,
        "1_market":     mkt,
        "2_long_trend": {"ma200": ma200, "deviation": ma200_dev,
                         "slope": slope_label(s200), "conclusion": long_trend},
        "3_mid_trend":  {"ma20": ma20, "ma60": ma60,
                         "slope20": slope_label(s20), "slope60": slope_label(s60),
                         "conclusion": mid_trend},
        "4_structure":  {"highs":         [(str(d.date()), v) for d, v in highs],
                         "lows":          [(str(d.date()), v) for d, v in lows],
                         "type":          struct_t,
                         "conclusion":    struct_c,
                         "breakout_info": breakout_info},
        "5_levels":     levels,
        "6_rs":         rs,
        "7_volume":     vol,
        "8_momentum":   mom,
        "9_volatility": vol_state,
        "10_trade":     trade,
        "11_risk":      risk,
        "12_event":     evt,
    }


def analyze_all(tickers=None):
    if tickers is None:
        tickers = STOCK_POOL
    print("\n[预处理] 拉取参考ETF数据...")
    ref_cache = fetch_all_ref_data()
    print(f"[预处理] 完成，缓存：{list(ref_cache.keys())}")
    results = []
    for ticker in tickers:
        results.append(analyze_ticker(ticker, ref_cache))
        time.sleep(random.uniform(1, 2))
    return results


if __name__ == "__main__":
    r = analyze_all(["SPY", "TSLA"])[0]
    bi = r["4_structure"].get("breakout_info")
    print(f"\n✅ {r['ticker']} @ {r['price']}")
    print(f"   结构：{r['4_structure']['type']}")
    print(f"   突破信息：{bi}")
    print(f"   赔率：{r['11_risk']['conclusion']}")
