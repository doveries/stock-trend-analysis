"""
图表生成模块
每只股票生成：主图(K线+均线) + 成交量 + RSI + MACD
中文字体兼容处理
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import pandas as pd
import numpy as np
import pandas_ta as ta
import os
import platform

# ── 中文字体配置 ──────────────────────────────────────────────
def setup_chinese_font():
    """跨平台中文字体配置"""
    import matplotlib.font_manager as fm

    system = platform.system()

    # 候选字体列表（按优先级）
    font_candidates = []

    if system == "Linux":
        font_candidates = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        ]
    elif system == "Darwin":
        font_candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode MS.ttf",
        ]
    elif system == "Windows":
        font_candidates = [
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/msyh.ttc",
        ]

    for path in font_candidates:
        if os.path.exists(path):
            prop = fm.FontProperties(fname=path)
            matplotlib.rcParams["font.family"] = prop.get_name()
            matplotlib.rcParams["axes.unicode_minus"] = False
            print(f"  字体加载成功：{path}")
            return True

    # fallback：尝试系统字体名称
    for font_name in ["WenQuanYi Micro Hei", "Noto Sans CJK SC", "SimHei", "Arial Unicode MS"]:
        try:
            fm.findfont(fm.FontProperties(family=font_name), fallback_to_default=False)
            matplotlib.rcParams["font.family"] = font_name
            matplotlib.rcParams["axes.unicode_minus"] = False
            print(f"  字体加载成功（系统字体）：{font_name}")
            return True
        except Exception:
            continue

    # 最终fallback：使用英文，避免乱码
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
    matplotlib.rcParams["axes.unicode_minus"] = False
    print("  ⚠️ 未找到中文字体，使用英文标注")
    return False

HAS_CHINESE = setup_chinese_font()


def label(zh: str, en: str) -> str:
    """根据字体可用性返回中文或英文标注"""
    return zh if HAS_CHINESE else en


def generate_chart(result: dict, output_dir: str = "/tmp") -> str:
    """生成单只股票的技术分析图表，返回图片路径"""
    ticker = result["ticker"]
    df = result["df"].copy()
    price = result["price"]

    # 只取最近120个交易日
    df = df.iloc[-120:]

    # 计算指标
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    rsi = ta.rsi(df["Close"], length=14)
    macd_df = ta.macd(df["Close"], fast=12, slow=26, signal=9)

    macd_col = [c for c in macd_df.columns if c.startswith("MACD_") and "s" not in c.lower() and "h" not in c.lower()]
    sig_col  = [c for c in macd_df.columns if "MACDs" in c]
    hist_col = [c for c in macd_df.columns if "MACDh" in c]

    # ── 布局 ──────────────────────────────────────────────────
    fig = plt.figure(figsize=(14, 12), facecolor="#1a1a2e")
    gs = gridspec.GridSpec(4, 1, height_ratios=[4, 1.5, 1.5, 1.5], hspace=0.08)

    ax1 = fig.add_subplot(gs[0])  # 主图
    ax2 = fig.add_subplot(gs[1], sharex=ax1)  # 成交量
    ax3 = fig.add_subplot(gs[2], sharex=ax1)  # RSI
    ax4 = fig.add_subplot(gs[3], sharex=ax1)  # MACD

    bg_color = "#1a1a2e"
    text_color = "#e0e0e0"
    grid_color = "#2a2a4a"

    for ax in [ax1, ax2, ax3, ax4]:
        ax.set_facecolor(bg_color)
        ax.tick_params(colors=text_color, labelsize=8)
        ax.grid(color=grid_color, linestyle="--", linewidth=0.5, alpha=0.7)
        for spine in ax.spines.values():
            spine.set_color(grid_color)

    dates = np.arange(len(df))

    # ── 主图：K线（用矩形近似）+ 均线 ─────────────────────────
    for i, (idx, row) in enumerate(df.iterrows()):
        o, h, l, c = row["Open"], row["High"], row["Low"], row["Close"]
        color = "#26a69a" if c >= o else "#ef5350"
        # 影线
        ax1.plot([i, i], [l, h], color=color, linewidth=0.8, alpha=0.9)
        # 实体
        rect_h = abs(c - o) if abs(c - o) > 0 else 0.01
        rect_y = min(o, c)
        rect = mpatches.FancyBboxPatch(
            (i - 0.3, rect_y), 0.6, rect_h,
            boxstyle="square,pad=0",
            facecolor=color, edgecolor=color, alpha=0.9
        )
        ax1.add_patch(rect)

    # 均线
    ax1.plot(dates, df["MA20"].values,  color="#ffeb3b", linewidth=1.2, label=label("MA20", "MA20"), alpha=0.9)
    ax1.plot(dates, df["MA60"].values,  color="#ff9800", linewidth=1.2, label=label("MA60", "MA60"), alpha=0.9)
    ax1.plot(dates, df["MA200"].values, color="#f48fb1", linewidth=1.5, label=label("MA200", "MA200"), alpha=0.9)

    # 关键位置标线
    levels = result["5_levels"]
    ax1.axhline(levels["resistance"],   color="#ef5350", linewidth=0.8, linestyle="--", alpha=0.7,
                label=label(f"阻力 {levels['resistance']}", f"Res {levels['resistance']}"))
    ax1.axhline(levels["support"],      color="#26a69a", linewidth=0.8, linestyle="--", alpha=0.7,
                label=label(f"支撑 {levels['support']}", f"Sup {levels['support']}"))
    ax1.axhline(levels["invalidation"], color="#ff5722", linewidth=0.8, linestyle=":",  alpha=0.6,
                label=label(f"失效位 {levels['invalidation']}", f"Inv {levels['invalidation']}"))

    # 标题
    long_c  = result["2_long_trend"]["conclusion"]
    mid_c   = result["3_mid_trend"]["conclusion"]
    struct_c = result["4_structure"]["type"]
    ax1.set_title(
        f"{ticker}  {label('当前价', 'Price')}: ${price}  |  "
        f"{label('长期', 'LT')}: {long_c}  |  "
        f"{label('中期', 'MT')}: {mid_c}  |  "
        f"{label('结构', 'St')}: {struct_c}",
        color=text_color, fontsize=11, pad=8, loc="left"
    )
    ax1.legend(loc="upper left", fontsize=7, facecolor=bg_color, labelcolor=text_color,
               framealpha=0.8, ncol=4)
    ax1.set_ylabel(label("价格 ($)", "Price ($)"), color=text_color, fontsize=9)
    ax1.yaxis.set_label_position("right")
    ax1.yaxis.tick_right()

    # ── 成交量图 ──────────────────────────────────────────────
    vol_colors = ["#26a69a" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#ef5350"
                  for i in range(len(df))]
    ax2.bar(dates, df["Volume"].values / 1e6, color=vol_colors, alpha=0.8, width=0.8)
    ax2.set_ylabel(label("量(M)", "Vol(M)"), color=text_color, fontsize=8)
    ax2.yaxis.set_label_position("right")
    ax2.yaxis.tick_right()

    vol_ratio = result["7_volume"]["ratio"]
    vol_conclusion = result["7_volume"]["conclusion"]
    ax2.set_title(
        label(f"成交量  量价比: {vol_ratio}  {vol_conclusion}", f"Volume  V-ratio: {vol_ratio}  {vol_conclusion}"),
        color=text_color, fontsize=8, loc="left", pad=3
    )

    # ── RSI图 ─────────────────────────────────────────────────
    if rsi is not None and not rsi.empty:
        rsi_aligned = rsi.reindex(df.index)
        ax3.plot(dates, rsi_aligned.values, color="#ba68c8", linewidth=1.2)
        ax3.axhline(70, color="#ef5350", linewidth=0.8, linestyle="--", alpha=0.8)
        ax3.axhline(30, color="#26a69a", linewidth=0.8, linestyle="--", alpha=0.8)
        ax3.axhline(50, color=grid_color, linewidth=0.8, linestyle="-", alpha=0.5)
        ax3.fill_between(dates, rsi_aligned.values, 70,
                         where=(rsi_aligned.values >= 70), alpha=0.2, color="#ef5350")
        ax3.fill_between(dates, rsi_aligned.values, 30,
                         where=(rsi_aligned.values <= 30), alpha=0.2, color="#26a69a")
        ax3.set_ylim(0, 100)
        rsi_now = result["8_momentum"]["rsi"]
        ax3.set_title(label(f"RSI(14)  当前: {rsi_now}", f"RSI(14)  Now: {rsi_now}"),
                      color=text_color, fontsize=8, loc="left", pad=3)
    ax3.set_ylabel("RSI", color=text_color, fontsize=8)
    ax3.yaxis.set_label_position("right")
    ax3.yaxis.tick_right()

    # ── MACD图 ────────────────────────────────────────────────
    if macd_col and sig_col and hist_col:
        macd_aligned = macd_df[macd_col[0]].reindex(df.index)
        sig_aligned  = macd_df[sig_col[0]].reindex(df.index)
        hist_aligned = macd_df[hist_col[0]].reindex(df.index)

        hist_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in hist_aligned.values]
        ax4.bar(dates, hist_aligned.values, color=hist_colors, alpha=0.8, width=0.8)
        ax4.plot(dates, macd_aligned.values, color="#64b5f6", linewidth=1.2,
                 label=label("MACD", "MACD"))
        ax4.plot(dates, sig_aligned.values,  color="#ffb74d", linewidth=1.0,
                 label=label("信号线", "Signal"))
        ax4.axhline(0, color=grid_color, linewidth=0.8)

        macd_now = result["8_momentum"]["macd_val"]
        ax4.set_title(label(f"MACD(12,26,9)  当前: {macd_now}", f"MACD(12,26,9)  Now: {macd_now}"),
                      color=text_color, fontsize=8, loc="left", pad=3)
        ax4.legend(loc="upper left", fontsize=7, facecolor=bg_color, labelcolor=text_color, framealpha=0.8)
    ax4.set_ylabel("MACD", color=text_color, fontsize=8)
    ax4.yaxis.set_label_position("right")
    ax4.yaxis.tick_right()

    # ── X轴：显示日期 ─────────────────────────────────────────
    tick_step = max(1, len(df) // 8)
    tick_positions = list(range(0, len(df), tick_step))
    tick_labels = [df.index[i].strftime("%m/%d") for i in tick_positions]
    ax4.set_xticks(tick_positions)
    ax4.set_xticklabels(tick_labels, color=text_color, fontsize=8)
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.setp(ax2.get_xticklabels(), visible=False)
    plt.setp(ax3.get_xticklabels(), visible=False)

    # ── 水印 ──────────────────────────────────────────────────
    fig.text(0.5, 0.01,
             label("仅供参考，不构成投资建议", "For reference only, not investment advice"),
             ha="center", color="#555577", fontsize=8, alpha=0.8)

    # ── 保存 ──────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{ticker.replace('-', '_')}_chart.png")
    plt.savefig(path, dpi=130, bbox_inches="tight", facecolor=bg_color)
    plt.close(fig)
    print(f"  图表已保存：{path}")
    return path


if __name__ == "__main__":
    from analyze import analyze_ticker
    result = analyze_ticker("TSLA")
    path = generate_chart(result, output_dir="/tmp/charts")
    print(f"图表路径：{path}")
