# StockTrade Swiss Lab 🇨🇭

[English](README.md) | [简体中文](README_CN.md)

> **基于 Z 哥战法的 Python 实现 (加强版)**
> 
> 现代化的 A 股选股回测实验室。完整实现"暴力K"、"填坑"、"少妇"等经典战法，提供开箱即用的 Web 可视化看板及高性能 Parquet 数据存储。

## 核心功能 🚀

- **📊 策略全景看板**: 交互式气泡图，一眼识别 "高胜率 + 高收益" 策略。
- **🧪 选股实验室**: 批量选股 + 自动回测，即刻计算 1/3/5/10 日收益率。
- **⚡ 高性能优化**: Parquet 数据格式 + 多进程并行处理（5000+ 股票约 1 分钟）。
- **🌍 双语支持**: 一键切换 **English** / **简体中文**。
- **🐳 开源友好**: Docker 一键部署。

---

## 快速开始 (Docker) → 推荐

```bash
# 克隆仓库
git clone https://github.com/Uoghluvm/StockTradebyZ.git
cd StockTradebyZ

# 配置 Tushare Token
cp .env.example .env
# 编辑 .env 文件，填入你的 Tushare Token

# 启动容器
docker-compose up -d

# 打开浏览器: http://localhost:8501
```

---

## 手动安装

### 环境要求
- Python 3.10+
- Tushare Token ([获取地址](https://tushare.pro/))

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/Uoghluvm/StockTradebyZ.git
cd StockTradebyZ

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 Tushare Token
cp .env.example .env
# 编辑 .env 文件: TUSHARE_TOKEN=your_token_here

# 4. 下载行情数据 (保存到 data_parquet/)
python scripts/fetch_kline.py

# 5. 启动 Web 应用
streamlit run web/app.py
```

---

## 内置策略

| 策略 | 核心逻辑 | 适用场景 |
|------|---------|---------|
| **暴力K战法** | 放量长阳突破，贴近筹码均线 | 底部启动 |
| **填坑战法** | 双峰结构 + KDJ 低位金叉 | 超跌反弹 |
| **少妇战法** | BBI 多头 + KDJ 低位共振 | 趋势中继 |
| **上穿60放量** | 放量突破 MA60 | 中线右侧 |
| **SuperB1** | 少妇增强版 + 急跌黄金坑 | 牛回头 |
| **补票战法** | RSV 背离 + MACD 确认 | 震荡上行 |

详见 `src/strategy.py`

---

## 命令行使用 (高级)

```bash
# 单日选股
python scripts/select_stock.py --date 2026-01-20

# 单日回测
python scripts/backtest.py logs/2026-01-20选股.csv

# 批量运行 (支持自动跳过 + 并行处理)
python scripts/batch_run.py --start 2025-01-01 --end 2025-12-31 --skip

# 后台批量运行 (长时间任务)
nohup python scripts/batch_run.py --start 2025-01-01 --end 2025-12-31 --skip > batch.log 2>&1 &
```

---

## 项目结构

```
StockTradebyZ/
├── .env.example             # 环境变量模板
├── web/app.py               # Streamlit Web 界面
├── scripts/
│   ├── fetch_kline.py       # 数据同步 → data_parquet/*.parquet
│   ├── select_stock.py      # 策略引擎 (并行处理)
│   ├── backtest.py          # 收益计算
│   ├── batch_run.py         # 批量自动化
│   ├── find_stock.py        # 股票查找工具
│   ├── sector_shift.py      # 板块轮动分析
│   └── analyze_results.py   # 结果汇总分析
├── src/strategy.py          # 策略定义
├── config/
│   ├── strategies.json      # 策略配置
│   └── stock_list.csv       # 股票池
├── data_parquet/            # 股票数据 (Parquet 格式)
├── logs/                    # 选股结果 (CSV)
└── results/                 # 回测结果 (CSV)
```

---

## 致谢

设计与开发 by **Antigravity**. Powered by Python, Pandas, Streamlit & Plotly.
