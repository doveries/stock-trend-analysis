"""
邮件发送模块 v2.1
含：顶部总览表 + 执行摘要 + 逐股详细分析 + 底部汇总结构列表
"""

import smtplib, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

STYLE = """
<style>
  body{font-family:-apple-system,'Segoe UI',Arial,sans-serif;background:#0f0f1a;color:#e0e0e0;margin:0;padding:20px;}
  .container{max-width:920px;margin:0 auto;}
  .header{background:linear-gradient(135deg,#1a1a3e,#2a2a5e);padding:20px 30px;border-radius:12px;margin-bottom:20px;border:1px solid #3a3a6e;}
  .header h1{margin:0;font-size:22px;color:#7986cb;}
  .header .date{color:#9e9e9e;font-size:13px;margin-top:5px;}

  /* 总览表 */
  .overview-box{background:#1a1a3e;border:1px solid #3a3a6e;border-radius:10px;padding:16px 20px;margin-bottom:20px;}
  .overview-box h2{margin:0 0 12px 0;font-size:15px;color:#7986cb;}
  .overview-table{width:100%;border-collapse:collapse;font-size:12px;}
  .overview-table th{background:#0f0f2a;color:#7986cb;padding:8px 10px;text-align:left;font-weight:600;border-bottom:1px solid #3a3a6e;}
  .overview-table td{padding:7px 10px;border-bottom:1px solid #1a1a3e;vertical-align:middle;}
  .overview-table tr:last-child td{border-bottom:none;}
  .overview-table tr:hover td{background:#1f1f3a;}
  .ticker-cell{font-weight:bold;font-size:13px;color:#e0e0e0;}
  .price-cell{color:#7986cb;font-weight:600;}
  .ai-badge{display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:bold;white-space:nowrap;}
  .badge-buy{background:#1b5e20;color:#69f0ae;}
  .badge-trial{background:#1b5e20;color:#b9f6ca;}
  .badge-hold{background:#1a237e;color:#82b1ff;}
  .badge-wait{background:#e65100;color:#ffcc80;}
  .badge-no{background:#b71c1c;color:#ff8a80;}
  .badge-na{background:#2a2a4e;color:#9e9e9e;}

  /* 执行摘要 */
  .summary-box{background:#1a1a3e;border:1px solid #3a3a6e;border-radius:10px;padding:16px 20px;margin-bottom:20px;}
  .summary-box h2{margin:0 0 12px 0;font-size:15px;color:#7986cb;}
  .summary-row{display:flex;gap:10px;flex-wrap:wrap;}
  .summary-tag{padding:5px 12px;border-radius:20px;font-size:12px;font-weight:bold;}
  .tag-bull{background:#1b5e20;color:#69f0ae;border:1px solid #2e7d32;}
  .tag-bear{background:#b71c1c;color:#ff8a80;border:1px solid #c62828;}
  .tag-wait{background:#e65100;color:#ffcc80;border:1px solid #f57c00;}
  .tag-watch{background:#1a237e;color:#82b1ff;border:1px solid #283593;}

  /* 股票卡片 */
  .stock-card{background:#1a1a2e;border:1px solid #2a2a4e;border-radius:12px;margin-bottom:24px;overflow:hidden;}
  .card-header{background:#16213e;padding:14px 20px;display:flex;justify-content:space-between;align-items:center;}
  .card-header .ticker{font-size:20px;font-weight:bold;color:#e0e0e0;}
  .card-header .price{font-size:18px;color:#7986cb;}
  .card-body{padding:16px 20px;}
  .chart-img{width:100%;border-radius:8px;margin-bottom:16px;}

  .section{margin-bottom:14px;}
  .section-title{font-size:12px;color:#7986cb;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;border-bottom:1px solid #2a2a4e;padding-bottom:4px;}
  .kv-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:6px;}
  .kv{background:#0f0f1a;padding:7px 10px;border-radius:6px;border-left:3px solid #3a3a6e;}
  .kv .k{font-size:10px;color:#9e9e9e;margin-bottom:2px;}
  .kv .v{font-size:13px;color:#e0e0e0;font-weight:500;}
  .bull{color:#69f0ae!important;} .bear{color:#ff5252!important;}
  .warn{color:#ffab40!important;} .neutral{color:#82b1ff!important;}

  /* AI板块 */
  .ai-section{background:#0d1f2d;border:1px solid #1a4060;border-radius:10px;margin:16px 0;padding:16px 20px;}
  .ai-section-title{font-size:12px;color:#4fc3f7;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;border-bottom:1px solid #1a4060;padding-bottom:6px;}
  .ai-model-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;margin-bottom:14px;}
  .ai-model-card{background:#0a1929;border:1px solid #1a3a5c;border-radius:8px;padding:10px 14px;}
  .ai-model-name{font-size:10px;color:#4fc3f7;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;}
  .ai-decision{font-size:14px;font-weight:bold;margin-bottom:4px;}
  .ai-reason{font-size:11px;color:#b0bec5;line-height:1.5;}
  .ai-trigger{font-size:11px;color:#80cbc4;margin-top:4px;}
  .ai-risk{font-size:11px;color:#ff8a80;margin-top:3px;}
  .ai-confidence{font-size:10px;color:#78909c;margin-top:3px;}

  /* 双元分析 */
  .judge-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px;}
  .ai-judge{background:#1a2744;border:1px solid #3a5a9e;border-radius:8px;padding:12px 16px;}
  .ai-judge-title{font-size:11px;color:#7986cb;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;}
  .ai-consensus{font-size:12px;color:#a5d6a7;margin-bottom:5px;}
  .ai-divergence{font-size:12px;color:#ffcc80;margin-bottom:6px;}
  .ai-final{font-size:14px;font-weight:bold;margin-bottom:4px;}
  .ai-final-trigger{font-size:11px;color:#80cbc4;margin-bottom:4px;}
  .ai-final-reason{font-size:11px;color:#b0bec5;line-height:1.5;}
  .agree-tag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;margin-left:6px;vertical-align:middle;}
  .agree-high{background:#1b5e20;color:#69f0ae;}
  .agree-mid{background:#1a237e;color:#82b1ff;}
  .agree-low{background:#b71c1c;color:#ff8a80;}

  /* 底部汇总列表 */
  .summary-list-box{background:#1a1a3e;border:1px solid #3a3a6e;border-radius:10px;padding:20px;margin-top:24px;}
  .summary-list-box h2{margin:0 0 16px 0;font-size:15px;color:#7986cb;}
  .summary-list-item{background:#0f0f2a;border:1px solid #2a2a4e;border-radius:8px;padding:14px 16px;margin-bottom:12px;}
  .sli-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;}
  .sli-ticker{font-size:16px;font-weight:bold;color:#e0e0e0;}
  .sli-price{font-size:14px;color:#7986cb;}
  .sli-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:6px;margin-bottom:8px;}
  .sli-kv{font-size:11px;}
  .sli-kv .sk{color:#9e9e9e;margin-right:4px;}
  .sli-trigger{font-size:11px;color:#80cbc4;margin-top:6px;padding-top:6px;border-top:1px solid #2a2a4e;}
  .sli-disclaimer{font-size:10px;color:#ffab40;margin-top:4px;}

  .cost-box{background:#0a1929;border:1px solid #1a3a5c;border-radius:8px;padding:10px 16px;margin-top:16px;font-size:11px;color:#78909c;}
  .cost-box span{color:#4fc3f7;}
  .footer{text-align:center;color:#555577;font-size:11px;padding:16px;border-top:1px solid #2a2a4e;margin-top:20px;}
</style>
"""


