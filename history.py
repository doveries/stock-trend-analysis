"""
历史档案模块
记录每日关键状态，用于检测变化、生成今日动作卡
保留最近30天数据
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

HISTORY_FILE = "history.json"
KEEP_DAYS    = 30


def load_history():
    """加载历史档案"""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 历史档案加载失败: {e}")
        return {}


def save_history(history):
    """保存历史档案，自动清理超过30天的数据"""
    cutoff = (datetime.now() - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    history = {k: v for k, v in history.items() if k >= cutoff}
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ 历史档案保存失败: {e}")
        return False


def extract_snapshot(results, ai_results=None):
    """从分析结果提取当日快照"""
    snapshot = {}
    for r in results:
        if "error" in r:
            continue
        ticker = r["ticker"]
        ai     = (ai_results or {}).get(ticker, {})
        oj     = ai.get("opus_judge", {}) or {}
        gj     = ai.get("gpt_judge",  {}) or {}

        opus_dec = oj.get("final_decision", "") if not oj.get("error") else ""
        gpt_dec  = gj.get("final_decision", "") if not gj.get("error") else ""

        snapshot[ticker] = {
            "price":          r["price"],
            "long_trend":     r["2_long_trend"]["conclusion"],
            "mid_trend":      r["3_mid_trend"]["conclusion"],
            "structure":      r["4_structure"]["type"],
            "rsi":            r["8_momentum"]["rsi_val"],
            "rr_pass":        r["11_risk"]["rr_pass"],
            "resistance":     r["5_levels"]["resistance"],
            "support":        r["5_levels"]["support"],
            "invalidation":   r["5_levels"]["invalidation"],
            "atr":            r["9_volatility"]["atr"],
            "opus_decision":  opus_dec,
            "gpt_decision":   gpt_dec,
            "event_risk":     r["12_event"]["risk"],
        }
    return snapshot


def update_history(today_snapshot):
    """更新今日数据到历史档案"""
    history = load_history()
    today   = datetime.now().strftime("%Y-%m-%d")
    history[today] = today_snapshot
    save_history(history)
    return history


def get_yesterday_snapshot(history):
    """获取最近一次（不含今天）的快照"""
    today = datetime.now().strftime("%Y-%m-%d")
    dates = sorted([d for d in history.keys() if d < today], reverse=True)
    if not dates:
        return None, None
    return dates[0], history[dates[0]]


def detect_changes(today_snapshot, yesterday_snapshot):
    """
    检测变化，返回每只股票的变化列表
    变化类型：
    - approach_trigger: 接近触发位（< 1×ATR）
    - structure_change: 结构状态突变
    - trend_change:     趋势变化
    - decision_change:  AI建议变化
    - event_alert:      事件风险升高
    """
    changes = {}
    if not yesterday_snapshot:
        return changes

    for ticker, today in today_snapshot.items():
        yesterday = yesterday_snapshot.get(ticker)
        ticker_changes = []

        # ── 变化1：接近触发位（无需历史对比）────────────────
        atr = today.get("atr", 0)
        if atr > 0:
            price        = today["price"]
            resistance   = today["resistance"]
            support      = today["support"]
            invalidation = today["invalidation"]

            if 0 < (resistance - price) <= atr:
                dist = round(resistance - price, 2)
                ticker_changes.append({
                    "type":  "approach_trigger",
                    "level": "resistance",
                    "msg":   f"逼近阻力位 ${resistance}（距离 ${dist}，约{round(dist/atr,1)}×ATR）",
                    "priority": 1,
                })

            if 0 < (price - support) <= atr * 0.5:
                dist = round(price - support, 2)
                ticker_changes.append({
                    "type":  "approach_trigger",
                    "level": "support",
                    "msg":   f"逼近支撑位 ${support}（距离 ${dist}）",
                    "priority": 1,
                })

            if 0 < (price - invalidation) <= atr:
                dist = round(price - invalidation, 2)
                ticker_changes.append({
                    "type":  "approach_trigger",
                    "level": "invalidation",
                    "msg":   f"⚠️ 逼近失效位 ${invalidation}（距离 ${dist}）",
                    "priority": 0,
                })

        # ── 需要历史对比的变化 ─────────────────────────────
        if yesterday:
            # 变化2：结构突变
            if today["structure"] != yesterday.get("structure"):
                ticker_changes.append({
                    "type":  "structure_change",
                    "msg":   f"结构变化：{yesterday.get('structure','?')} → {today['structure']}",
                    "priority": 1,
                })

            # 变化3：长期/中期趋势变化
            if today["long_trend"] != yesterday.get("long_trend"):
                ticker_changes.append({
                    "type":  "trend_change",
                    "msg":   f"长期趋势：{yesterday.get('long_trend','?')} → {today['long_trend']}",
                    "priority": 0,
                })
            elif today["mid_trend"] != yesterday.get("mid_trend"):
                ticker_changes.append({
                    "type":  "trend_change",
                    "msg":   f"中期趋势：{yesterday.get('mid_trend','?')} → {today['mid_trend']}",
                    "priority": 1,
                })

            # 变化4：AI建议变化（任一裁判变化都算）
            opus_changed = today["opus_decision"] != yesterday.get("opus_decision","")
            gpt_changed  = today["gpt_decision"]  != yesterday.get("gpt_decision","")
            if opus_changed:
                ticker_changes.append({
                    "type": "decision_change",
                    "msg":  f"Opus裁判：{yesterday.get('opus_decision','?')} → {today['opus_decision']}",
                    "priority": 1,
                })
            if gpt_changed:
                ticker_changes.append({
                    "type": "decision_change",
                    "msg":  f"GPT裁判：{yesterday.get('gpt_decision','?')} → {today['gpt_decision']}",
                    "priority": 1,
                })

            # 变化5：赔率pass状态变化
            if today["rr_pass"] != yesterday.get("rr_pass"):
                if today["rr_pass"]:
                    ticker_changes.append({
                        "type": "rr_change",
                        "msg":  "赔率从不合格 → 合格（可能出现交易机会）",
                        "priority": 0,
                    })
                else:
                    ticker_changes.append({
                        "type": "rr_change",
                        "msg":  "赔率从合格 → 不合格（机会窗口关闭）",
                        "priority": 1,
                    })

        # 变化6：事件风险（只在升高时提示）
        if today["event_risk"] in ("高", "中"):
            yesterday_event = yesterday.get("event_risk", "低") if yesterday else "低"
            if today["event_risk"] != yesterday_event:
                ticker_changes.append({
                    "type": "event_alert",
                    "msg":  f"事件风险：{yesterday_event} → {today['event_risk']}",
                    "priority": 0,
                })

        if ticker_changes:
            ticker_changes.sort(key=lambda x: x["priority"])
            changes[ticker] = ticker_changes

    return changes


def build_action_summary(today_snapshot, changes):
    """
    生成今日动作摘要
    返回 (need_attention_tickers, no_action_tickers)
    """
    need_attention = []
    no_action      = []

    for ticker in today_snapshot.keys():
        if ticker in changes:
            need_attention.append(ticker)
        else:
            # 没变化但opus或gpt是非"等待"的也归到关注列
            snap = today_snapshot[ticker]
            opus = snap.get("opus_decision", "")
            gpt  = snap.get("gpt_decision", "")
            # 只有"持有/不交易/等待确认"这种稳态才进入"无需操作"
            if any(x in (opus, gpt) for x in ["买入", "试多"]):
                need_attention.append(ticker)
            else:
                no_action.append(ticker)

    return need_attention, no_action


if __name__ == "__main__":
    print("history.py 测试")
    h = load_history()
    print(f"  历史档案：{len(h)} 天")
    yd, ys = get_yesterday_snapshot(h)
    print(f"  最近一次：{yd}")
