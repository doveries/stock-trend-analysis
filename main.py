"""
主入口 v2：批量分析 + AI综合解读 + 生成图表 + 发送邮件
"""

import os
import sys
from analyze import analyze_all, STOCK_POOL
from chart import generate_chart
from email_sender import send_email
from ai_analysis import run_ai_analysis

CHART_DIR = "/tmp/charts"


def main():
    tickers = list(STOCK_POOL)
    extra_env = os.environ.get("EXTRA_TICKERS", "").strip()
    if extra_env:
        extra = [t.strip().upper() for t in extra_env.split()
                 if t.strip().replace("-", "").isalpha()]
        tickers = list(dict.fromkeys(tickers + extra))

    gmail_user     = os.environ.get("GMAIL_USER", "")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not gmail_user or not gmail_password:
        print("❌ 未找到邮件配置")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  股票技术分析日报 v2")
    print(f"  标的：{', '.join(tickers)}")
    print(f"{'='*60}")

    # 1. 技术分析（12项框架）
    results = analyze_all(tickers)

    # 2. AI综合分析（v2新增）
    ai_results, cost_summary = run_ai_analysis(results)

    # 3. 生成图表
    chart_paths = {}
    for r in results:
        if "error" not in r:
            try:
                path = generate_chart(r, output_dir=CHART_DIR)
                chart_paths[r["ticker"]] = path
            except Exception as e:
                print(f"  ⚠️ {r['ticker']} 图表生成失败: {e}")

    # 4. 发送邮件
    send_email(
        results=results,
        chart_paths=chart_paths,
        gmail_user=gmail_user,
        gmail_password=gmail_password,
        to_addr=gmail_user,
        ai_results=ai_results,
        cost_summary=cost_summary,
    )


if __name__ == "__main__":
    main()