def tc(text):
    """趋势颜色"""
    if any(k in text for k in ["多头","支持","确认","放量","强","突破"]): return "bull"
    if any(k in text for k in ["空头","警惕","破坏","弱势","弱","假突破"]): return "bear"
    if any(k in text for k in ["观望","等待","不支持","不适合","存疑"]): return "warn"
    return "neutral"


def dc(d):
    """决策颜色"""
    if "买入" in d or "试多" in d: return "bull"
    if "不交易" in d or "观望" in d: return "bear"
    return "warn"


def ai_badge(decision):
    if not decision or decision == "N/A":
        return '<span class="ai-badge badge-na">暂无</span>'
    if "买入" in decision:   return f'<span class="ai-badge badge-buy">{decision}</span>'
    if "试多" in decision:   return f'<span class="ai-badge badge-trial">{decision}</span>'
    if "持有" in decision:   return f'<span class="ai-badge badge-hold">{decision}</span>'
    if "等待" in decision:   return f'<span class="ai-badge badge-wait">{decision}</span>'
    if "不交易" in decision: return f'<span class="ai-badge badge-no">{decision}</span>'
    return f'<span class="ai-badge badge-na">{decision}</span>'


def agree_cls(a):
    if "高度" in a: return "agree-high"
    if "明显" in a: return "agree-low"
    return "agree-mid"


