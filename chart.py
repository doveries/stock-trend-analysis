"""
图表生成模块（无pandas-ta依赖）
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import pandas as pd
import numpy as np
import os, platform

def setup_chinese_font():
    import matplotlib.font_manager as fm
    candidates = []
    if platform.system() == "Linux":
        candidates = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
    elif platform.system() == "Darwin":
        candidates = ["/System/Library/Fonts/PingFang.ttc"]
    elif platform.system() == "Windows":
        candidates = ["C:/Windows/Fonts/simhei.ttf","C:/Windows/Fonts/msyh.ttc"]

    for path in candidates:
        if os.path.exists(path):
            prop = fm.FontProperties(fname=path)
            matplotlib.rcParams["font.family"] = prop.get_name()
            matplotlib.rcParams["axes.unicode_minus"] = False
            print(f"  字体加载成功：{path}")
            return True

    for name in ["WenQuanYi Micro Hei","WenQuanYi Zen Hei","Noto Sans CJK SC","SimHei"]:
        try:
            fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
            matplotlib.rcParams["font.family"] = name
            matplotlib.rcParams["axes.unicode_minus"] = False
            print(f"  字体加载成功：{name}")
            return True
        except Exception:
            continue

    matplotlib.rcParams["font.family"] = "DejaVu Sans"
    matplotlib.rcParams["axes.unicode_minus"] = False
    print("  ⚠️ 未找到中文字体，使用英文")
    return False

HAS_CHINESE = setup_chinese_font()

def lbl(zh, en):
    return zh if HAS_CHINESE else en

def generate_chart(result, output_dir="/tmp"):
    ticker = result["ticker"]
    df     = result["df"].copy().iloc[-120:]
    price  = result["price"]

    df["MA20"]  = df["Close"].rolling(20).mean()
    df["MA60"]  = df["Close"].rolling(60).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    mom       = result["8_momentum"]
    vol_state = result["9_volatility"]
    rsi_s     = mom["rsi_series"].reindex(df.index)
    macd_s    = mom["macd_series"].reindex(df.index)
    sig_s     = mom["signal_series"].reindex(df.index)
    hist_s    = mom["hist_series"].reindex(df.index)

    bg = "#1a1a2e"; tc = "#e0e0e0"; gc = "#2a2a4a"
    fig = plt.figure(figsize=(14,12), facecolor=bg)
    gs  = gridspec.GridSpec(4,1, height_ratios=[4,1.5,1.5,1.5], hspace=0.08)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax4 = fig.add_subplot(gs[3], sharex=ax1)

    for ax in [ax1,ax2,ax3,ax4]:
        ax.set_facecolor(bg)
        ax.tick_params(colors=tc, labelsize=8)
        ax.grid(color=gc, linestyle="--", linewidth=0.5, alpha=0.7)
        for sp in ax.spines.values(): sp.set_color(gc)

    dates = np.arange(len(df))

    # 主图K线
    for i,(idx,row) in enumerate(df.iterrows()):
        o,h,l,c = row["Open"],row["High"],row["Low"],row["Close"]
        col = "#26a69a" if c>=o else "#ef5350"
        ax1.plot([i,i],[l,h], color=col, linewidth=0.8, alpha=0.9)
        rh = max(abs(c-o), 0.01)
        ax1.add_patch(mpatches.FancyBboxPatch(
            (i-0.3, min(o,c)), 0.6, rh,
            boxstyle="square,pad=0", facecolor=col, edgecolor=col, alpha=0.9))

    ax1.plot(dates, df["MA20"].values,  color="#ffeb3b", linewidth=1.2, label="MA20",  alpha=0.9)
    ax1.plot(dates, df["MA60"].values,  color="#ff9800", linewidth=1.2, label="MA60",  alpha=0.9)
    ax1.plot(dates, df["MA200"].values, color="#f48fb1", linewidth=1.5, label="MA200", alpha=0.9)

    lv = result["5_levels"]
    ax1.axhline(lv["resistance"],   color="#ef5350", lw=0.8, ls="--", alpha=0.7,
                label=lbl(f"阻力 {lv['resistance']}", f"Res {lv['resistance']}"))
    ax1.axhline(lv["support"],      color="#26a69a", lw=0.8, ls="--", alpha=0.7,
                label=lbl(f"支撑 {lv['support']}",   f"Sup {lv['support']}"))
    ax1.axhline(lv["invalidation"], color="#ff5722", lw=0.8, ls=":",  alpha=0.6,
                label=lbl(f"失效 {lv['invalidation']}", f"Inv {lv['invalidation']}"))

    long_c  = result["2_long_trend"]["conclusion"]
    mid_c   = result["3_mid_trend"]["conclusion"]
    struct_c= result["4_structure"]["type"]
    ax1.set_title(
        f"{ticker}  {lbl('当前价','Price')}: ${price}  |  "
        f"{lbl('长期','LT')}: {long_c}  |  "
        f"{lbl('中期','MT')}: {mid_c}  |  "
        f"{lbl('结构','St')}: {struct_c}",
        color=tc, fontsize=11, pad=8, loc="left")
    ax1.legend(loc="upper left", fontsize=7, facecolor=bg, labelcolor=tc, framealpha=0.8, ncol=4)
    ax1.set_ylabel(lbl("价格 ($)","Price ($)"), color=tc, fontsize=9)
    ax1.yaxis.set_label_position("right"); ax1.yaxis.tick_right()

    # 成交量
    vcols = ["#26a69a" if df["Close"].iloc[i]>=df["Open"].iloc[i] else "#ef5350" for i in range(len(df))]
    ax2.bar(dates, df["Volume"].values/1e6, color=vcols, alpha=0.8, width=0.8)
    vr = result["7_volume"]
    ax2.set_title(lbl(f"成交量  量价比: {vr['ratio']}  {vr['conclusion']}",
                       f"Volume  V-ratio: {vr['ratio']}  {vr['conclusion']}"),
                  color=tc, fontsize=8, loc="left", pad=3)
    ax2.set_ylabel(lbl("量(M)","Vol(M)"), color=tc, fontsize=8)
    ax2.yaxis.set_label_position("right"); ax2.yaxis.tick_right()

    # RSI
    ax3.plot(dates, rsi_s.values, color="#ba68c8", linewidth=1.2)
    ax3.axhline(70, color="#ef5350", lw=0.8, ls="--", alpha=0.8)
    ax3.axhline(30, color="#26a69a", lw=0.8, ls="--", alpha=0.8)
    ax3.axhline(50, color=gc,        lw=0.8, ls="-",  alpha=0.5)
    ax3.fill_between(dates, rsi_s.values, 70, where=(rsi_s.values>=70), alpha=0.2, color="#ef5350")
    ax3.fill_between(dates, rsi_s.values, 30, where=(rsi_s.values<=30), alpha=0.2, color="#26a69a")
    ax3.set_ylim(0,100)
    ax3.set_title(lbl(f"RSI(14)  当前: {mom['rsi']}", f"RSI(14)  Now: {mom['rsi']}"),
                  color=tc, fontsize=8, loc="left", pad=3)
    ax3.set_ylabel("RSI", color=tc, fontsize=8)
    ax3.yaxis.set_label_position("right"); ax3.yaxis.tick_right()

    # MACD
    hcols = ["#26a69a" if v>=0 else "#ef5350" for v in hist_s.values]
    ax4.bar(dates, hist_s.values,  color=hcols, alpha=0.8, width=0.8)
    ax4.plot(dates, macd_s.values, color="#64b5f6", linewidth=1.2, label=lbl("MACD","MACD"))
    ax4.plot(dates, sig_s.values,  color="#ffb74d", linewidth=1.0, label=lbl("信号线","Signal"))
    ax4.axhline(0, color=gc, lw=0.8)
    ax4.set_title(lbl(f"MACD(12,26,9)  当前: {mom['macd_val']}",
                       f"MACD(12,26,9)  Now: {mom['macd_val']}"),
                  color=tc, fontsize=8, loc="left", pad=3)
    ax4.legend(loc="upper left", fontsize=7, facecolor=bg, labelcolor=tc, framealpha=0.8)
    ax4.set_ylabel("MACD", color=tc, fontsize=8)
    ax4.yaxis.set_label_position("right"); ax4.yaxis.tick_right()

    step   = max(1, len(df)//8)
    ticks  = list(range(0, len(df), step))
    labels = [df.index[i].strftime("%m/%d") for i in ticks]
    ax4.set_xticks(ticks); ax4.set_xticklabels(labels, color=tc, fontsize=8)
    for ax in [ax1,ax2,ax3]: plt.setp(ax.get_xticklabels(), visible=False)

    fig.text(0.5, 0.01, lbl("仅供参考，不构成投资建议","For reference only, not investment advice"),
             ha="center", color="#555577", fontsize=8, alpha=0.8)

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{ticker.replace('-','_')}_chart.png")
    plt.savefig(path, dpi=130, bbox_inches="tight", facecolor=bg)
    plt.close(fig)
    print(f"  图表保存：{path}")
    return path

if __name__ == "__main__":
    from analyze import analyze_ticker
    r = analyze_ticker("TSLA")
    generate_chart(r, "/tmp/charts")
