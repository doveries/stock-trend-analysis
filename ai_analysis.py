"""
V2 AI分析模块
并行调用 Claude Opus 4.7 / GPT-5.5 / DeepSeek V4 Pro
最终由 Claude Opus 4.7 做元分析（综合裁判）
每个模型每天 $5 限额保护
"""

import asyncio
import aiohttp
import json
import os
import time
from datetime import datetime

# ── 模型配置 ─────────────────────────────────────────────────
MODELS = {
    "claude":   "anthropic/claude-opus-4.7",
    "gpt":      "openai/gpt-5.5",
    "deepseek": "deepseek/deepseek-v4-pro",
}
JUDGE_MODEL = "anthropic/claude-opus-4.7"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# 每个模型每天费用上限（美元）
DAILY_BUDGET_PER_MODEL = 5.0

# 粗略价格估算（$/1K output tokens），用于限额检查
MODEL_PRICE_PER_1K = {
    "anthropic/claude-opus-4.7": 0.015,
    "openai/gpt-5.5":            0.020,
    "deepseek/deepseek-v4-pro":  0.002,
}

# 请求超时（秒）
REQUEST_TIMEOUT = 90


# ── 费用追踪 ─────────────────────────────────────────────────

class CostTracker:
    def __init__(self):
        self.usage = {}   # model -> {tokens, cost}

    def record(self, model: str, output_tokens: int):
        price = MODEL_PRICE_PER_1K.get(model, 0.01)
        cost  = output_tokens / 1000 * price
        if model not in self.usage:
            self.usage[model] = {"tokens": 0, "cost": 0.0}
        self.usage[model]["tokens"] += output_tokens
        self.usage[model]["cost"]   += cost

    def check_budget(self, model: str) -> bool:
        """返回True表示未超限，可以继续调用"""
        current = self.usage.get(model, {}).get("cost", 0.0)
        return current < DAILY_BUDGET_PER_MODEL

    def summary(self) -> dict:
        total = sum(v["cost"] for v in self.usage.values())
        return {
            "per_model": {k: {"tokens": v["tokens"], "cost": round(v["cost"], 4)}
                          for k, v in self.usage.items()},
            "total_cost": round(total, 4),
            "budget_per_model": DAILY_BUDGET_PER_MODEL,
        }


# ── Prompt构建 ───────────────────────────────────────────────

def build_analysis_prompt(result: dict) -> str:
    """把12项框架数据格式化为AI可读的结构化prompt"""
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

    prompt = f"""你是专业技术分析师，以下是 {t} 的系统化技术分析数据（{d}），请基于这些数据给出你的判断。

【基础信息】
标的：{t} | 当前价：${p} | 分析日期：{d}

【长期趋势（MA200维度）】
MA200：${r2['ma200']} | 价格偏离：{r2['deviation']}% | MA200斜率：{r2['slope']}
结论：{r2['conclusion']}

【中期趋势（MA20/MA60维度）】
MA20：${r3['ma20']}（{r3['slope20']}）| MA60：${r3['ma60']}（{r3['slope60']}）
结论：{r3['conclusion']}

【价格结构】
近期高点序列：{highs_str}
近期低点序列：{lows_str}
结构类型：{r4['type']} | 确认状态：{r4['conclusion']}

【关键价格位】
最近阻力：${r5['resistance']} | 关键确认位：${r5['confirm']}
最近支撑：${r5['support']} | 结构失效位：${r5['invalidation']}

【相对强弱（近20日）】
vs {r6['index_name']}：{r6['vs_index']}
vs {r6['sector_name']}：{r6['vs_sector']}
结论：{r6['conclusion']}

【量价确认（近10日）】
上涨日均量：{r7['up_vol']}M | 下跌日均量：{r7['down_vol']}M | 量价比：{r7['ratio']}
结论：{r7['conclusion']}

【动量状态】
RSI(14)：{r8['rsi']} | MACD：{r8['macd']}
MACD柱状图：{r8['histogram']}
结论：{r8['conclusion']}

【波动率状态】
ATR(14)：${r9['atr']}（占价格{r9['atr_pct']}%）| 布林带宽度：{r9['bw_val']}
波动率状态：{r9['vol_state']} | 仓位影响：{r9['pos_impact']}

【交易类型判断】
类型：{r10['type']} | 是否适合：{r10['suitable']} | 是否等待确认：{r10['wait']}

【风险参考位（需人工确认）】
短线止损参考：${r11['short_stop']} | 中期止损参考：${r11['mid_stop']} | 结构止损参考：${r11['structure_stop']}
目标一参考：${r11['target1']} | 目标二参考：${r11['target2']}

【事件风险】
{r12['event']} | 风险等级：{r12['risk']} | 建议：{r12['action']}

---
请严格按以下JSON格式输出，不要有任何额外文字：
{{
  "decision": "买入/小仓试多/持有/等待确认/不交易",
  "reason": "核心理由，100字以内",
  "key_risk": "最大风险点，50字以内",
  "confidence": "高/中/低",
  "support_zone": "{r5['support']}-{r5['invalidation']}",
  "resistance_zone": "{r5['resistance']}"
}}"""
    return prompt


