"""
邮件发送模块 v2
生成HTML格式分析报告（含AI综合解读），通过Gmail SMTP发送
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime


STYLE = """
<style>
  body { font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
         background: #0f0f1a; color: #e0e0e0; margin: 0; padding: 20px; }
  .container { max-width: 900px; margin: 0 auto; }
  .header { background: linear-gradient(135deg, #1a1a3e, #2a2a5e);
            padding: 20px 30px; border-radius: 12px; margin-bottom: 20px;
            border: 1px solid #3a3a6e; }
  .header h1 { margin: 0; font-size: 22px; color: #7986cb; }
  .header .date { color: #9e9e9e; font-size: 13px; margin-top: 5px; }

  .summary-box { background: #1a1a3e; border: 1px solid #3a3a6e;
                 border-radius: 10px; padding: 16px 20px; margin-bottom: 20px; }
  .summary-box h2 { margin: 0 0 12px 0; font-size: 15px; color: #7986cb; }
  .summary-row { display: flex; gap: 10px; flex-wrap: wrap; }
  .summary-tag { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
  .tag-bull  { background: #1b5e20; color: #69f0ae; border: 1px solid #2e7d32; }
  .tag-bear  { background: #b71c1c; color: #ff8a80; border: 1px solid #c62828; }
  .tag-wait  { background: #e65100; color: #ffcc80; border: 1px solid #f57c00; }
  .tag-watch { background: #1a237e; color: #82b1ff; border: 1px solid #283593; }

  .stock-card { background: #1a1a2e; border: 1px solid #2a2a4e;
                border-radius: 12px; margin-bottom: 24px; overflow: hidden; }
  .card-header { background: #16213e; padding: 14px 20px;
                 display: flex; justify-content: space-between; align-items: center; }
  .card-header .ticker { font-size: 20px; font-weight: bold; color: #e0e0e0; }
  .card-header .price  { font-size: 18px; color: #7986cb; }
  .card-body { padding: 16px 20px; }
  .chart-img { width: 100%; border-radius: 8px; margin-bottom: 16px; }

  .section { margin-bottom: 14px; }
  .section-title { font-size: 12px; color: #7986cb; text-transform: uppercase;
                   letter-spacing: 1px; margin-bottom: 6px;
                   border-bottom: 1px solid #2a2a4e; padding-bottom: 4px; }
  .kv-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px,1fr)); gap: 6px; }
  .kv { background: #0f0f1a; padding: 7px 10px; border-radius: 6px;
        border-left: 3px solid #3a3a6e; }
  .kv .k { font-size: 10px; color: #9e9e9e; margin-bottom: 2px; }
  .kv .v { font-size: 13px; color: #e0e0e0; font-weight: 500; }

  .bull    { color: #69f0ae !important; }
  .bear    { color: #ff5252 !important; }
  .warn    { color: #ffab40 !important; }
  .neutral { color: #82b1ff !important; }

  /* ── AI分析板块 ── */
  .ai-section { background: #0d1f2d; border: 1px solid #1a4060;
                border-radius: 10px; margin: 16px 0; padding: 16px 20px; }
  .ai-section-title { font-size: 12px; color: #4fc3f7; text-transform: uppercase;
                      letter-spacing: 1px; margin-bottom: 12px;
                      border-bottom: 1px solid #1a4060; padding-bottom: 6px; }
  .ai-model-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px,1fr));
                  gap: 10px; margin-bottom: 12px; }
  .ai-model-card { background: #0a1929; border: 1px solid #1a3a5c;
                   border-radius: 8px; padding: 10px 14px; }
  .ai-model-name { font-size: 10px; color: #4fc3f7; margin-bottom: 6px;
                   text-transform: uppercase; letter-spacing: 0.5px; }
  .ai-decision { font-size: 14px; font-weight: bold; margin-bottom: 4px; }
  .ai-reason { font-size: 11px; color: #b0bec5; line-height: 1.5; }
  .ai-risk   { font-size: 11px; color: #ff8a80; margin-top: 4px; }
  .ai-confidence { font-size: 10px; color: #78909c; margin-top: 4px; }
  .ai-judge { background: #1a2744; border: 1px solid #3a5a9e;
              border-radius: 8px; padding: 12px 16px; margin-top: 10px; }
  .ai-judge-title { font-size: 11px; color: #7986cb; margin-bottom: 8px;
                    text-transform: uppercase; letter-spacing: 0.5px; }
  .ai-consensus  { font-size: 12px; color: #a5d6a7; margin-bottom: 6px; }
  .ai-divergence { font-size: 12px; color: #ffcc80; margin-bottom: 8px; }
  .ai-final { font-size: 15px; font-weight: bold; margin-bottom: 4px; }
  .ai-final-reason { font-size: 12px; color: #b0bec5; line-height: 1.5; }
  .agree-tag { display: inline-block; padding: 2px 8px; border-radius: 10px;
               font-size: 10px; margin-left: 8px; vertical-align: middle; }
  .agree-high { background: #1b5e20; color: #69f0ae; }
  .agree-mid  { background: #1a237e; color: #82b1ff; }
  .agree-low  { background: #b71c1c; color: #ff8a80; }

  .cost-box { background: #0a1929; border: 1px solid #1a3a5c; border-radius: 8px;
              padding: 10px 16px; margin-top: 16px; font-size: 11px; color: #78909c; }
  .cost-box span { color: #4fc3f7; }

  .footer { text-align: center; color: #555577; font-size: 11px;
            padding: 16px; border-top: 1px solid #2a2a4e; margin-top: 20px; }
</style>
"""


def trend_color(text):
    if any(k in text for k in ["多头","支持","确认","放量","强"]):   return "bull"
    if any(k in text for k in ["空头","警惕","破坏","弱势","弱"]):   return "bear"
    if any(k in text for k in ["观望","等待","不支持","不适合"]):     return "warn"
    return "neutral"


def decision_color(d):
    if "买入" in d or "试多" in d: return "bull"
    if "不交易" in d or "观望" in d: return "bear"
    if "等待" in d or "持有" in d:  return "warn"
    return "neutral"


def agree_class(agreement):
    if "高度" in agreement: return "agree-high"
    if "明显" in agreement: return "agree-low"
    return "agree-mid"


def kv(key, value, color_class=""):
    vc = f' class="{color_class}"' if color_class else ""
    return f'<div class="kv"><div class="k">{key}</div><div class="v"{vc}>{value}</div></div>'


def build_ai_html(ticker, ai_data):
    """生成单只股票的AI分析HTML板块"""
    if not ai_data:
        return ""

    def model_card(name, r):
        if not r or r.get("error"):
            return f'''<div class="ai-model-card">
              <div class="ai-model-name">{name}</div>
              <div class="ai-reason warn">调用失败：{r.get("error","未知错误") if r else "无数据"}</div>
            </div>'''
        dc = decision_color(r.get("decision",""))
        return f'''<div class="ai-model-card">
          <div class="ai-model-name">{name}</div>
          <div class="ai-decision {dc}">{r.get("decision","N/A")}</div>
          <div class="ai-reason">{r.get("reason","")}</div>
          <div class="ai-risk">⚠️ {r.get("key_risk","")}</div>
          <div class="ai-confidence">置信度：{r.get("confidence","N/A")}</div>
        </div>'''

    judge = ai_data.get("judge", {})
    fd    = judge.get("final_decision", "N/A")
    fa    = judge.get("model_agreement", "")
    fdc   = decision_color(fd)
    ac    = agree_class(fa)

    judge_html = ""
    if judge and not judge.get("error"):
        judge_html = f'''<div class="ai-judge">
          <div class="ai-judge-title">⚖️ Opus 元分析裁判</div>
          <div class="ai-consensus">✅ 共识：{judge.get("consensus","")}</div>
          <div class="ai-divergence">🔀 分歧：{judge.get("divergence","")}</div>
          <div class="ai-final {fdc}">
            最终结论：{fd}
            <span class="agree-tag {ac}">{fa}</span>
          </div>
          <div class="ai-final-reason">{judge.get("final_reason","")}</div>
        </div>'''
    elif judge.get("error"):
        judge_html = f'<div class="ai-judge warn">元分析失败：{judge["error"]}</div>'

    return f'''<div class="ai-section">
      <div class="ai-section-title">🤖 AI 三模型综合分析</div>
      <div class="ai-model-row">
        {model_card("Claude Opus 4.7", ai_data.get("claude"))}
        {model_card("GPT-5.5", ai_data.get("gpt"))}
        {model_card("DeepSeek V4 Pro", ai_data.get("deepseek"))}
      </div>
      {judge_html}
    </div>'''


def build_stock_html(result, chart_cid, ai_data=None):
    t   = result["ticker"]
    p   = result["price"]
    d   = result["date"]
    r0  = result["0_cycle"]
    r1  = result["1_market"]
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

    ai_html = build_ai_html(t, ai_data)

    return f"""
    <div class="stock-card">
      <div class="card-header">
        <div><span class="ticker">{t}</span>
          <span style="margin-left:10px;font-size:12px;color:#9e9e9e;">{d}</span></div>
        <span class="price">${p}</span>
      </div>
      <div class="card-body">
        <img src="cid:{chart_cid}" class="chart-img" alt="{t} 技术分析图"/>

        {ai_html}

        <div class="section">
          <div class="section-title">0. 交易周期</div>
          <div class="kv-grid">
            {kv("周期", r0["cycle"])}
            {kv("结论", r0["conclusion"])}
          </div>
        </div>
        <div class="section">
          <div class="section-title">1. 市场/行业背景</div>
          <div class="kv-grid">
            {kv("市场背景", r1["market"], trend_color(r1["market"]))}
            {kv("参考行业ETF", r1["sector"])}
            {kv("综合结论", r1["conclusion"], trend_color(r1["conclusion"]))}
          </div>
        </div>
        <div class="section">
          <div class="section-title">2. 长期趋势</div>
          <div class="kv-grid">
            {kv("MA200", str(r2["ma200"]))}
            {kv("价格偏离MA200", f"{r2['deviation']}%", 'bull' if r2['deviation']>0 else 'bear')}
            {kv("MA200斜率", r2["slope"])}
            {kv("长期趋势", r2["conclusion"], trend_color(r2["conclusion"]))}
          </div>
        </div>
        <div class="section">
          <div class="section-title">3. 中期趋势</div>
          <div class="kv-grid">
            {kv("MA20", str(r3["ma20"]))}
            {kv("MA60", str(r3["ma60"]))}
            {kv("MA20方向", r3["slope20"])}
            {kv("MA60方向", r3["slope60"])}
            {kv("中期趋势", r3["conclusion"], trend_color(r3["conclusion"]))}
          </div>
        </div>
        <div class="section">
          <div class="section-title">4. 价格结构</div>
          <div class="kv-grid">
            {kv("结构类型", r4["type"])}
            {kv("结构结论", r4["conclusion"], trend_color(r4["conclusion"]))}
            {kv("近期高点", " → ".join([f"${v}" for _,v in r4["highs"][-3:]]))}
            {kv("近期低点", " → ".join([f"${v}" for _,v in r4["lows"][-3:]]))}
          </div>
        </div>
        <div class="section">
          <div class="section-title">5. 关键位置</div>
          <div class="kv-grid">
            {kv("最近阻力", f"${r5['resistance']}", 'bear')}
            {kv("关键确认位", f"${r5['confirm']}")}
            {kv("最近支撑", f"${r5['support']}", 'bull')}
            {kv("结构失效位", f"${r5['invalidation']}", 'warn')}
          </div>
        </div>
        <div class="section">
          <div class="section-title">6. 相对强弱</div>
          <div class="kv-grid">
            {kv(f"vs {r6['index_name']}", r6['vs_index'], trend_color(r6['vs_index']))}
            {kv(f"vs {r6['sector_name']}", r6['vs_sector'], trend_color(r6['vs_sector']))}
            {kv("相对强弱结论", r6["conclusion"], trend_color(r6["conclusion"]))}
          </div>
        </div>
        <div class="section">
          <div class="section-title">7. 量价确认</div>
          <div class="kv-grid">
            {kv("上涨日均量", f"{r7['up_vol']}M")}
            {kv("下跌日均量", f"{r7['down_vol']}M")}
            {kv("量价比", str(r7["ratio"]))}
            {kv("量价结论", r7["conclusion"], trend_color(r7["conclusion"]))}
          </div>
        </div>
        <div class="section">
          <div class="section-title">8. 动量状态</div>
          <div class="kv-grid">
            {kv("RSI(14)", r8["rsi"])}
            {kv("MACD状态", r8["macd"])}
            {kv("MACD柱状图", r8["histogram"])}
            {kv("动量结论", r8["conclusion"], trend_color(r8["conclusion"]))}
          </div>
        </div>
        <div class="section">
          <div class="section-title">9. 波动率状态</div>
          <div class="kv-grid">
            {kv("ATR(14)", str(r9["atr"]))}
            {kv("ATR/价格", f"{r9['atr_pct']}%")}
            {kv("布林带宽度", str(r9["bw_val"]))}
            {kv("波动率状态", r9["vol_state"])}
            {kv("仓位影响", r9["pos_impact"], 'warn' if r9['pos_impact']!='正常' else '')}
          </div>
        </div>
        <div class="section">
          <div class="section-title">10. 交易类型</div>
          <div class="kv-grid">
            {kv("交易类型", r10["type"])}
            {kv("是否适合", r10["suitable"], trend_color(r10["suitable"]))}
            {kv("是否等待确认", r10["wait"])}
          </div>
        </div>
        <div class="section">
          <div class="section-title">11. 风险与赔率（参考位 · 需人工确认）</div>
          <div class="kv-grid">
            {kv("当前价/参考入场", f"${r11['entry']}")}
            {kv("短线止损参考", f"${r11['short_stop']}", 'warn')}
            {kv("中期止损参考", f"${r11['mid_stop']}", 'warn')}
            {kv("结构止损参考", f"${r11['structure_stop']}", 'bear')}
            {kv("目标一参考", f"${r11['target1']}", 'bull')}
            {kv("目标二参考", f"${r11['target2']}", 'bull')}
          </div>
          <p style="font-size:11px;color:#ffab40;margin-top:8px;">⚠️ {r11['note']}</p>
        </div>
        <div class="section">
          <div class="section-title">12. 事件风险</div>
          <div class="kv-grid">
            {kv("未来事件", r12["event"])}
            {kv("事件风险", r12["risk"], 'warn' if r12['risk']=='高' else '')}
            {kv("执行方式", r12["action"])}
          </div>
        </div>
      </div>
    </div>"""


def build_summary_html(results, ai_results=None):
    """执行摘要：优先用AI最终结论，无AI则用技术分析结论"""
    tags = []
    for r in results:
        if "error" in r:
            continue
        ticker = r["ticker"]
        ai     = (ai_results or {}).get(ticker, {})
        judge  = ai.get("judge", {})
        fd     = judge.get("final_decision", "") if judge and not judge.get("error") else ""

        if fd:
            # 用AI结论
            if "买入" in fd:
                css, label = "tag-bull", f"✅ {ticker} AI建议买入"
            elif "试多" in fd:
                css, label = "tag-bull", f"🟢 {ticker} AI建议试多"
            elif "不交易" in fd:
                css, label = "tag-bear", f"🔴 {ticker} AI建议不交易"
            elif "等待" in fd:
                css, label = "tag-wait", f"⏳ {ticker} 等待确认"
            else:
                css, label = "tag-watch", f"👀 {ticker} 持有观望"
        else:
            # 降级到技术分析结论
            long_c = r["2_long_trend"]["conclusion"]
            trade  = r["10_trade"]["suitable"]
            if "适合" in trade and "多头" in long_c:
                css, label = "tag-bull", f"✅ {ticker} 可关注"
            elif "空头" in long_c:
                css, label = "tag-bear", f"🔴 {ticker} 趋势偏弱"
            elif "等待" in trade or "暂不" in trade:
                css, label = "tag-wait", f"⏳ {ticker} 等待确认"
            else:
                css, label = "tag-watch", f"👀 {ticker} 观望"

        tags.append(f'<span class="summary-tag {css}">{label}</span>')

    return f"""<div class="summary-box">
      <h2>📋 今日执行摘要</h2>
      <div class="summary-row">{''.join(tags)}</div>
    </div>"""


def build_cost_html(cost_summary):
    if not cost_summary:
        return ""
    total = cost_summary.get("total_cost", 0)
    per   = cost_summary.get("per_model", {})
    rows  = " | ".join([f"{k.split('/')[-1]}: <span>${v['cost']}</span>" for k, v in per.items()])
    return f'<div class="cost-box">今日API费用：{rows} | 合计：<span>${total}</span> / 预算上限：<span>$5/模型</span></div>'


def build_full_html(results, chart_paths, ai_results=None, cost_summary=None):
    date_str = datetime.now().strftime("%Y年%m月%d日")
    cid_map  = {}
    stocks_html = ""

    for r in results:
        if "error" in r:
            stocks_html += f'<div class="stock-card" style="padding:20px;color:#ff5252;">{r["ticker"]} 数据获取失败</div>'
            continue
        ticker   = r["ticker"]
        cid      = f"chart_{ticker.replace('-','_')}"
        cid_map[cid] = chart_paths.get(ticker, "")
        ai_data  = (ai_results or {}).get(ticker)
        stocks_html += build_stock_html(r, cid, ai_data)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">{STYLE}</head>
<body><div class="container">
  <div class="header">
    <h1>📈 股票技术分析日报 v2</h1>
    <div class="date">{date_str} · 12项框架 + AI三模型综合解读</div>
  </div>
  {build_summary_html(results, ai_results)}
  {stocks_html}
  {build_cost_html(cost_summary)}
  <div class="footer">
    本报告由自动化技术分析系统生成 · 仅供参考，不构成任何投资建议<br>
    数据来源：Yahoo Finance · AI分析：Claude Opus 4.7 / GPT-5.5 / DeepSeek V4 Pro via OpenRouter
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
    msg["Subject"] = f"📈 股票技术分析日报 v2 · {date_str}"
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
