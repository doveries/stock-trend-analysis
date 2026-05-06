"""
V2 AI分析模块
并行调用 Claude Opus 4.7 / GPT-5.5 / DeepSeek V4 Pro
元分析由 Opus 4.7 和 GPT-5.5 各自独立解读一遍
每个模型每天 $5 限额保护
"""

import asyncio
import aiohttp
import json
import os
import time

MODELS = {
    "claude":   "anthropic/claude-opus-4.7",
    "gpt":      "openai/gpt-5.5",
    "deepseek": "deepseek/deepseek-v4-pro",
}
JUDGE_MODELS = {
    "opus_judge": "anthropic/claude-opus-4.7",
    "gpt_judge":  "openai/gpt-5.5",
}

OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"
DAILY_BUDGET       = 5.0
REQUEST_TIMEOUT    = 90

MODEL_PRICE_PER_1K = {
    "anthropic/claude-opus-4.7": 0.015,
    "openai/gpt-5.5":            0.020,
    "deepseek/deepseek-v4-pro":  0.002,
}


class CostTracker:
    def __init__(self):
        self.usage = {}

    def record(self, model, output_tokens):
        price = MODEL_PRICE_PER_1K.get(model, 0.01)
        cost  = output_tokens / 1000 * price
        if model not in self.usage:
            self.usage[model] = {"tokens": 0, "cost": 0.0}
        self.usage[model]["tokens"] += output_tokens
        self.usage[model]["cost"]   += cost

    def check_budget(self, model):
        return self.usage.get(model, {}).get("cost", 0.0) < DAILY_BUDGET

    def summary(self):
        total = sum(v["cost"] for v in self.usage.values())
        return {
            "per_model":  {k: {"tokens": v["tokens"], "cost": round(v["cost"], 4)}
                           for k, v in self.usage.items()},
            "total_cost": round(total, 4),
        }


def build_analysis_prompt(result):
    t   = result["ticker"]
    p   = result["price"]
    d   = result["date"]
    r2  = result["2_long_trend"]
    r3  = result["3_mid_trend"]
    r4  = result["4_structure"]
    r5  = result["5_levels"]
    r6  = result["6_rs"]
    r7  = result["7_volume"]
    r8  = result["8_momentum"]
    r9  = result["9_volatility"]
    r10 = result["10_trade"]
    r11 = result["11_risk"]
    r12 = result["12_event"]

    highs_str = " → ".join([f"${v}" for _, v in r4["highs"][-3:]]) or "数据不足"
    lows_str  = " → ".join([f"${v}" for _, v in r4["lows"][-3:]])  or "数据不足"
    bi        = r4.get("breakout_info") or {}
    breakout_str = (f"突破信息：{bi.get('struct_type','')}，质量评分{bi.get('score','N/A')}/5，"
                    f"{'历史新高区域' if bi.get('is_all_time_area') else '近期前高'}"
                    if bi else "无突破信号")

    return f"""你是专业技术分析师，以下是 {t} 的系统化技术分析数据（{d}），请基于这些数据给出判断。

【基础信息】标的：{t} | 当前价：${p} | 日期：{d}

【长期趋势】MA200：${r2['ma200']} | 偏离：{r2['deviation']}% | 斜率：{r2['slope']} | 结论：{r2['conclusion']}
【中期趋势】MA20：${r3['ma20']}（{r3['slope20']}）| MA60：${r3['ma60']}（{r3['slope60']}）| 结论：{r3['conclusion']}
【价格结构】{r4['type']} | {r4['conclusion']}
【突破分析】{breakout_str}
【近期高点】{highs_str}
【近期低点】{lows_str}
【关键位置】阻力：${r5['resistance']} | 确认位：${r5['confirm']} | 支撑：${r5['support']} | 失效位：${r5['invalidation']}
【相对强弱】vs {r6['index_name']}：{r6['vs_index']} | vs {r6['sector_name']}：{r6['vs_sector']} | 结论：{r6['conclusion']}
【量价】上涨均量：{r7['up_vol']}M | 下跌均量：{r7['down_vol']}M | 量价比：{r7['ratio']} | {r7['conclusion']}
【动量】RSI：{r8['rsi']} | MACD：{r8['macd']} | 柱状图：{r8['histogram']} | {r8['conclusion']}
【波动率】ATR：${r9['atr']}（{r9['atr_pct']}%）| 状态：{r9['vol_state']} | 仓位影响：{r9['pos_impact']}
【交易类型】{r10['type']} | 适合：{r10['suitable']} | 等待：{r10['wait']}
【赔率】目标一：${r11['target1']}（{r11['t1_rr']}:1）| 目标二：${r11['target2']}（{r11['t2_rr']}:1）| {r11['conclusion']}
【止损参考】短线：${r11['short_stop']} | 中期：${r11['mid_stop']} | 结构：${r11['structure_stop']}
【事件风险】{r12['event']} | 等级：{r12['risk']} | {r12['disclaimer']}

注意：如果赔率结论为"不合格"，你的决策不能输出"买入"或"小仓试多"。

请严格按以下JSON格式输出，不要有额外文字：
{{
  "decision": "买入/小仓试多/持有/等待确认/不交易",
  "reason": "核心理由，100字以内",
  "key_risk": "最大风险点，50字以内",
  "trigger": "触发买入/加仓的条件，60字以内",
  "confidence": "高/中/低"
}}"""


