"""
邮件发送模块 v3.0
设计原则：
- 单列布局，移动端友好
- 三色系统：绿(好)/红(坏)/黄(等待)/灰(辅助)
- 字号分级：18px结论 / 14px数据 / 12px说明 / 10px附注
- 大间距分隔，留白为王
- 字重对比 > 颜色对比
- 顶部"今日动作卡"指引行动
"""

import smtplib, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

# ── 浅色主题（邮件友好）─────────────────────────────────────
# 设计原则：白底黑字，三色用深饱和色，对比度全部≥7:1
GREEN  = "#0d8050"   # 深绿 - 多头/支持/买入
RED    = "#c43c3c"   # 深红 - 空头/警惕/不交易
YELLOW = "#b87100"   # 深橙 - 等待/观望/中性
TEXT_MAIN     = "#1a1a1a"  # 主文字（接近纯黑）
TEXT_BODY     = "#3a3a3a"  # 正文文字
TEXT_SUB      = "#666666"  # 辅助文字（标签、说明）
TEXT_MUTED    = "#999999"  # 次级辅助
BG            = "#ffffff"  # 主背景纯白
BG_CARD       = "#f7f8fa"  # 卡片浅灰底
BG_HIGHLIGHT  = "#fef8e7"  # 强调背景（淡黄）
BORDER        = "#e0e3e8"  # 浅边框
BORDER_STRONG = "#c8ccd4"  # 强边框

