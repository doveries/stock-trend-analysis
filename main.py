"""
主入口 v3.0：分析 + AI + 历史对比 + 邮件
"""

import os
import sys
from analyze import analyze_all, STOCK_POOL
from chart import generate_chart
from email_sender import send_email
from ai_analysis import run_ai_analysis
from history import (
    load_history, update_history, extract_snapshot,
    get_yesterday_snapshot, detect_changes, build_action_summary
)

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
        print("❌ 邮件配置缺失")
        sys.exit(1)

    print(f"\n{'='*60}\n  股票技术分析 v3.0\n  标的：{', '.join(tickers)}\n{'='*60}")

    # 1. 技术分析
    results = analyze_all(tickers)

    # 2. AI分析
    ai_results, cost_summary = run_ai_analysis(results)

    # 3. 历史对比
    print(f"\n{'='*60}\n  历史对比 + 变化检测\n{'='*60}")
    history = load_history()
    yesterday_date, yesterday_snapshot = get_yesterday_snapshot(history)
    today_snapshot = extract_snapshot(results, ai_results)
    changes = detect_changes(today_snapshot, yesterday_snapshot)
    need_attention, no_action = build_action_summary(today_snapshot, changes)

    print(f"  最近一次档案：{yesterday_date or '无'}")
    print(f"  今日变化标的：{list(changes.keys()) if changes else '无'}")
    print(f"  需要关注：{need_attention}")
    print(f"  无需操作：{no_action}")

    # 更新历史档案
    update_history(today_snapshot)
    print(f"  ✅ 历史档案已更新")

    # 4. 生成图表
    chart_paths = {}
    for r in results:
        if "error" not in r:
            try:
                path = generate_chart(r, output_dir=CHART_DIR)
                chart_paths[r["ticker"]] = path
            except Exception as e:
                print(f"  ⚠️ {r['ticker']} 图表生成失败: {e}")

    # 5. 发送邮件
    send_email(
        results=results,
        chart_paths=chart_paths,
        gmail_user=gmail_user,
        gmail_password=gmail_password,
        to_addr=gmail_user,
        ai_results=ai_results,
        cost_summary=cost_summary,
        today_snapshot=today_snapshot,
        changes=changes,
        no_action_tickers=no_action,
    )


if __name__ == "__main__":
    main()