def build_judge_prompt(ticker, price, claude_r, gpt_r, deepseek_r, judge_role):
    """元分析prompt，judge_role区分Opus和GPT的视角"""
    role_str = ("作为Claude Opus，请从趋势跟踪和风险控制的角度综合评判"
                if judge_role == "opus" else
                "作为GPT-5.5，请从量化逻辑和概率分布的角度综合评判")

    def fmt(name, r):
        if not r or r.get("error"):
            return f"【{name}】调用失败"
        return (f"【{name}】决策：{r.get('decision','N/A')} | 置信度：{r.get('confidence','N/A')}\n"
                f"  理由：{r.get('reason','N/A')}\n"
                f"  触发条件：{r.get('trigger','N/A')}\n"
                f"  风险：{r.get('key_risk','N/A')}")

    return f"""{role_str}，以下是三个AI模型对 {ticker}（当前价 ${price}）的独立技术分析：

{fmt('Claude Opus 4.7', claude_r)}

{fmt('GPT-5.5', gpt_r)}

{fmt('DeepSeek V4 Pro', deepseek_r)}

请综合输出元分析结论。严格按以下JSON格式，不要有额外文字：
{{
  "consensus": "三模型共同点，60字以内",
  "divergence": "分歧点，60字以内，无分歧填'判断基本一致'",
  "final_decision": "买入/小仓试多/持有/等待确认/不交易",
  "final_reason": "综合理由，120字以内",
  "final_trigger": "触发条件，80字以内",
  "final_confidence": "高/中/低",
  "model_agreement": "高度一致/基本一致/存在分歧/明显分歧"
}}"""


async def call_openrouter(session, model, prompt, api_key, tracker):
    if not tracker.check_budget(model):
        return {"error": f"已超出今日预算 ${DAILY_BUDGET}"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://github.com/doveries/stock-trend-analysis",
        "X-Title":       "Stock Technical Analysis",
    }
    payload = {
        "model":       model,
        "messages":    [{"role": "user", "content": prompt}],
        "max_tokens":  600,
        "temperature": 0.3,
    }

    try:
        async with session.post(
            OPENROUTER_URL, headers=headers, json=payload,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as resp:
            data = await resp.json()
            if resp.status != 200:
                return {"error": f"HTTP {resp.status}: {data.get('error',{}).get('message', str(data))}"}

            content = data["choices"][0]["message"]["content"].strip()
            tracker.record(model, data.get("usage", {}).get("completion_tokens", 300))

            try:
                clean = content.replace("```json", "").replace("```", "").strip()
                return json.loads(clean)
            except json.JSONDecodeError:
                return {"error": "JSON解析失败", "raw": content[:200]}

    except asyncio.TimeoutError:
        return {"error": f"请求超时（>{REQUEST_TIMEOUT}s）"}
    except Exception as e:
        return {"error": str(e)}


async def analyze_one_ticker_async(session, result, api_key, tracker):
    ticker = result["ticker"]
    price  = result["price"]
    prompt = build_analysis_prompt(result)

    print(f"  [{ticker}] 并行调用三模型...")

    # 三模型并行
    claude_r, gpt_r, deepseek_r = await asyncio.gather(
        call_openrouter(session, MODELS["claude"],   prompt, api_key, tracker),
        call_openrouter(session, MODELS["gpt"],      prompt, api_key, tracker),
        call_openrouter(session, MODELS["deepseek"], prompt, api_key, tracker),
    )

    print(f"  [{ticker}] Claude: {claude_r.get('decision', claude_r.get('error','?'))}")
    print(f"  [{ticker}] GPT:    {gpt_r.get('decision', gpt_r.get('error','?'))}")
    print(f"  [{ticker}] DS:     {deepseek_r.get('decision', deepseek_r.get('error','?'))}")

    # 元分析：Opus和GPT各自独立解读，并行跑
    opus_prompt = build_judge_prompt(ticker, price, claude_r, gpt_r, deepseek_r, "opus")
    gpt_prompt  = build_judge_prompt(ticker, price, claude_r, gpt_r, deepseek_r, "gpt")

    opus_judge, gpt_judge = await asyncio.gather(
        call_openrouter(session, JUDGE_MODELS["opus_judge"], opus_prompt, api_key, tracker),
        call_openrouter(session, JUDGE_MODELS["gpt_judge"],  gpt_prompt,  api_key, tracker),
    )

    print(f"  [{ticker}] Opus元分析: {opus_judge.get('final_decision', opus_judge.get('error','?'))}")
    print(f"  [{ticker}] GPT元分析:  {gpt_judge.get('final_decision', gpt_judge.get('error','?'))}")

    return {
        "ticker":     ticker,
        "claude":     claude_r,
        "gpt":        gpt_r,
        "deepseek":   deepseek_r,
        "opus_judge": opus_judge,
        "gpt_judge":  gpt_judge,
    }


async def run_ai_analysis_async(results, api_key):
    tracker    = CostTracker()
    ai_results = {}
    valid      = [r for r in results if "error" not in r]

    async with aiohttp.ClientSession() as session:
        for r in valid:
            ai_result = await analyze_one_ticker_async(session, r, api_key, tracker)
            ai_results[r["ticker"]] = ai_result
            await asyncio.sleep(2)

    return ai_results, tracker.summary()


def run_ai_analysis(results):
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("⚠️ 未找到 OPENROUTER_API_KEY，跳过AI分析")
        return {}, {}

    print(f"\n{'='*60}")
    print(f"  V2 AI综合分析（元分析：Opus + GPT双解读）")
    print(f"{'='*60}")

    start = time.time()
    ai_results, cost = asyncio.run(run_ai_analysis_async(results, api_key))
    elapsed = round(time.time() - start, 1)

    print(f"\n✅ AI分析完成，耗时 {elapsed}s | 总费用：${cost.get('total_cost',0)}")
    return ai_results, cost