def kv(key, val, cls=""):
    vc = f' class="{cls}"' if cls else ""
    return f'<div class="kv"><div class="k">{key}</div><div class="v"{vc}>{val}</div></div>'


def judge_card(title, j):
    if not j or j.get("error"):
        return f'<div class="ai-judge"><div class="ai-judge-title">{title}</div><div class="warn">调用失败</div></div>'
    fd  = j.get("final_decision","N/A")
    fa  = j.get("model_agreement","")
    return f'''<div class="ai-judge">
      <div class="ai-judge-title">{title}</div>
      <div class="ai-consensus">✅ 共识：{j.get("consensus","")}</div>
      <div class="ai-divergence">🔀 分歧：{j.get("divergence","")}</div>
      <div class="ai-final {dc(fd)}">{fd}
        <span class="agree-tag {agree_cls(fa)}">{fa}</span>
      </div>
      <div class="ai-final-trigger">📍 触发：{j.get("final_trigger","")}</div>
      <div class="ai-final-reason">{j.get("final_reason","")}</div>
    </div>'''


def model_card(name, r):
    if not r or r.get("error"):
        return f'<div class="ai-model-card"><div class="ai-model-name">{name}</div><div class="warn">调用失败</div></div>'
    return f'''<div class="ai-model-card">
      <div class="ai-model-name">{name}</div>
      <div class="ai-decision {dc(r.get("decision",""))}">{r.get("decision","N/A")}</div>
      <div class="ai-reason">{r.get("reason","")}</div>
      <div class="ai-trigger">📍 {r.get("trigger","")}</div>
      <div class="ai-risk">⚠️ {r.get("key_risk","")}</div>
      <div class="ai-confidence">置信度：{r.get("confidence","N/A")}</div>
    </div>'''


def build_ai_html(ticker, ai_data):
    if not ai_data:
        return ""
    return f'''<div class="ai-section">
      <div class="ai-section-title">🤖 AI 三模型独立分析</div>
      <div class="ai-model-row">
        {model_card("Claude Opus 4.7", ai_data.get("claude"))}
        {model_card("GPT-5.5", ai_data.get("gpt"))}
        {model_card("DeepSeek V4 Pro", ai_data.get("deepseek"))}
      </div>
      <div class="ai-section-title" style="margin-top:4px;">⚖️ 双元分析裁判</div>
      <div class="judge-row">
        {judge_card("Opus 4.7 解读（趋势+风控视角）", ai_data.get("opus_judge"))}
        {judge_card("GPT-5.5 解读（量化+概率视角）", ai_data.get("gpt_judge"))}
      </div>
    </div>'''


