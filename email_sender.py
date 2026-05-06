"""
邮件发送模块 v2.2
彭博风格重设计：数据密度高，层级清晰，易读优先
"""

import smtplib, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

STYLE = """
<style>
* { box-sizing: border-box; }
body {
  font-family: 'SF Mono', 'Fira Code', 'Segoe UI', Arial, sans-serif;
  background: #0a0a0f;
  color: #c8ccd4;
  margin: 0; padding: 16px;
  font-size: 13px;
  line-height: 1.5;
}
.container { max-width: 900px; margin: 0 auto; }

/* ── 顶部 header ── */
.header {
  border-left: 3px solid #4a9eff;
  padding: 10px 16px;
  margin-bottom: 20px;
  background: #0f0f1a;
}
.header-title {
  font-size: 16px; font-weight: 700;
  color: #e0e4ef; letter-spacing: 1px;
  text-transform: uppercase;
}
.header-sub { color: #5a6070; font-size: 11px; margin-top: 2px; }

/* ── 区块标题 ── */
.section-header {
  font-size: 10px; font-weight: 700;
  color: #4a9eff;
  text-transform: uppercase;
  letter-spacing: 2px;
  padding: 6px 0 4px 0;
  border-bottom: 1px solid #1e2030;
  margin-bottom: 12px;
}

/* ── 总览表格 ── */
.overview-wrap { margin-bottom: 20px; }
.overview-table {
  width: 100%; border-collapse: collapse;
  font-size: 12px;
}
.overview-table th {
  color: #4a6080; font-weight: 600;
  text-transform: uppercase; font-size: 10px;
  letter-spacing: 1px;
  padding: 6px 10px;
  border-bottom: 1px solid #1e2030;
  text-align: left;
  background: #0a0a0f;
}
.overview-table td {
  padding: 7px 10px;
  border-bottom: 1px solid #12121a;
  vertical-align: middle;
}
.overview-table tr:hover td { background: #0f0f1a; }
.ov-ticker { font-weight: 700; color: #e0e4ef; font-size: 13px; }
.ov-price  { color: #4a9eff; font-weight: 600; }
.tag {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 2px;
  font-size: 10px; font-weight: 700;
  letter-spacing: 0.5px;
}
.tag-buy    { background: #0d2a1a; color: #3ddc84; border: 1px solid #1a4a2a; }
.tag-trial  { background: #0d2a1a; color: #69f0ae; border: 1px solid #1a4a2a; }
.tag-hold   { background: #0d1a3a; color: #5b9eff; border: 1px solid #1a2a5a; }
.tag-wait   { background: #2a1a06; color: #ffb74d; border: 1px solid #4a3010; }
.tag-no     { background: #2a0d0d; color: #ff5252; border: 1px solid #4a1a1a; }
.tag-na     { background: #1a1a2a; color: #5a6070; border: 1px solid #2a2a3a; }

/* 颜色 */
.bull { color: #3ddc84; }
.bear { color: #ff5252; }
.warn { color: #ffb74d; }
.muted { color: #5a6070; }
.blue { color: #4a9eff; }

/* ── 执行摘要 ── */
.exec-summary {
  background: #0f0f1a;
  border: 1px solid #1e2030;
  border-radius: 2px;
  padding: 10px 16px;
  margin-bottom: 20px;
  font-size: 12px;
  color: #8a90a0;
}
.exec-summary-items {
  display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;
}

/* ── AI区块 ── */
.ai-wrap { margin-bottom: 24px; }

/* AI横向对比表 */
.ai-matrix-table {
  width: 100%; border-collapse: collapse;
  font-size: 11px; margin-bottom: 20px;
}
.ai-matrix-table th {
  color: #4a6080; font-weight: 600;
  text-transform: uppercase; font-size: 10px;
  letter-spacing: 0.5px;
  padding: 5px 8px;
  border-bottom: 1px solid #1e2030;
  text-align: center;
  background: #0a0a0f;
}
.ai-matrix-table th:first-child { text-align: left; }
.ai-matrix-table td {
  padding: 6px 8px;
  border-bottom: 1px solid #12121a;
  text-align: center;
  vertical-align: middle;
}
.ai-matrix-table td:first-child { text-align: left; }
.ai-matrix-table tr:hover td { background: #0f0f1a; }
.matrix-ticker { font-weight: 700; color: #e0e4ef; }
.matrix-price  { color: #5a6070; font-size: 10px; }
.conf-badge {
  font-size: 9px; color: #5a6070;
  display: block; margin-top: 1px;
}

/* AI详细理由区块 */
.ai-detail-block { margin-bottom: 20px; }
.ai-ticker-header {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #1e2030;
  margin-bottom: 12px;
}
.ai-ticker-name { font-size: 14px; font-weight: 700; color: #e0e4ef; }
.ai-ticker-price { font-size: 12px; color: #4a9eff; }

.ai-models-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
.ai-model-col { }
.ai-model-label {
  font-size: 9px; font-weight: 700;
  color: #4a6080; text-transform: uppercase;
  letter-spacing: 1px; margin-bottom: 4px;
}
.ai-model-decision {
  font-size: 13px; font-weight: 700;
  margin-bottom: 4px;
}
.ai-model-body {
  font-size: 11px; color: #8a90a0;
  line-height: 1.6; margin-bottom: 6px;
}
.ai-model-trigger {
  font-size: 11px; color: #3daa6a;
  padding-left: 10px; position: relative;
  margin-bottom: 3px;
}
.ai-model-trigger::before { content: "📍 "; }
.ai-model-risk {
  font-size: 11px; color: #cc6644;
  padding-left: 10px; position: relative;
}
.ai-model-risk::before { content: "⚠️ "; }

/* 双元裁判 */
.judge-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding-top: 10px;
  border-top: 1px solid #1e2030;
}
.judge-col { }
.judge-label {
  font-size: 9px; font-weight: 700;
  color: #4a6080; text-transform: uppercase;
  letter-spacing: 1px; margin-bottom: 4px;
}
.judge-decision {
  font-size: 13px; font-weight: 700; margin-bottom: 4px;
}
.judge-agree {
  display: inline-block;
  font-size: 9px; color: #5a7090;
  border: 1px solid #2a3a4a;
  padding: 1px 5px; border-radius: 2px;
  margin-left: 6px; vertical-align: middle;
}
.judge-consensus { font-size: 11px; color: #5a9070; margin-bottom: 3px; }
.judge-divergence { font-size: 11px; color: #907050; margin-bottom: 4px; }
.judge-body { font-size: 11px; color: #8a90a0; line-height: 1.6; margin-bottom: 4px; }
.judge-trigger { font-size: 11px; color: #3daa6a; }
.judge-trigger::before { content: "📍 "; }

/* ── 逐股详情 ── */
.stock-wrap { margin-bottom: 28px; }
.stock-header {
  display: flex; align-items: baseline;
  gap: 12px; padding: 8px 0;
  border-bottom: 2px solid #1e2030;
  margin-bottom: 12px;
}
.stock-name { font-size: 18px; font-weight: 700; color: #e0e4ef; }
.stock-price { font-size: 16px; color: #4a9eff; }
.stock-date  { font-size: 11px; color: #5a6070; }

/* 一行结论摘要 */
.stock-summary-line {
  font-size: 11px; color: #7a8090;
  margin-bottom: 12px;
  padding: 6px 10px;
  background: #0f0f1a;
  border-left: 2px solid #2a3a5a;
}
.stock-summary-line span { margin-right: 8px; }

/* 图表 */
.chart-wrap { margin-bottom: 14px; }
.chart-img { width: 100%; display: block; border: 1px solid #1e2030; }

/* 12项紧凑数据表 */
.data-section { margin-bottom: 10px; }
.data-section-title {
  font-size: 9px; font-weight: 700;
  color: #4a6070; text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 4px;
}
.data-table {
  width: 100%; border-collapse: collapse;
  font-size: 11px;
}
.data-table td {
  padding: 3px 8px 3px 0;
  vertical-align: top;
  border: none;
  width: 25%;
}
.data-key { color: #4a6070; white-space: nowrap; }
.data-val { color: #c0c4d0; font-weight: 500; }
.data-conclusion {
  font-size: 11px; font-weight: 600;
  margin-top: 3px; padding: 3px 8px;
  border-left: 2px solid #2a3a4a;
  color: #8a90a0;
}

/* 分隔线 */
.divider {
  border: none; border-top: 1px solid #1e2030;
  margin: 16px 0;
}

/* footer */
.footer {
  font-size: 10px; color: #3a4050;
  text-align: center; padding: 16px 0;
  border-top: 1px solid #1a1a2a;
  margin-top: 20px;
}
</style>
"""