def build_judge_prompt(ticker: str, price: float,
                       claude_result: dict, gpt_result: dict, deepseek_result: dict) -> str:
    """元分析prompt：让Opus综合三个模型的结论"""

    def fmt(name, r):
        if r.get("error"):
            return f"【{name}】调用失败：{r['error']}"
        return (f"【{name}】\n"
                f"  决策：{r.get('decision','N/A')} | 置信度：{r.get('confidence','N/A')}\n"
                f"  理由：{r.get('reason','N/A')}\n"
                f"  最大风险：{r.get('key_risk','N/A')}")

    return f"""你是资深投资顾问，以下是三个AI模型对 {ticker}（当前价 ${price}）的独立技术分析结论：

{fmt('Claude Opus 4.7', claude_result)}

{fmt('GPT-5.5', gpt_result)}

{fmt('DeepSeek V4 Pro', deepseek_result)}

请综合以上三个模型的判断，输出元分析结论。严格按以下JSON格式，不要有额外文字：
{{
  "consensus": "三模型共同点，60字以内",
  "divergence": "三模型分歧点，60字以内，如无分歧填'三模型判断基本一致'",
  "final_decision": "买入/小仓试多/持有/等待确认/不交易",
  "final_reason": "综合裁判理由，120字以内",
  "final_confidence": "高/中/低",
  "model_agreement": "高度一致/基本一致/存在分歧/明显分歧"
}}"""


# ── API调用 ──────────────────────────────────────────────────

async def call_openrouter(session: aiohttp.ClientSession,
                          model: str, prompt: str,
                          api_key: str, tracker: CostTracker) -> dict:
    """单次异步调用OpenRouter"""
    if not tracker.check_budget(model):
        return {"error": f"已超出今日预算 ${DAILY_BUDGET_PER_MODEL}"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://github.com/doveries/stock-trend-analysis",
        "X-Title":       "Stock Technical Analysis",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.3,
    }

    try:
        async with session.post(
            OPENROUTER_URL, headers=headers, json=payload,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as resp:
            data = await resp.json()

            if resp.status != 200:
                return {"error": f"HTTP {resp.status}: {data.get('error', {}).get('message', str(data))}"}

            content = data["choices"][0]["message"]["content"].strip()
            output_tokens = data.get("usage", {}).get("completion_tokens", 200)
            tracker.record(model, output_tokens)

            # 解析JSON
            try:
                # 去掉可能的markdown代码块
                clean = content.replace("```json", "").replace("```", "").strip()
                return json.loads(clean)
            except json.JSONDecodeError:
                return {"error": f"JSON解析失败", "raw": content[:200]}

    except asyncio.TimeoutError:
        return {"error": f"请求超时（>{REQUEST_TIMEOUT}s）"}
    except Exception as e:
        return {"error": str(e)}


async def analyze_one_ticker_async(session: aiohttp.ClientSession,
                                   result: dict, api_key: str,
                                   tracker: CostTracker) -> dict:
    """对单只股票并行调用三个模型，然后元分析"""
    ticker = result["ticker"]
    price  = result["price"]
    prompt = build_analysis_prompt(result)

    print(f"  [{ticker}] 并行调用三模型...")

    # 并行调用
    claude_task   = call_openrouter(session, MODELS["claude"],   prompt, api_key, tracker)
    gpt_task      = call_openrouter(session, MODELS["gpt"],      prompt, api_key, tracker)
    deepseek_task = call_openrouter(session, MODELS["deepseek"], prompt, api_key, tracker)

    claude_r, gpt_r, deepseek_r = await asyncio.gather(
        claude_task, gpt_task, deepseek_task
    )

    print(f"  [{ticker}] Claude: {claude_r.get('decision', claude_r.get('error', '?'))}")
    print(f"  [{ticker}] GPT:    {gpt_r.get('decision', gpt_r.get('error', '?'))}")
    print(f"  [{ticker}] DS:     {deepseek_r.get('decision', deepseek_r.get('error', '?'))}")

    # 元分析
    judge_prompt = build_judge_prompt(ticker, price, claude_r, gpt_r, deepseek_r)
    judge_r = await call_openrouter(session, JUDGE_MODEL, judge_prompt, api_key, tracker)
    print(f"  [{ticker}] 元分析: {judge_r.get('final_decision', judge_r.get('error', '?'))}")

    return {
        "ticker":   ticker,
        "claude":   claude_r,
        "gpt":      gpt_r,
        "deepseek": deepseek_r,
        "judge":    judge_r,
    }


async def run_ai_analysis_async(results: list, api_key: str) -> tuple:
    """对所有股票跑AI分析，返回(ai_results, cost_summary)"""
    tracker = CostTracker()
    ai_results = {}

    # 过滤掉数据获取失败的标的
    valid = [r for r in results if "error" not in r]

    async with aiohttp.ClientSession() as session:
        # 股票之间串行（避免同时发太多请求），每只内部并行
        for r in valid:
            ai_result = await analyze_one_ticker_async(session, r, api_key, tracker)
            ai_results[r["ticker"]] = ai_result
            await asyncio.sleep(2)  # 股票间间隔2秒

    return ai_results, tracker.summary()


def run_ai_analysis(results: list) -> tuple:
    """同步入口，供main.py调用"""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("⚠️ 未找到 OPENROUTER_API_KEY，跳过AI分析")
        return {}, {}

    print(f"\n{'='*60}")
    print(f"  V2 AI综合分析")
    print(f"  模型：{', '.join(MODELS.values())}")
    print(f"  预算：每模型 ${DAILY_BUDGET_PER_MODEL}/天")
    print(f"{'='*60}")

    start = time.time()
    ai_results, cost = asyncio.run(run_ai_analysis_async(results, api_key))
    elapsed = round(time.time() - start, 1)

    print(f"\n✅ AI分析完成，耗时 {elapsed}s")
    print(f"   总费用：${cost.get('total_cost', 0)}")
    for model, info in cost.get("per_model", {}).items():
        print(f"   {model}: {info['tokens']} tokens = ${info['cost']}")

    return ai_results, cost


if __name__ == "__main__":
    # 本地测试
    from analyze import analyze_all
    results = analyze_all(["TSLA"])
    ai_results, cost = run_ai_analysis(results)
    print(json.dumps(ai_results, ensure_ascii=False, indent=2))
    print("费用:", cost)