STYLE = f"""
<style>
* {{ box-sizing: border-box; -webkit-text-size-adjust: 100%; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
  background: {BG};
  color: {TEXT_BODY};
  margin: 0; padding: 0;
  font-size: 15px;
  line-height: 1.6;
}}
.container {{
  max-width: 680px;
  margin: 0 auto;
  padding: 20px 16px;
  background: {BG};
}}

/* ── 顶部 header ── */
.header {{
  padding: 16px 0 20px 0;
  border-bottom: 2px solid {BORDER_STRONG};
  margin-bottom: 24px;
}}
.header-title {{
  font-size: 22px;
  font-weight: 700;
  color: {TEXT_MAIN};
  margin-bottom: 4px;
}}
.header-sub {{
  font-size: 12px;
  color: {TEXT_SUB};
}}

/* ── 区块标题 ── */
.section-title {{
  font-size: 12px;
  font-weight: 700;
  color: {TEXT_SUB};
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 32px 0 14px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid {BORDER_STRONG};
}}

/* ── 今日动作卡 ── */
.action-card {{
  background: {BG_HIGHLIGHT};
  border: 1px solid {BORDER_STRONG};
  border-left: 4px solid {YELLOW};
  border-radius: 4px;
  padding: 16px;
  margin-bottom: 24px;
}}
.action-card-title {{
  font-size: 14px;
  font-weight: 700;
  color: {TEXT_MAIN};
  margin-bottom: 12px;
}}
.action-card-title .count {{
  color: {YELLOW};
  font-weight: 700;
  margin-left: 6px;
}}
.action-item {{
  padding: 12px 0;
  border-bottom: 1px solid {BORDER};
}}
.action-item:last-child {{ border-bottom: none; }}
.action-ticker-line {{
  font-size: 17px;
  font-weight: 700;
  color: {TEXT_MAIN};
  margin-bottom: 6px;
}}
.action-ticker-line .price {{
  color: {TEXT_SUB};
  font-weight: 500;
  font-size: 14px;
  margin-left: 8px;
}}
.action-change {{
  font-size: 14px;
  color: {TEXT_BODY};
  line-height: 1.7;
  margin: 3px 0;
}}
.action-change.priority-0 {{ color: {RED}; font-weight: 600; }}
.action-no-action {{
  font-size: 13px;
  color: {TEXT_SUB};
  padding-top: 12px;
  margin-top: 4px;
  border-top: 1px solid {BORDER};
}}
.action-no-action .label {{ color: {GREEN}; font-weight: 700; }}

/* ── 总览表 ── */
.overview-wrap {{ margin-bottom: 24px; }}
.overview-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}}
.overview-table th {{
  font-size: 11px;
  font-weight: 700;
  color: {TEXT_SUB};
  text-transform: uppercase;
  letter-spacing: 1px;
  text-align: left;
  padding: 10px 6px;
  border-bottom: 2px solid {BORDER_STRONG};
  background: {BG_CARD};
}}
.overview-table td {{
  padding: 12px 6px;
  border-bottom: 1px solid {BORDER};
  vertical-align: middle;
}}
.ov-ticker {{ font-weight: 700; color: {TEXT_MAIN}; font-size: 14px; }}
.ov-price  {{ color: {TEXT_MAIN}; font-weight: 700; }}

/* ── 标签 tag ── */
.tag {{
  display: inline-block;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
  border-radius: 3px;
  white-space: nowrap;
}}
.tag-bull {{ background: #e6f4ed; color: {GREEN}; border: 1px solid #b3dcc7; }}
.tag-bear {{ background: #fae5e5; color: {RED};   border: 1px solid #ebb3b3; }}
.tag-wait {{ background: #fdf0d4; color: {YELLOW}; border: 1px solid #e8c98a; }}
.tag-hold {{ background: #e8eaed; color: {TEXT_BODY}; border: 1px solid #c8ccd4; }}
.tag-na   {{ background: #f0f1f3; color: {TEXT_MUTED}; border: 1px solid {BORDER}; }}

/* 颜色 */
.green  {{ color: {GREEN} !important; }}
.red    {{ color: {RED} !important; }}
.yellow {{ color: {YELLOW} !important; }}
.gray   {{ color: {TEXT_SUB} !important; }}
.bold   {{ font-weight: 700; }}

/* ── AI区块 ── */
.ai-matrix {{
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  margin-bottom: 32px;
}}
.ai-matrix th {{
  font-size: 11px;
  font-weight: 700;
  color: {TEXT_SUB};
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 10px 5px;
  text-align: center;
  background: {BG_CARD};
  border-bottom: 2px solid {BORDER_STRONG};
}}
.ai-matrix th:first-child {{ text-align: left; }}
.ai-matrix td {{
  padding: 10px 5px;
  border-bottom: 1px solid {BORDER};
  text-align: center;
}}
.ai-matrix td:first-child {{ text-align: left; }}

/* ── AI详细理由 ── */
.ai-detail {{
  margin-bottom: 28px;
}}
.ai-detail-header {{
  font-size: 18px;
  font-weight: 700;
  color: {TEXT_MAIN};
  padding: 8px 0 12px 0;
  border-bottom: 2px solid {BORDER_STRONG};
  margin-bottom: 14px;
}}
.ai-detail-header .price {{
  color: {TEXT_SUB};
  font-weight: 500;
  font-size: 14px;
  margin-left: 8px;
}}
.ai-model-block {{
  margin-bottom: 16px;
  padding: 10px 12px;
  background: {BG_CARD};
  border-left: 3px solid {BORDER_STRONG};
  border-radius: 2px;
}}
.ai-model-block.judge {{
  border-left-color: {YELLOW};
}}
.ai-model-name {{
  font-size: 11px;
  font-weight: 700;
  color: {TEXT_SUB};
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 4px;
}}
.ai-model-decision {{
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 6px;
  color: {TEXT_MAIN};
}}
.ai-model-decision .conf {{
  color: {TEXT_SUB};
  font-size: 12px;
  font-weight: 500;
  margin-left: 8px;
}}
.ai-model-body {{
  font-size: 13px;
  color: {TEXT_BODY};
  line-height: 1.7;
  margin-bottom: 6px;
}}
.ai-trigger {{
  font-size: 13px;
  color: {GREEN};
  font-weight: 600;
  margin: 4px 0;
  padding-left: 16px;
  position: relative;
}}
.ai-trigger::before {{
  content: "▸";
  position: absolute;
  left: 0;
  color: {GREEN};
}}
.ai-risk {{
  font-size: 13px;
  color: {RED};
  font-weight: 600;
  margin: 4px 0;
  padding-left: 16px;
  position: relative;
}}
.ai-risk::before {{
  content: "⚠";
  position: absolute;
  left: 0;
}}
.judge-meta {{
  font-size: 12px;
  color: {TEXT_BODY};
  margin: 4px 0;
}}
.judge-meta .label {{
  font-weight: 700;
  color: {TEXT_MAIN};
}}
.judge-tag {{
  display: inline-block;
  padding: 2px 7px;
  font-size: 10px;
  background: #ffffff;
  border: 1px solid {BORDER_STRONG};
  color: {TEXT_SUB};
  border-radius: 2px;
  margin-left: 6px;
  vertical-align: middle;
  font-weight: 600;
}}

/* ── 逐股详情 ── */
.stock-block {{
  margin-bottom: 40px;
  padding-bottom: 16px;
}}
.stock-header {{
  padding: 12px 0;
  border-bottom: 3px solid {TEXT_MAIN};
  margin-bottom: 16px;
}}
.stock-name {{
  font-size: 24px;
  font-weight: 700;
  color: {TEXT_MAIN};
}}
.stock-price {{
  font-size: 20px;
  color: {TEXT_MAIN};
  font-weight: 700;
  margin-left: 12px;
}}
.stock-date {{
  font-size: 12px;
  color: {TEXT_SUB};
  margin-left: 8px;
}}

/* 一行结论 */
.stock-summary {{
  font-size: 14px;
  color: {TEXT_BODY};
  margin-bottom: 16px;
  line-height: 1.9;
  padding: 10px 12px;
  background: {BG_CARD};
  border-radius: 3px;
}}
.stock-summary span {{ margin-right: 12px; }}

/* 图表 */
.chart-wrap {{ margin-bottom: 16px; }}
.chart-img {{
  width: 100%;
  display: block;
  border: 1px solid {BORDER_STRONG};
  border-radius: 3px;
}}

/* 数据组 */
.data-group {{
  margin-bottom: 18px;
}}
.data-group-title {{
  font-size: 11px;
  font-weight: 700;
  color: {TEXT_MAIN};
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid {BORDER};
}}
.data-row {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 8px 0;
  border-bottom: 1px solid {BORDER};
  font-size: 14px;
}}
.data-row:last-child {{ border-bottom: none; }}
.data-row .key {{
  color: {TEXT_SUB};
  font-size: 13px;
}}
.data-row .val {{
  color: {TEXT_MAIN};
  font-weight: 500;
  text-align: right;
  font-size: 14px;
}}
.data-row .val.bold {{ font-weight: 700; }}

/* 事件提示 */
.event-note {{
  font-size: 11px;
  color: {TEXT_SUB};
  margin-top: 8px;
  font-style: italic;
  padding: 6px 8px;
  background: {BG_CARD};
  border-radius: 2px;
}}

/* footer */
.footer {{
  font-size: 11px;
  color: {TEXT_SUB};
  text-align: center;
  padding: 24px 0 8px 0;
  border-top: 1px solid {BORDER_STRONG};
  margin-top: 32px;
  line-height: 1.7;
}}

/* 响应式 - 移动端进一步优化 */
@media (max-width: 600px) {{
  body {{ font-size: 14px; }}
  .container {{ padding: 16px 12px; }}
  .stock-name {{ font-size: 22px; }}
  .stock-price {{ font-size: 18px; }}
  .overview-table {{ font-size: 12px; }}
  .overview-table th, .overview-table td {{ padding: 8px 4px; }}
  .ai-matrix {{ font-size: 11px; }}
  .ai-matrix th, .ai-matrix td {{ padding: 8px 3px; }}
}}

@media (prefers-color-scheme: dark) {{
  /* 强制使用浅色主题，避免深色模式渲染异常 */
  body, .container {{ background: {BG} !important; color: {TEXT_BODY} !important; }}
}}
</style>
"""