# ── 工具函数 ─────────────────────────────────────────────────

def tc(text):
    if any(k in text for k in ["多头","支持","确认","放量","强","突破"]): return "bull"
    if any(k in text for k in ["空头","警惕","破坏","弱","假突破","不支持"]): return "bear"
    if any(k in text for k in ["观望","等待","不适合","存疑","冲突"]): return "warn"
    return "muted"


def dc(d):
    if not d or d == "N/A": return "muted"
    if "买入" in d: return "bull"
    if "试多" in d: return "bull"
    if "持有" in d: return "blue"
    if "不交易" in d: return "bear"
    return "warn"


def make_tag(decision):
    if not decision or decision == "N/A":
        return '<span class="tag tag-na">—</span>'
    if "买入" in decision:   return f'<span class="tag tag-buy">{decision}</span>'
    if "试多" in decision:   return f'<span class="tag tag-trial">{decision}</span>'
    if "持有" in decision:   return f'<span class="tag tag-hold">{decision}</span>'
    if "等待" in decision:   return f'<span class="tag tag-wait">{decision}</span>'
    if "不交易" in decision: return f'<span class="tag tag-no">{decision}</span>'
    return f'<span class="tag tag-na">{decision}</span>'


def get_ai_decisions(ai_data):
    """提取五个决策"""
    if not ai_data:
        return {k: "" for k in ["claude","gpt","deepseek","opus_judge","gpt_judge"]}
    def _d(m):
        r = ai_data.get(m, {})
        if not r or r.get("error"): return ""
        return r.get("decision", r.get("final_decision", ""))
    return {
        "claude":     _d("claude"),
        "gpt":        _d("gpt"),
        "deepseek":   _d("deepseek"),
        "opus_judge": ai_data.get("opus_judge",{}).get("final_decision","") if ai_data.get("opus_judge") and not ai_data.get("opus_judge",{}).get("error") else "",
        "gpt_judge":  ai_data.get("gpt_judge",{}).get("final_decision","")  if ai_data.get("gpt_judge")  and not ai_data.get("gpt_judge",{}).get("error")  else "",
    }