def build_stock_html(result, cid, ai_data=None):
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

    breakout_extra = ""
    if bi:
        breakout_extra = f'''
        <div class="section">
          <div class="section-title">📈 突破分析</div>
          <div class="kv-grid">
            {kv("突破状态", bi.get("struct_type",""), tc(bi.get("struct_type","")))}
            {kv("质量评分", f"{bi.get('score','?')}/5")}
            {kv("历史高位", "是" if bi.get("is_all_time_area") else "否")}
            {kv("突破幅度", f"${bi.get('breakout_amp','?')} vs 0.5ATR=${round(bi.get('atr_val',0)*0.5,2)}")}
            {kv("评分细节", " | ".join(bi.get("details",[]) or ["未达标"]))}
          </div>
        </div>'''

    rs_label = ("基准资产" if r6.get("is_benchmark") else r6["conclusion"])
    rs_color = ("neutral" if r6.get("is_benchmark") else tc(r6["conclusion"]))

    return f"""<div class="stock-card">
      <div class="card-header">
        <div><span class="ticker">{t}</span>
          <span style="margin-left:10px;font-size:12px;color:#9e9e9e;">{d}</span></div>
        <span class="price">${p}</span>
      </div>
      <div class="card-body">
        <img src="cid:{cid}" class="chart-img" alt="{t}"/>
        {build_ai_html(t, ai_data)}
        {breakout_extra}
        <div class="section"><div class="section-title">2. 长期趋势</div><div class="kv-grid">
          {kv("MA200", str(r2["ma200"]))}
          {kv("偏离MA200", f"{r2['deviation']}%", 'bull' if r2['deviation']>0 else 'bear')}
          {kv("MA200斜率", r2["slope"])}
          {kv("结论", r2["conclusion"], tc(r2["conclusion"]))}
        </div></div>
        <div class="section"><div class="section-title">3. 中期趋势</div><div class="kv-grid">
          {kv("MA20", str(r3["ma20"]))} {kv("MA60", str(r3["ma60"]))}
          {kv("MA20方向", r3["slope20"])} {kv("MA60方向", r3["slope60"])}
          {kv("结论", r3["conclusion"], tc(r3["conclusion"]))}
        </div></div>
        <div class="section"><div class="section-title">4. 价格结构</div><div class="kv-grid">
          {kv("结构类型", r4["type"], tc(r4["type"]))}
          {kv("结论", r4["conclusion"])}
          {kv("近期高点", " → ".join([f"${v}" for _,v in r4["highs"][-3:]]))}
          {kv("近期低点", " → ".join([f"${v}" for _,v in r4["lows"][-3:]]))}
        </div></div>
        <div class="section"><div class="section-title">5. 关键位置</div><div class="kv-grid">
          {kv("阻力", f"${r5['resistance']}", 'bear')}
          {kv("确认位", f"${r5['confirm']}")}
          {kv("支撑", f"${r5['support']}", 'bull')}
          {kv("失效位", f"${r5['invalidation']}", 'warn')}
        </div></div>
        <div class="section"><div class="section-title">6. 相对强弱</div><div class="kv-grid">
          {kv(f"vs {r6['index_name']}", r6['vs_index'])}
          {kv(f"vs {r6['sector_name']}", r6['vs_sector'])}
          {kv("结论", rs_label, rs_color)}
        </div></div>
        <div class="section"><div class="section-title">7. 量价确认</div><div class="kv-grid">
          {kv("上涨日均量", f"{r7['up_vol']}M")}
          {kv("下跌日均量", f"{r7['down_vol']}M")}
          {kv("20日均量", f"{r7['vol_ma20']}M")}
          {kv("量价比", str(r7["ratio"]))}
          {kv("结论", r7["conclusion"], tc(r7["conclusion"]))}
        </div></div>
        <div class="section"><div class="section-title">8. 动量状态</div><div class="kv-grid">
          {kv("RSI(14)", r8["rsi"])}
          {kv("MACD", r8["macd"])}
          {kv("柱状图", r8["histogram"])}
          {kv("结论", r8["conclusion"], tc(r8["conclusion"]))}
        </div></div>
        <div class="section"><div class="section-title">9. 波动率</div><div class="kv-grid">
          {kv("ATR(14)", str(r9["atr"]))}
          {kv("ATR/价格", f"{r9['atr_pct']}%")}
          {kv("布林带宽度", str(r9["bw_val"]))}
          {kv("状态", r9["vol_state"])}
          {kv("仓位影响", r9["pos_impact"], 'warn' if r9['pos_impact']!='正常' else '')}
        </div></div>
        <div class="section"><div class="section-title">10. 交易类型</div><div class="kv-grid">
          {kv("类型", r10["type"])}
          {kv("是否适合", r10["suitable"], tc(r10["suitable"]))}
          {kv("等待确认", r10["wait"])}
          {kv("赔率约束", "已触发" if r10.get("rr_block") else "未触发", 'warn' if r10.get("rr_block") else '')}
        </div></div>
        <div class="section"><div class="section-title">11. 风险与赔率</div><div class="kv-grid">
          {kv("参考入场", f"${r11['entry']}")}
          {kv("短线止损", f"${r11['short_stop']}", 'warn')}
          {kv("中期止损", f"${r11['mid_stop']}", 'warn')}
          {kv("结构止损", f"${r11['structure_stop']}", 'bear')}
          {kv("目标一", f"${r11['target1']}（{r11['t1_rr']}:1）{'⚠️无效' if r11['t1_invalid'] else ''}", 'bull' if not r11['t1_invalid'] else 'warn')}
          {kv("目标二", f"${r11['target2']}（{r11['t2_rr']}:1）", 'bull')}
          {kv("目标方法", r11["target_method"])}
          {kv("赔率结论", r11["conclusion"], 'bull' if r11['rr_pass'] else 'bear')}
        </div>
        <p style="font-size:11px;color:#ffab40;margin-top:8px;">⚠️ {r11['note']}</p></div>
        <div class="section"><div class="section-title">12. 事件风险</div><div class="kv-grid">
          {kv("检测结果", r12["event"])}
          {kv("风险等级", r12["risk"], 'warn' if r12['risk']=='高' else '')}
          {kv("执行建议", r12["action"])}
        </div>
        <p style="font-size:10px;color:#ffab40;margin-top:6px;">{r12["disclaimer"]}</p></div>
      </div>
    </div>"""