# ── 工具函数 ─────────────────────────────────────────────────

def color_class(text, context="trend"):
    """三色系统：根据语义返回颜色class"""
    if not text: return "gray"
    if any(k in text for k in ["多头","支持","确认","放量","买入","合格","上升","试多","建议"]):
        return "green"
    if any(k in text for k in ["空头","警惕","破坏","弱","假突破","不支持","不交易","不合格","下降"]):
        return "red"
    if any(k in text for k in ["观望","等待","暂不","存疑","冲突","调整","不足","需"]):
        return "yellow"
    return "gray"


def make_tag(decision):
    if not decision or decision == "N/A":
        return '<span class="tag tag-na">—</span>'
    if "买入" in decision or "试多" in decision:
        return f'<span class="tag tag-bull">{decision}</span>'
    if "持有" in decision:
        return f'<span class="tag tag-hold">{decision}</span>'
    if "等待" in decision:
        return f'<span class="tag tag-wait">{decision}</span>'
    if "不交易" in decision:
        return f'<span class="tag tag-bear">{decision}</span>'
    return f'<span class="tag tag-na">{decision}</span>'


def get_decisions(ai_data):
    if not ai_data:
        return {k: "" for k in ["claude","gpt","deepseek","opus_judge","gpt_judge"]}
    def _d(m, key="decision"):
        r = ai_data.get(m, {}) or {}
        if r.get("error"): return ""
        return r.get(key, "")
    return {
        "claude":     _d("claude"),
        "gpt":        _d("gpt"),
        "deepseek":   _d("deepseek"),
        "opus_judge": _d("opus_judge", "final_decision"),
        "gpt_judge":  _d("gpt_judge",  "final_decision"),
    }