# ── 各区块构建 ────────────────────────────────────────────────

def build_overview(results, ai_results=None):
    rows = ""
    for r in results:
        if "error" in r: continue
        ticker = r["ticker"]
        lv     = r["5_levels"]
        r2     = r["2_long_trend"]
        r3     = r["3_mid_trend"]
        r11    = r["11_risk"]
        ai     = (ai_results or {}).get(ticker, {})
        d      = get_ai_decisions(ai)
        fd     = d["opus_judge"] or d["gpt_judge"] or ""

        rows += f"""<tr>
          <td><span class="ov-ticker">{ticker}</span></td>
          <td class="ov-price">${r['price']}</td>
          <td class="{tc(r2['conclusion'])}">{r2['conclusion']}</td>
          <td class="{tc(r3['conclusion'])}">{r3['conclusion']}</td>
          <td class="bear">${lv['resistance']}</td>
          <td class="bull">${lv['support']}</td>
          <td class="warn">${lv['invalidation']}</td>
          <td class="{'bull' if r11['rr_pass'] else 'bear'}" style="font-size:10px;">{r11['conclusion'][:14]}</td>
          <td>{make_tag(fd)}</td>
        </tr>"""

    return f"""<div class="overview-wrap">
      <div class="section-header">市场总览</div>
      <table class="overview-table">
        <thead><tr>
          <th>标的</th><th>现价</th><th>长期</th><th>中期</th>
          <th>阻力</th><th>支撑</th><th>失效位</th><th>赔率</th><th>AI建议</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""


def build_exec_summary(results, ai_results=None):
    items = []
    for r in results:
        if "error" in r: continue
        ticker = r["ticker"]
        ai     = (ai_results or {}).get(ticker, {})
        d      = get_ai_decisions(ai)
        fd     = d["opus_judge"] or d["gpt_judge"] or ""
        items.append(make_tag(fd) + f' <span style="color:#5a6070;font-size:11px;">{ticker}</span>')

    return f"""<div class="exec-summary">
      <div style="color:#4a6080;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:2px;">执行摘要</div>
      <div class="exec-summary-items">{''.join(items)}</div>
    </div>"""


def build_ai_section(results, ai_results=None):
    """AI分析区块：横向对比表 + 逐股详细理由"""
    if not ai_results:
        return ""

    # ── 横向对比表 ──
    matrix_rows = ""
    for r in results:
        if "error" in r: continue
        ticker = r["ticker"]
        ai     = ai_results.get(ticker, {})
        d      = get_ai_decisions(ai)

        def cell(key):
            dec = d[key]
            conf = ""
            raw = ai.get(key, {}) if key in ["claude","gpt","deepseek"] else ai.get(key, {})
            if raw and not raw.get("error"):
                conf_val = raw.get("confidence", raw.get("final_confidence",""))
                if conf_val:
                    conf = f'<span class="conf-badge">{conf_val}</span>'
            return f'<td>{make_tag(dec)}{conf}</td>'

        matrix_rows += f"""<tr>
          <td>
            <span class="matrix-ticker">{ticker}</span>
            <span class="matrix-price"> ${r['price']}</span>
          </td>
          {cell('claude')}{cell('gpt')}{cell('deepseek')}
          {cell('opus_judge')}{cell('gpt_judge')}
        </tr>"""

    matrix_html = f"""<table class="ai-matrix-table">
      <thead><tr>
        <th>标的</th>
        <th>Claude Opus 4.7</th><th>GPT-5.5</th><th>DeepSeek V4</th>
        <th>Opus 裁判</th><th>GPT 裁判</th>
      </tr></thead>
      <tbody>{matrix_rows}</tbody>
    </table>"""

    # ── 逐股详细理由 ──
    detail_html = ""
    for r in results:
        if "error" in r: continue
        ticker = r["ticker"]
        price  = r["price"]
        ai     = ai_results.get(ticker, {})
        if not ai:
            continue

        def model_col(name, label, key, is_judge=False):
            raw = ai.get(key, {})
            if not raw or raw.get("error"):
                return f'<div class="ai-model-col"><div class="ai-model-label">{label}</div><div class="muted" style="font-size:11px;">调用失败</div></div>'

            if is_judge:
                dec  = raw.get("final_decision","N/A")
                body = raw.get("final_reason","")
                trig = raw.get("final_trigger","")
                risk = ""
                conf = raw.get("final_confidence","")
                cons = raw.get("consensus","")
                divg = raw.get("divergence","")
                agr  = raw.get("model_agreement","")
                return f"""<div class="judge-col">
                  <div class="judge-label">{label}</div>
                  <div class="judge-decision {dc(dec)}">{dec}<span class="judge-agree">{agr}</span></div>
                  <div class="judge-consensus">✅ 共识：{cons}</div>
                  <div class="judge-divergence">🔀 分歧：{divg}</div>
                  <div class="judge-body">{body}</div>
                  {'<div class="judge-trigger">' + trig + '</div>' if trig else ''}
                </div>"""
            else:
                dec  = raw.get("decision","N/A")
                body = raw.get("reason","")
                trig = raw.get("trigger","")
                risk = raw.get("key_risk","")
                conf = raw.get("confidence","")
                return f"""<div class="ai-model-col">
                  <div class="ai-model-label">{label}</div>
                  <div class="ai-model-decision {dc(dec)}">{dec} <span style="font-size:10px;color:#5a6070;font-weight:400;">· {conf}</span></div>
                  <div class="ai-model-body">{body}</div>
                  {'<div class="ai-model-trigger">' + trig + '</div>' if trig else ''}
                  {'<div class="ai-model-risk">' + risk + '</div>' if risk else ''}
                </div>"""

        detail_html += f"""<div class="ai-detail-block">
          <div class="ai-ticker-header">
            <span class="ai-ticker-name">{ticker}</span>
            <span class="ai-ticker-price">${price}</span>
          </div>
          <div class="ai-models-grid">
            {model_col("claude","Claude Opus 4.7","claude")}
            {model_col("gpt","GPT-5.5","gpt")}
            {model_col("deepseek","DeepSeek V4 Pro","deepseek")}
          </div>
          <div class="judge-grid">
            {model_col("opus_judge","Opus 裁判（趋势+风控）","opus_judge",True)}
            {model_col("gpt_judge","GPT 裁判（量化+概率）","gpt_judge",True)}
          </div>
        </div>"""
        detail_html += '<hr class="divider">'

    return f"""<div class="ai-wrap">
      <div class="section-header">AI 多模型分析</div>
      {matrix_html}
      <div style="font-size:10px;color:#3a4a5a;margin-bottom:14px;font-style:italic;">
        ↓ 各标的详细分析理由
      </div>
      {detail_html}
    </div>"""


def build_stock_section(result, cid, ai_data=None):
    """逐股详情：一行摘要 + 图表 + 紧凑数据表，无AI模块"""
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
    bi  = r4.get("breakout_info") or {}

    # 一行结论摘要
    summary_parts = [
        f'<span class="{tc(r2["conclusion"])}">{r2["conclusion"]}</span>',
        f'<span class="{tc(r3["conclusion"])}">{r3["conclusion"]}</span>',
        f'<span class="{tc(r4["type"])}">{r4["type"]}</span>',
        f'<span>RSI {r8["rsi_val"]}</span>',
        f'<span class="{tc(r7["conclusion"])}">{r7["conclusion"]}</span>',
        f'<span class="{"bull" if r11["rr_pass"] else "bear"}">{r11["conclusion"][:12]}</span>',
    ]
    summary_line = ' · '.join(summary_parts)

    # 突破信息行
    breakout_line = ""
    if bi:
        breakout_line = f"""<div style="font-size:10px;color:#5a7090;margin-bottom:10px;padding:4px 8px;border-left:2px solid #2a4a6a;">
          突破 {bi.get('struct_type','')} · 评分 {bi.get('score','?')}/5 · {'历史新高区域' if bi.get('is_all_time_area') else '近期前高'} · 目标法：{r11['target_method']}
        </div>"""

    # 数据表：分组展示
    def row(k1, v1, cls1, k2, v2, cls2, k3="", v3="", cls3="", k4="", v4="", cls4=""):
        def cell(k, v, c):
            if not k: return "<td></td><td></td>"
            return f'<td class="data-key">{k}</td><td class="data-val {c}">{v}</td>'
        return f"<tr>{cell(k1,v1,cls1)}{cell(k2,v2,cls2)}{cell(k3,v3,cls3)}{cell(k4,v4,cls4)}</tr>"

    rs_vs = f"vs {r6['index_name']}: {r6['vs_index']}" if not r6.get('is_benchmark') else r6['vs_index']
    rs_sec = f"vs {r6['sector_name']}: {r6['vs_sector']}" if not r6.get('is_benchmark') else r6['vs_sector']

    data_html = f"""
    <div class="data-section">
      <div class="data-section-title">趋势 · 结构</div>
      <table class="data-table">
        {row("MA200", f"${r2['ma200']} {r2['slope']}", tc(r2['conclusion']),
             "MA60",  f"${r3['ma60']} {r3['slope60']}", "",
             "MA20",  f"${r3['ma20']} {r3['slope20']}", "",
             "偏离MA200", f"{r2['deviation']}%", 'bull' if r2['deviation']>0 else 'bear')}
        {row("长期趋势", r2['conclusion'], tc(r2['conclusion']),
             "中期趋势", r3['conclusion'], tc(r3['conclusion']),
             "价格结构", r4['type'][:10], tc(r4['type']),
             "结构结论", r4['conclusion'][:8], "")}
      </table>
    </div>
    <div class="data-section">
      <div class="data-section-title">关键位置</div>
      <table class="data-table">
        {row("阻力", f"${r5['resistance']}", "bear",
             "确认位", f"${r5['confirm']}", "",
             "支撑", f"${r5['support']}", "bull",
             "失效位", f"${r5['invalidation']}", "warn")}
      </table>
    </div>
    <div class="data-section">
      <div class="data-section-title">动量 · 量价 · 波动率</div>
      <table class="data-table">
        {row("RSI(14)", r8['rsi'], "",
             "MACD", r8['macd'][:14], "",
             "量价比", str(r7['ratio']), tc(r7['conclusion']),
             "ATR", f"${r9['atr']} ({r9['atr_pct']}%)", "")}
        {row("动量结论", r8['conclusion'], tc(r8['conclusion']),
             "量价结论", r7['conclusion'][:8], tc(r7['conclusion']),
             "波动率", r9['vol_state'][:8], "",
             "布林带宽", str(r9['bw_val']), "")}
      </table>
    </div>
    <div class="data-section">
      <div class="data-section-title">相对强弱</div>
      <table class="data-table">
        {row("大盘参照", rs_vs[:20], "",
             "行业参照", rs_sec[:20], "",
             "结论", r6['conclusion'][:10], tc(r6['conclusion']),
             "", "", "")}
      </table>
    </div>
    <div class="data-section">
      <div class="data-section-title">风险赔率 · 交易类型</div>
      <table class="data-table">
        {row("入场参考", f"${r11['entry']}", "",
             "短线止损", f"${r11['short_stop']}", "warn",
             "中期止损", f"${r11['mid_stop']}", "warn",
             "结构止损", f"${r11['structure_stop']}", "bear")}
        {row("目标一", f"${r11['target1']} ({r11['t1_rr']}:1){'⚠️' if r11['t1_invalid'] else ''}", 'warn' if r11['t1_invalid'] else 'bull',
             "目标二", f"${r11['target2']} ({r11['t2_rr']}:1)", "bull",
             "赔率结论", r11['conclusion'][:12], 'bull' if r11['rr_pass'] else 'bear',
             "交易类型", r10['type'][:8], tc(r10['suitable']))}
      </table>
    </div>
    <div class="data-section">
      <div class="data-section-title">事件风险</div>
      <table class="data-table">
        {row("检测结果", r12['event'][:20], "",
             "风险等级", r12['risk'], 'warn' if r12['risk']=='高' else '',
             "执行建议", r12['action'][:10], "",
             "", "", "")}
      </table>
      <div style="font-size:10px;color:#3a4a5a;margin-top:3px;">{r12['disclaimer']}</div>
    </div>"""

    return f"""<div class="stock-wrap">
      <div class="stock-header">
        <span class="stock-name">{t}</span>
        <span class="stock-price">${p}</span>
        <span class="stock-date">{d}</span>
      </div>
      <div class="stock-summary-line">{summary_line}</div>
      {breakout_line}
      <div class="chart-wrap">
        <img src="cid:{cid}" class="chart-img" alt="{t}"/>
      </div>
      {data_html}
    </div>"""


def build_cost_html(cost):
    if not cost: return ""
    total = cost.get("total_cost", 0)
    per   = cost.get("per_model", {})
    parts = " · ".join([f"{k.split('/')[-1]} ${v['cost']}" for k, v in per.items()])
    return f'<div style="font-size:10px;color:#3a4050;text-align:center;padding:8px;">API费用：{parts} · 合计 ${total}</div>'


def build_full_html(results, chart_paths, ai_results=None, cost_summary=None):
    date_str    = datetime.now().strftime("%Y-%m-%d")
    cid_map     = {}
    stocks_html = ""

    for r in results:
        if "error" in r:
            stocks_html += f'<div style="color:#ff5252;padding:10px;">{r["ticker"]} 数据获取失败</div>'
            continue
        ticker = r["ticker"]
        cid    = f"chart_{ticker.replace('-','_')}"
        cid_map[cid] = chart_paths.get(ticker, "")
        stocks_html += build_stock_section(r, cid, (ai_results or {}).get(ticker))
        stocks_html += '<hr class="divider">'

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">{STYLE}</head>
<body><div class="container">

  <div class="header">
    <div class="header-title">📈 股票技术分析日报</div>
    <div class="header-sub">{date_str} · 12项框架 · Claude Opus 4.7 / GPT-5.5 / DeepSeek V4 Pro</div>
  </div>

  {build_overview(results, ai_results)}
  <hr class="divider">
  {build_exec_summary(results, ai_results)}
  {build_ai_section(results, ai_results)}
  <hr class="divider">
  <div class="section-header">逐标的详情</div>
  {stocks_html}
  {build_cost_html(cost_summary)}
  <div class="footer">
    仅供参考，不构成投资建议 · 数据来源 Yahoo Finance · AI via OpenRouter
  </div>
</div></body></html>"""
    return html, cid_map


def send_email(results, chart_paths, gmail_user, gmail_password,
               to_addr=None, ai_results=None, cost_summary=None):
    if to_addr is None:
        to_addr = gmail_user

    html_content, cid_map = build_full_html(results, chart_paths, ai_results, cost_summary)
    date_str = datetime.now().strftime("%Y-%m-%d")

    msg = MIMEMultipart("related")
    msg["Subject"] = f"📈 股票技术分析日报 · {date_str}"
    msg["From"]    = gmail_user
    msg["To"]      = to_addr

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_content, "html", "utf-8"))
    msg.attach(alt)

    for cid, path in cid_map.items():
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                img = MIMEImage(f.read())
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=os.path.basename(path))
            msg.attach(img)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_addr, msg.as_string())
        print(f"✅ 邮件已发送至 {to_addr}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False