def build_overview_table(results, ai_results=None):
    rows = ""
    for r in results:
        if "error" in r: continue
        ticker = r["ticker"]
        lv     = r["5_levels"]
        r2     = r["2_long_trend"]
        r3     = r["3_mid_trend"]
        r11    = r["11_risk"]
        ai     = (ai_results or {}).get(ticker, {})

        # 取两个元分析中更保守的结论
        oj = ai.get("opus_judge", {})
        gj = ai.get("gpt_judge",  {})
        fd_opus = oj.get("final_decision","") if oj and not oj.get("error") else ""
        fd_gpt  = gj.get("final_decision","") if gj and not gj.get("error") else ""
        fd = fd_opus or fd_gpt or ""

        lc = tc(r2["conclusion"])
        mc = tc(r3["conclusion"])
        rr_cls = "bull" if r11["rr_pass"] else "bear"

        rows += f"""<tr>
          <td class="ticker-cell">{ticker}</td>
          <td class="price-cell">${r['price']}</td>
          <td class="{lc}">{r2['conclusion']}</td>
          <td class="{mc}">{r3['conclusion']}</td>
          <td class="bear">${lv['resistance']}</td>
          <td class="bull">${lv['support']}</td>
          <td class="warn">${lv['invalidation']}</td>
          <td class="{rr_cls}">{r11['conclusion'][:12]}...</td>
          <td>{ai_badge(fd)}</td>
        </tr>"""

    return f"""<div class="overview-box">
      <h2>📊 今日市场总览</h2>
      <table class="overview-table">
        <thead><tr>
          <th>标的</th><th>现价</th><th>长期</th><th>中期</th>
          <th>阻力</th><th>支撑</th><th>失效位</th><th>赔率</th><th>AI建议</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""


def build_summary_html(results, ai_results=None):
    tags = []
    for r in results:
        if "error" in r: continue
        ticker = r["ticker"]
        ai     = (ai_results or {}).get(ticker, {})
        oj     = ai.get("opus_judge", {})
        gj     = ai.get("gpt_judge",  {})
        fd     = (oj.get("final_decision","") if oj and not oj.get("error") else
                  gj.get("final_decision","") if gj and not gj.get("error") else "")

        if fd:
            if "买入" in fd:   css, lbl = "tag-bull", f"✅ {ticker} 建议买入"
            elif "试多" in fd: css, lbl = "tag-bull", f"🟢 {ticker} 建议试多"
            elif "不交易" in fd: css, lbl = "tag-bear", f"🔴 {ticker} 不交易"
            elif "等待" in fd: css, lbl = "tag-wait", f"⏳ {ticker} 等待确认"
            else:              css, lbl = "tag-watch", f"👀 {ticker} 持有观望"
        else:
            long_c = r["2_long_trend"]["conclusion"]
            trade  = r["10_trade"]["suitable"]
            if "适合" in trade and "多头" in long_c: css, lbl = "tag-bull", f"✅ {ticker} 可关注"
            elif "空头" in long_c:                   css, lbl = "tag-bear", f"🔴 {ticker} 趋势偏弱"
            elif "等待" in trade or "暂不" in trade: css, lbl = "tag-wait", f"⏳ {ticker} 等待确认"
            else:                                    css, lbl = "tag-watch", f"👀 {ticker} 观望"
        tags.append(f'<span class="summary-tag {css}">{lbl}</span>')

    return f"""<div class="summary-box">
      <h2>📋 今日执行摘要</h2>
      <div class="summary-row">{''.join(tags)}</div>
    </div>"""


def build_summary_list(results, ai_results=None):
    """底部汇总：每只股票一行，包含结构化关键信息"""
    items = ""
    for r in results:
        if "error" in r: continue
        ticker = r["ticker"]
        lv     = r["5_levels"]
        r2     = r["2_long_trend"]
        r3     = r["3_mid_trend"]
        r4     = r["4_structure"]
        r8     = r["8_momentum"]
        r11    = r["11_risk"]
        r12    = r["12_event"]
        ai     = (ai_results or {}).get(ticker, {})

        oj = ai.get("opus_judge", {})
        gj = ai.get("gpt_judge",  {})
        opus_fd     = oj.get("final_decision","N/A") if oj and not oj.get("error") else "N/A"
        gpt_fd      = gj.get("final_decision","N/A") if gj and not gj.get("error") else "N/A"
        opus_trigger= oj.get("final_trigger","")     if oj and not oj.get("error") else ""
        gpt_trigger = gj.get("final_trigger","")     if gj and not gj.get("error") else ""

        bi = r4.get("breakout_info") or {}
        struct_str = bi.get("struct_type", r4["type"]) if bi else r4["type"]

        items += f"""<div class="summary-list-item">
          <div class="sli-header">
            <span class="sli-ticker">{ticker}</span>
            <span class="sli-price">${r['price']}</span>
          </div>
          <div class="sli-grid">
            <div class="sli-kv"><span class="sk">长期趋势</span><span class="{tc(r2['conclusion'])}">{r2['conclusion']}</span></div>
            <div class="sli-kv"><span class="sk">中期趋势</span><span class="{tc(r3['conclusion'])}">{r3['conclusion']}</span></div>
            <div class="sli-kv"><span class="sk">价格结构</span><span class="{tc(struct_str)}">{struct_str}</span></div>
            <div class="sli-kv"><span class="sk">RSI</span><span>{r8['rsi']}</span></div>
            <div class="sli-kv"><span class="sk">阻力位</span><span class="bear">${lv['resistance']}</span></div>
            <div class="sli-kv"><span class="sk">支撑位</span><span class="bull">${lv['support']}</span></div>
            <div class="sli-kv"><span class="sk">失效位</span><span class="warn">${lv['invalidation']}</span></div>
            <div class="sli-kv"><span class="sk">目标一</span><span class="{'warn' if r11['t1_invalid'] else 'bull'}">${r11['target1']}（{r11['t1_rr']}:1）{'⚠️' if r11['t1_invalid'] else ''}</span></div>
            <div class="sli-kv"><span class="sk">目标二</span><span class="bull">${r11['target2']}（{r11['t2_rr']}:1）</span></div>
            <div class="sli-kv"><span class="sk">赔率</span><span class="{'bull' if r11['rr_pass'] else 'bear'}">{r11['conclusion'][:15]}</span></div>
            <div class="sli-kv"><span class="sk">事件风险</span><span class="{'warn' if r12['risk']=='高' else ''}">{r12['risk']}</span></div>
            <div class="sli-kv"><span class="sk">Opus建议</span>{ai_badge(opus_fd)}</div>
            <div class="sli-kv"><span class="sk">GPT建议</span>{ai_badge(gpt_fd)}</div>
          </div>
          {'<div class="sli-trigger">📍 Opus触发：' + opus_trigger + '</div>' if opus_trigger else ''}
          {'<div class="sli-trigger">📍 GPT触发：' + gpt_trigger + '</div>' if gpt_trigger else ''}
          <div class="sli-disclaimer">⚠️ 事件风险检测局限：{r12['disclaimer']}</div>
        </div>"""

    return f"""<div class="summary-list-box">
      <h2>📑 各标的详细汇总</h2>
      {items}
    </div>"""


def build_cost_html(cost):
    if not cost: return ""
    total = cost.get("total_cost", 0)
    per   = cost.get("per_model", {})
    rows  = " | ".join([f"{k.split('/')[-1]}: <span>${v['cost']}</span>" for k, v in per.items()])
    return f'<div class="cost-box">今日API费用：{rows} | 合计：<span>${total}</span> / 预算：<span>$5/模型</span></div>'


def build_full_html(results, chart_paths, ai_results=None, cost_summary=None):
    date_str    = datetime.now().strftime("%Y年%m月%d日")
    cid_map     = {}
    stocks_html = ""

    for r in results:
        if "error" in r:
            stocks_html += f'<div class="stock-card" style="padding:20px;color:#ff5252;">{r["ticker"]} 数据获取失败</div>'
            continue
        ticker = r["ticker"]
        cid    = f"chart_{ticker.replace('-','_')}"
        cid_map[cid] = chart_paths.get(ticker, "")
        stocks_html += build_stock_html(r, cid, (ai_results or {}).get(ticker))

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">{STYLE}</head>
<body><div class="container">
  <div class="header">
    <h1>📈 股票技术分析日报 v2.1</h1>
    <div class="date">{date_str} · 12项框架 + 突破识别 + AI双元分析</div>
  </div>
  {build_overview_table(results, ai_results)}
  {build_summary_html(results, ai_results)}
  {stocks_html}
  {build_summary_list(results, ai_results)}
  {build_cost_html(cost_summary)}
  <div class="footer">
    仅供参考，不构成投资建议 · 数据来源：Yahoo Finance<br>
    AI分析：Claude Opus 4.7 / GPT-5.5 / DeepSeek V4 Pro via OpenRouter
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
    msg["Subject"] = f"📈 股票技术分析日报 v2.1 · {date_str}"
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