# ── 今日动作卡 ────────────────────────────────────────────────

def build_action_card(today_snapshot, changes, no_action_tickers, ai_results=None):
    """构建顶部"今日动作"卡片"""

    # 没有变化的特殊情况
    if not changes and not today_snapshot:
        return ""

    items_html = ""
    if changes:
        for ticker, change_list in changes.items():
            snap = today_snapshot.get(ticker, {})
            ai   = (ai_results or {}).get(ticker, {})
            d    = get_decisions(ai)
            decision = d["opus_judge"] or d["gpt_judge"] or "—"

            change_lines = "".join([
                f'<div class="action-change priority-{c["priority"]}">{c["msg"]}</div>'
                for c in change_list[:3]  # 最多显示3条
            ])

            items_html += f'''<div class="action-item">
              <div class="action-ticker-line">{ticker} <span class="price">${snap.get("price","?")}</span> {make_tag(decision)}</div>
              {change_lines}
            </div>'''

    no_action_html = ""
    if no_action_tickers:
        no_action_html = f'''<div class="action-no-action">
          <span class="label">✓ 无需操作（{len(no_action_tickers)}只）</span>
          <span style="color:{TEXT_SUB};margin-left:8px;">{' · '.join(no_action_tickers)}</span>
        </div>'''

    if not items_html and not no_action_html:
        return ""

    title = f"📍 今日重点关注"
    count = f'<span class="count">{len(changes)}/{len(today_snapshot)}</span>' if today_snapshot else ""

    if not changes:
        title = "✓ 今日无明显变化"
        count = ""
        items_html = f'<div style="font-size:13px;color:{TEXT_SUB};padding:8px 0;">所有标的状态稳定，无需特别关注</div>'

    return f'''<div class="action-card">
      <div class="action-card-title">{title}{count}</div>
      {items_html}
      {no_action_html}
    </div>'''


