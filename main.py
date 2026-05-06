"""
主入口：批量分析 + 生成图表 + 发送邮件
"""

import os
import sys
from analyze import analyze_all, STOCK_POOL
from chart import generate_chart
from email_sender import send_email

CHART_DIR = "/tmp/charts"


def main():
    # 安全读取额外股票（从环境变量，不从命令行，避免注入）
    tickers = list(STOCK_POOL)
    extra_env = os.environ.get("EXTRA_TICKERS", "").strip()
    if extra_env:
        extra = [t.strip().upper() for t in extra_env.split() if t.strip().isalpha() or "-" in t]
        tickers = list(dict.fromkeys(tickers + extra))

    gmail_user     = os.environ.get("GMAIL_USER", "")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not gmail_user or not gmail_password:
        print("❌ 未找到 GMAIL_USER 或 GMAIL_APP_PASSWORD 环境变量")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  股票技术分析日报")
    print(f"  标的：{', '.join(tickers)}")
    print(f"{'='*60}")

    # 1. 分析（内部统一预拉取参考数据）
    results = analyze_all(tickers)

    # 2. 生成图表
    chart_paths = {}
    for r in results:
        if "error" not in r:
            try:
                path = generate_chart(r, output_dir=CHART_DIR)
                chart_paths[r["ticker"]] = path
            except Exception as e:
                print(f"  ⚠️ {r['ticker']} 图表生成失败: {e}")

    # 3. 发送邮件
    send_email(
        results=results,
        chart_paths=chart_paths,
        gmail_user=gmail_user,
        gmail_password=gmail_password,
        to_addr=gmail_user,
    )


if __name__ == "__main__":
    main()
