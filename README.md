# 📈 stock-trend-analysis

系统化技术分析日报 · 12项框架自动分析 · 每日邮件推送

## 功能
- 每天北京时间 20:00 自动分析 BRK-B、TSLA、GLD、CCJ、FCX
- 生成技术分析图表（K线+均线+RSI+MACD）
- 发送 HTML 格式邮件报告

## 部署步骤

### 1. 开启 Gmail 应用专用密码
1. 访问 [Google 账号安全设置](https://myaccount.google.com/security)
2. 开启两步验证
3. 搜索"应用专用密码"，生成一个，名称填 `stock-analysis`
4. 复制生成的 16 位密码

### 2. 填入 GitHub Secrets
进入仓库 → Settings → Secrets and variables → Actions → New repository secret

| Secret 名称 | 值 |
|---|---|
| `GMAIL_USER` | doveries@gmail.com |
| `GMAIL_APP_PASSWORD` | Gmail生成的16位应用密码 |

### 3. 手动触发测试
进入仓库 → Actions → 股票技术分析日报 → Run workflow

## 临时分析其他股票
在 Actions 页面手动触发时，在 `extra_tickers` 输入框填入股票代码（空格分隔）
例如：`AAPL NVDA`

## 免责声明
本工具仅供技术分析参考，不构成任何投资建议。
