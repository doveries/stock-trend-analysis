"""
邮件发送模块
生成HTML格式分析报告，通过Gmail SMTP发送
"""

import smtplib
import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime


# ── HTML模板 ──────────────────────────────────────────────────
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

  /* 执行摘要 */
  .summary-box { background: #1a1a3e; border: 1px solid #3a3a6e;
                 border-radius: 10px; padding: 16px 20px; margin-bottom: 20px; }
  .summary-box h2 { margin: 0 0 12px 0; font-size: 15px; color: #7986cb; }
  .summary-row { display: flex; gap: 10px; flex-wrap: wrap; }
  .summary-tag { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
  .tag-bull  { background: #1b5e20; color: #69f0ae; border: 1px solid #2e7d32; }
  .tag-bear  { background: #b71c1c; color: #ff8a80; border: 1px solid #c62828; }
  .tag-wait  { background: #e65100; color: #ffcc80; border: 1px solid #f57c00; }
  .tag-watch { background: #1a237e; color: #82b1ff; border: 1px solid #283593; }

  /* 股票卡片 */
  .stock-card { background: #1a1a2e; border: 1px solid #2a2a4e;
                border-radius: 12px; margin-bottom: 24px; overflow: hidden; }
  .card-header { background: #16213e; padding: 14px 20px;
                 display: flex; justify-content: space-between; align-items: center; }
  .card-header .ticker { font-size: 20px; font-weight: bold; color: #e0e0e0; }
  .card-header .price  { font-size: 18px; color: #7986cb; }
  .card-header .date   { font-size: 12px; color: #9e9e9e; }

  .card-body { padding: 16px 20px; }
  .chart-img { width: 100%; border-radius: 8px; margin-bottom: 16px; }

  /* 分析表格 */
  .section { margin-bottom: 14px; }
  .section-title { font-size: 12px; color: #7986cb; text-transform: uppercase;
                   letter-spacing: 1px; margin-bottom: 6px; border-bottom: 1px solid #2a2a4e;
                   padding-bottom: 4px; }
  .kv-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
             gap: 6px; }
  .kv { background: #0f0f1a; padding: 7px 10px; border-radius: 6px;
        border-left: 3px solid #3a3a6e; }
  .kv .k { font-size: 10px; color: #9e9e9e; margin-bottom: 2px; }
  .kv .v { font-size: 13px; color: #e0e0e0; font-weight: 500; }

  /* 状态颜色 */
  .bull { color: #69f0ae !important; }
  .bear { color: #ff5252 !important; }
  .warn { color: #ffab40 !important; }
  .neutral { color: #82b1ff !important; }

  /* 底部 */
  .footer { text-align: center; color: #555577; font-size: 11px;
            padding: 16px; border-top: 1px solid #2a2a4e; margin-top: 20px; }
</style>
"""


def trend_color(text: str) -> str:
    """根据趋势结论返回颜色class"""
    if any(k in text for k in ["多头", "支持", "确认", "放量", "强"]):
        return "bull"
    elif any(k in text for k in ["空头", "警惕", "破坏", "弱势", "弱"]):
        return "bear"
    elif any(k in text for k in ["观望", "等待", "不支持", "不适合"]):
        return "warn"
    else:
        return "neutral"


def kv(key: str, value: str, color_class: str = "") -> str:
    v_class = f' class="{color_class}"' if color_class else ""
    return f'<div class="kv"><div class="k">{key}</div><div class="v"{v_class}>{value}</div></div>'


def build_stock_html(result: dict, chart_cid: str) -> str:
    """生成单只股票的HTML内容"""
    t = result["ticker"]
    p = result["price"]
    d = result["date"]

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

    html = f"""
    <div class="stock-card">
      <div class="card-header">
        <div>
          <span class="ticker">{t}</span>
          <span style="margin-left:10px; font-size:12px; color:#9e9e9e;">{d}</span>
        </div>
        <span class="price">${p}</span>
      </div>
      <div class="card-body">
        <img src="cid:{chart_cid}" class="chart-img" alt="{t} 技术分析图"/>

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
            {kv("价格偏离MA200", f"{r2['deviation']}%", 'bull' if r2['deviation'] > 0 else 'bear')}
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
            {kv("近期高点序列", " → ".join([f"{v}" for _, v in r4["highs"][-3:]]))}
            {kv("近期低点序列", " → ".join([f"{v}" for _, v in r4["lows"][-3:]]))}
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
            {kv("仓位影响", r9["pos_impact"], 'warn' if r9['pos_impact'] != '正常' else '')}
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
            {kv("赔率结论", r11["conclusion"], 'warn')}
          </div>
          <p style="font-size:11px; color:#ffab40; margin-top:8px;">⚠️ {r11['note']}</p>
        </div>

        <div class="section">
          <div class="section-title">12. 事件风险</div>
          <div class="kv-grid">
            {kv("未来事件", r12["event"])}
            {kv("事件风险", r12["risk"], trend_color("警惕" if r12["risk"]=="高" else "支持"))}
            {kv("执行方式", r12["action"])}
          </div>
        </div>

      </div>
    </div>
    """
    return html


def build_summary_html(results: list) -> str:
    """生成执行摘要"""
    tags = []
    for r in results:
        if "error" in r:
            continue
        ticker = r["ticker"]
        trade_type = r["10_trade"]["suitable"]
        long_c = r["2_long_trend"]["conclusion"]

        if "适合" in trade_type and "多头" in long_c:
            css = "tag-bull"
            label = f"✅ {ticker} 可关注"
        elif "空头" in long_c:
            css = "tag-bear"
            label = f"🔴 {ticker} 趋势偏弱"
        elif "等待" in trade_type or "暂不" in trade_type:
            css = "tag-wait"
            label = f"⏳ {ticker} 等待确认"
        else:
            css = "tag-watch"
            label = f"👀 {ticker} 观望"

        tags.append(f'<span class="summary-tag {css}">{label}</span>')

    return f"""
    <div class="summary-box">
      <h2>📋 今日执行摘要</h2>
      <div class="summary-row">{''.join(tags)}</div>
    </div>
    """


def build_full_html(results: list, chart_paths: dict) -> tuple:
    """生成完整HTML邮件内容，返回(html_str, cid_map)"""
    date_str = datetime.now().strftime("%Y年%m月%d日")
    cid_map = {}

    stocks_html = ""
    for r in results:
        if "error" in r:
            stocks_html += f'<div class="stock-card" style="padding:20px;color:#ff5252;">{r["ticker"]} 数据获取失败</div>'
            continue
        ticker = r["ticker"]
        cid = f"chart_{ticker.replace('-', '_')}"
        cid_map[cid] = chart_paths.get(ticker, "")
        stocks_html += build_stock_html(r, cid)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8">{STYLE}</head>
    <body>
      <div class="container">
        <div class="header">
          <h1>📈 股票技术分析日报</h1>
          <div class="date">{date_str} · 系统化12项框架分析</div>
        </div>
        {build_summary_html(results)}
        {stocks_html}
        <div class="footer">
          本报告由自动化技术分析系统生成 · 仅供参考，不构成任何投资建议<br>
          数据来源：Yahoo Finance · 分析框架：系统化技术分析策略 v1.0
        </div>
      </div>
    </body>
    </html>
    """
    return html, cid_map


def send_email(results: list, chart_paths: dict,
               gmail_user: str, gmail_password: str,
               to_addr: str = None) -> bool:
    """发送HTML邮件"""
    if to_addr is None:
        to_addr = gmail_user

    html_content, cid_map = build_full_html(results, chart_paths)
    date_str = datetime.now().strftime("%Y-%m-%d")

    msg = MIMEMultipart("related")
    msg["Subject"] = f"📈 股票技术分析日报 · {date_str}"
    msg["From"]    = gmail_user
    msg["To"]      = to_addr

    # HTML正文
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_content, "html", "utf-8"))
    msg.attach(alt)

    # 内嵌图片
    for cid, path in cid_map.items():
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                img = MIMEImage(f.read())
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=os.path.basename(path))
            msg.attach(img)

    # 发送
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_addr, msg.as_string())
        print(f"✅ 邮件已发送至 {to_addr}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False


if __name__ == "__main__":
    # 测试：生成HTML但不发送
    from analyze import analyze_ticker
    from chart import generate_chart
    import tempfile

    result = analyze_ticker("TSLA")
    chart_path = generate_chart(result, output_dir="/tmp/charts")
    html, _ = build_full_html([result], {"TSLA": chart_path})

    with open("/tmp/test_report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML报告已生成：/tmp/test_report.html")