# ── 总览表 ────────────────────────────────────────────────────

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
        d      = get_decisions(ai)
        fd     = d["opus_judge"] or d["gpt_judge"] or ""

        rows += f"""<tr>
          <td><span class="ov-ticker">{ticker}</span></td>
          <td class="ov-price">${r['price']}</td>
          <td class="{color_class(r2['conclusion'])}">{r2['conclusion'][:6]}</td>
          <td class="red">${lv['resistance']}</td>
          <td class="green">${lv['support']}</td>
          <td>{make_tag(fd)}</td>
        </tr>"""

    return f"""<div class="overview-wrap">
      <div class="section-title">市场总览</div>
      <table class="overview-table">
        <thead><tr>
          <th>标的</th><th>现价</th><th>趋势</th>
          <th>阻力</th><th>支撑</th><th>AI建议</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""


# ── AI区块 ────────────────────────────────────────────────────

def build_ai_section(results, ai_results=None):
    if not ai_results:
        return ""

    # ── 横向对比表 ──
    matrix_rows = ""
    for r in results:
        if "error" in r: continue
        ticker = r["ticker"]
        ai     = ai_results.get(ticker, {})
        d      = get_decisions(ai)

        matrix_rows += f"""<tr>
          <td><span class="bold" style="color:#ffffff;">{ticker}</span> <span class="gray" style="font-size:10px;">${r['price']}</span></td>
          <td>{make_tag(d['claude'])}</td>
          <td>{make_tag(d['gpt'])}</td>
          <td>{make_tag(d['deepseek'])}</td>
          <td>{make_tag(d['opus_judge'])}</td>
          <td>{make_tag(d['gpt_judge'])}</td>
        </tr>"""

    matrix_html = f"""<table class="ai-matrix">
      <thead><tr>
        <th>标的</th>
        <th>Claude</th><th>GPT</th><th>DeepSeek</th>
        <th>Opus 裁判</th><th>GPT 裁判</th>
      </tr></thead>
      <tbody>{matrix_rows}</tbody>
    </table>"""

    # ── 逐股详细理由 ──
    detail_html = ""
    for r in results:
        if "error" in r: continue
        ticker = r["ticker"]
        ai     = ai_results.get(ticker, {})
        if not ai:
            continue

        def model_block(label, key, is_judge=False):
            raw = ai.get(key, {}) or {}
            css_class = "judge" if is_judge else ""

            if not raw or raw.get("error"):
                return f'''<div class="ai-model-block {css_class}">
                  <div class="ai-model-name">{label}</div>
                  <div class="gray" style="font-size:12px;">调用失败</div>
                </div>'''

            if is_judge:
                dec  = raw.get("final_decision","N/A")
                body = raw.get("final_reason","")
                trig = raw.get("final_trigger","")
                conf = raw.get("final_confidence","")
                cons = raw.get("consensus","")
                divg = raw.get("divergence","")
                agr  = raw.get("model_agreement","")

                meta = ""
                if cons:
                    meta += f'<div class="judge-meta"><span class="label">共识：</span>{cons}</div>'
                if divg:
                    meta += f'<div class="judge-meta"><span class="label">分歧：</span>{divg}</div>'

                return f'''<div class="ai-model-block judge">
                  <div class="ai-model-name">{label}</div>
                  <div class="ai-model-decision {color_class(dec)}">{dec}<span class="judge-tag">{agr}</span><span class="conf">置信 {conf}</span></div>
                  {meta}
                  <div class="ai-model-body">{body}</div>
                  {f'<div class="ai-trigger">{trig}</div>' if trig else ''}
                </div>'''
            else:
                dec  = raw.get("decision","N/A")
                body = raw.get("reason","")
                trig = raw.get("trigger","")
                risk = raw.get("key_risk","")
                conf = raw.get("confidence","")

                return f'''<div class="ai-model-block">
                  <div class="ai-model-name">{label}</div>
                  <div class="ai-model-decision {color_class(dec)}">{dec}<span class="conf">置信 {conf}</span></div>
                  <div class="ai-model-body">{body}</div>
                  {f'<div class="ai-trigger">{trig}</div>' if trig else ''}
                  {f'<div class="ai-risk">{risk}</div>' if risk else ''}
                </div>'''

        detail_html += f'''<div class="ai-detail">
          <div class="ai-detail-header">{ticker}<span class="price">${r['price']}</span></div>
          {model_block("Claude Opus 4.7", "claude")}
          {model_block("GPT-5.5", "gpt")}
          {model_block("DeepSeek V4 Pro", "deepseek")}
          {model_block("Opus 裁判（趋势+风控）", "opus_judge", True)}
          {model_block("GPT 裁判（量化+概率）", "gpt_judge", True)}
        </div>'''

    return f'''<div class="section-title">AI 多模型分析</div>
      {matrix_html}
      {detail_html}'''


# ── 单股详情 ─────────────────────────────────────────────────

def data_row(key, val, val_class="", bold=False):
    bold_class = " bold" if bold else ""
    return f'<div class="data-row"><span class="key">{key}</span><span class="val {val_class}{bold_class}">{val}</span></div>'


def build_stock_section(result, cid):
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

    # 一行结论
    summary_parts = [
        f'<span class="{color_class(r2["conclusion"])} bold">{r2["conclusion"]}</span>',
        f'<span class="{color_class(r3["conclusion"])}">{r3["conclusion"]}</span>',
        f'<span class="{color_class(r4["type"])}">{r4["type"]}</span>',
        f'<span class="gray">RSI {r8["rsi_val"]}</span>',
        f'<span class="{"green" if r11["rr_pass"] else "red"}">{"赔率合格" if r11["rr_pass"] else "赔率不足"}</span>',
    ]
    summary_line = ' · '.join(summary_parts)

    # 突破信息
    breakout_html = ""
    if bi:
        breakout_html = f'''<div class="data-group">
          <div class="data-group-title">突破分析</div>
          {data_row("结构状态", bi.get("struct_type",""), color_class(bi.get("struct_type","")), bold=True)}
          {data_row("质量评分", f"{bi.get('score','?')}/5")}
          {data_row("位置", "历史新高区域" if bi.get("is_all_time_area") else "近期前高")}
          {data_row("突破幅度", f"${bi.get('breakout_amp','?')}（阈值 ${round(bi.get('atr_val',0)*0.5,2)}）")}
        </div>'''

    rs_main = r6['vs_index'] if not r6.get('is_benchmark') else "基准资产"

    return f"""<div class="stock-block">
      <div class="stock-header">
        <span class="stock-name">{t}</span>
        <span class="stock-price">${p}</span>
        <span class="stock-date">{d}</span>
      </div>
      <div class="stock-summary">{summary_line}</div>
      <div class="chart-wrap">
        <img src="cid:{cid}" class="chart-img" alt="{t}"/>
      </div>

      <div class="data-group">
        <div class="data-group-title">趋势</div>
        {data_row("长期趋势", r2['conclusion'], color_class(r2['conclusion']), bold=True)}
        {data_row("中期趋势", r3['conclusion'], color_class(r3['conclusion']))}
        {data_row("MA200", f"${r2['ma200']}（{r2['slope']}）")}
        {data_row("MA60",  f"${r3['ma60']}（{r3['slope60']}）")}
        {data_row("MA20",  f"${r3['ma20']}（{r3['slope20']}）")}
        {data_row("偏离MA200", f"{r2['deviation']}%", "green" if r2['deviation']>0 else "red")}
      </div>

      <div class="data-group">
        <div class="data-group-title">价格结构</div>
        {data_row("结构类型", r4['type'], color_class(r4['type']), bold=True)}
        {data_row("结论", r4['conclusion'])}
        {data_row("近期高点", " → ".join([f"${v}" for _,v in r4["highs"][-3:]]))}
        {data_row("近期低点", " → ".join([f"${v}" for _,v in r4["lows"][-3:]]))}
      </div>

      <div class="data-group">
        <div class="data-group-title">关键位置</div>
        {data_row("阻力位", f"${r5['resistance']}", "red", bold=True)}
        {data_row("确认位", f"${r5['confirm']}")}
        {data_row("支撑位", f"${r5['support']}", "green", bold=True)}
        {data_row("失效位", f"${r5['invalidation']}", "yellow")}
      </div>

      {breakout_html}

      <div class="data-group">
        <div class="data-group-title">动量 · 量价 · 波动率</div>
        {data_row("RSI(14)", r8['rsi'])}
        {data_row("MACD", r8['macd'])}
        {data_row("MACD柱", r8['histogram'])}
        {data_row("量价比", f"{r7['ratio']}（{r7['conclusion']}）", color_class(r7['conclusion']))}
        {data_row("ATR(14)", f"${r9['atr']}（{r9['atr_pct']}%）")}
        {data_row("波动率状态", r9['vol_state'])}
      </div>

      <div class="data-group">
        <div class="data-group-title">相对强弱</div>
        {data_row(f"vs {r6['index_name']}", r6['vs_index'])}
        {data_row(f"vs {r6['sector_name']}", r6['vs_sector'])}
        {data_row("结论", r6['conclusion'], color_class(r6['conclusion']))}
      </div>

      <div class="data-group">
        <div class="data-group-title">交易类型 · 风险赔率</div>
        {data_row("交易类型", r10['type'], color_class(r10['suitable']), bold=True)}
        {data_row("是否适合", r10['suitable'], color_class(r10['suitable']))}
        {data_row("入场参考", f"${r11['entry']}", bold=True)}
        {data_row("短线止损", f"${r11['short_stop']}", "yellow")}
        {data_row("中期止损", f"${r11['mid_stop']}", "yellow")}
        {data_row("结构止损", f"${r11['structure_stop']}", "red")}
        {data_row("目标一", f"${r11['target1']}（{r11['t1_rr']}:1）{'⚠️无效' if r11['t1_invalid'] else ''}", "yellow" if r11['t1_invalid'] else "green")}
        {data_row("目标二", f"${r11['target2']}（{r11['t2_rr']}:1）", "green")}
        {data_row("目标方法", r11['target_method'])}
        {data_row("赔率结论", r11['conclusion'], "green" if r11['rr_pass'] else "red", bold=True)}
      </div>

      <div class="data-group">
        <div class="data-group-title">事件风险</div>
        {data_row("检测结果", r12['event'])}
        {data_row("风险等级", r12['risk'], "yellow" if r12['risk']=='高' else "gray")}
        {data_row("执行建议", r12['action'])}
        <div class="event-note">{r12['disclaimer']}</div>
      </div>
    </div>"""


# ── 费用 ────────────────────────────────────────────────────

def build_cost_html(cost):
    if not cost: return ""
    total = cost.get("total_cost", 0)
    per   = cost.get("per_model", {})
    parts = " · ".join([f"{k.split('/')[-1]} ${v['cost']}" for k, v in per.items()])
    return f'<div style="font-size:10px;color:{TEXT_SUB};text-align:center;padding:12px;">API 费用：{parts} · 合计 ${total}</div>'


# ── 完整HTML ──────────────────────────────────────────────────

def build_full_html(results, chart_paths, ai_results=None, cost_summary=None,
                    today_snapshot=None, changes=None, no_action_tickers=None):
    date_str = datetime.now().strftime("%Y-%m-%d")
    cid_map  = {}

    # 顶部今日动作卡
    action_card = ""
    if today_snapshot is not None:
        action_card = build_action_card(today_snapshot, changes or {}, no_action_tickers or [], ai_results)

    # 逐股详情
    stocks_html = ""
    for r in results:
        if "error" in r:
            stocks_html += f'<div style="color:{RED};padding:10px;">{r["ticker"]} 数据获取失败</div>'
            continue
        ticker = r["ticker"]
        cid    = f"chart_{ticker.replace('-','_')}"
        cid_map[cid] = chart_paths.get(ticker, "")
        stocks_html += build_stock_section(r, cid)

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{STYLE}
</head>
<body><div class="container">

  <div class="header">
    <div class="header-title">📈 股票技术分析日报</div>
    <div class="header-sub">{date_str} · 12项框架 · Opus 4.7 / GPT-5.5 / DeepSeek V4 Pro</div>
  </div>

  {action_card}

  {build_overview(results, ai_results)}

  {build_ai_section(results, ai_results)}

  <div class="section-title">逐标的详情</div>
  {stocks_html}

  {build_cost_html(cost_summary)}
  <div class="footer">
    仅供参考，不构成投资建议<br>
    数据来源 Yahoo Finance · AI via OpenRouter
  </div>
</div></body></html>"""
    return html, cid_map


# ── 发送 ────────────────────────────────────────────────────

def send_email(results, chart_paths, gmail_user, gmail_password,
               to_addr=None, ai_results=None, cost_summary=None,
               today_snapshot=None, changes=None, no_action_tickers=None):
    if to_addr is None:
        to_addr = gmail_user

    html_content, cid_map = build_full_html(
        results, chart_paths, ai_results, cost_summary,
        today_snapshot, changes, no_action_tickers
    )
    date_str = datetime.now().strftime("%Y-%m-%d")

    # 邮件标题：如有重要变化，标题加提示
    subject_extra = ""
    if changes:
        subject_extra = f" · {len(changes)}个关注"

    msg = MIMEMultipart("related")
    msg["Subject"] = f"📈 股票分析日报 · {date_str}{subject_extra}"
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
