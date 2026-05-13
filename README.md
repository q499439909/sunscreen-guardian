# 防晒管家 (Sunscreen Guardian)

基于 GitHub Actions 的飞书每日防晒提醒助手，每天早上 8 点自动推送紫外线指数和生活建议。

## 功能

- **每日推送**：每天早上 8 点（北京时间）通过飞书群机器人推送
- **紫外线趋势图**：自动生成当日 UV 指数折线图
- **智能建议**：根据天气生成防晒、穿搭、生活建议
- **手动触发**：支持在 GitHub Actions 页面手动触发推送

## 工作原理

```
GitHub Actions (cron: 每天 UTC 0:00)
  → push_daily.py
    → Open-Meteo API 获取天气
    → 生成 UV 折线图
    → 飞书 Webhook 推送消息
```

无需服务器，无需内网穿透，零成本运行。

## 配置

在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中添加：

| Secret | 说明 | 必填 |
|--------|------|------|
| `FEISHU_WEBHOOK_URL` | 飞书群机器人 Webhook 地址 | 是 |
| `DEFAULT_CITY` | 默认城市（默认"深圳"） | 否 |

## 本地运行

```bash
pip install -r requirements.txt
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx python push_daily.py
```

## 项目结构

```
SunscreenGuardian/
├── .github/workflows/
│   └── daily-push.yml      # GitHub Actions 定时任务
├── src/
│   ├── config_loader.py     # 配置加载（支持环境变量）
│   ├── weather.py           # Open-Meteo 天气 API
│   ├── advice.py            # 智能生活建议
│   ├── chart.py             # UV 折线图生成
│   └── feishu.py            # 飞书消息推送
├── push_daily.py            # 每日推送入口脚本
├── requirements.txt
└── README.md
```

## 许可证

MIT License
