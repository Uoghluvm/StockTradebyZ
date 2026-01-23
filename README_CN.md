# StockTrade Swiss Lab 🇨🇭

[English](README.md) | [简体中文](README_CN.md)

> **基于 Z 哥战法的 Python 实现 (加强版)**
> 
> 这是一个现代化的 A 股选股回测实验室。它完整实现了“暴力K”、“填坑”、“少妇”等经典战法，并提供了开箱即用的 Web 可视化看板以及全自动化的回测流程。

## 核心功能 🚀

- **📊 策略全景看板**:
  - 交互式气泡图：一眼识别 "高胜率 + 高收益" 的圣杯策略。
  - 核心 KPI 统计：一站式查看总荐股数、最佳策略得分。
- **🧪 选股实验室**:
  - **批量选股**: 支持日期范围循环执行，自动跳过已跑过的日期。
  - **自动回测**: 选股完成后自动触发回测，即刻计算 1/3/5/10 日收益率。
- **🌍 双语支持**: 侧边栏一键切换 **English** / **简体中文**。
- **🐳 开源友好**: 提供 Docker 一键部署，无需繁琐的 Python 环境配置。

---

## 快速开始 (Docker) -> 推荐新手

1. **安装 Docker Desktop**.
2. **运行**:

   ```bash
   docker-compose up -d
   ```

3. **打开浏览器**: 访问 `http://localhost:8501`.

---

## 手动安装指南

### 环境要求

- Python 3.10+
- Tushare Token (获取方式: [Tushare Pro](https://tushare.pro/))

### 安装步骤

1. **克隆仓库**:

   ```bash
   git clone https://github.com/your-repo/StockTradebyZ.git
   cd StockTradebyZ
   ```

2. **安装依赖**:

   ```bash
   pip install -r requirements.txt
   ```

3. **启动 Web 应用**:

   ```bash
   streamlit run web/app.py
   ```

---

## 内置策略 (Selector)

本项目内置了 6 种经典战法策略，涵盖趋势、反转、量能等多种维度：

### 1. 暴力K战法 (BigBullishVolume)

- **核心逻辑**: 捕捉放量启动、贴近短线均值的强势阳线。
- **特征**: 当日长阳突破 (涨幅 > 4%)，量能放大 1.5 倍以上，且收盘价未偏离筹码均线过远。
- **适用场景**: 底部启动或中继加速。

### 2. 填坑战法 (PeakKDJ)

- **核心逻辑**: 寻找前期有“坑口”压力，近期缩量回调后重新挑战的标的。
- **特征**: 识别历史双峰结构，结合 KDJ 低位金叉筛选“填坑”时机。
- **适用场景**: 超跌反弹或主力洗盘结束。

### 3. 少妇战法 (BBIKDJ)

- **核心逻辑**: BBI 多头排列，配合 KDJ 低位共振。
- **特征**: BBI 趋势整体向上 (允许微小回撤)，KDJ J 值处于历史低位分位数。
- **适用场景**: 趋势中继的二次启动点。

### 4. 上穿60放量战法 (MA60CrossVolumeWave)

- **核心逻辑**: 均线多头趋势下，捕捉放量突破 60 日线的波段机会。
- **特征**: 近期有效上穿 MA60，且上涨波段成交量显著放大，配合 MA60 斜率向上。
- **适用场景**: 中线趋势确立后的右侧交易。

### 5. SuperB1 选股器 (SuperB1)

- **核心逻辑**: `少妇战法` 的增强版，叠加盘整与急跌过滤。
- **特征**: 历史曾满足 BBIKDJ 条件，经历缩量盘整后，当日出现急跌且 J 值极低 (黄金坑)。
- **适用场景**: 牛回头策略。

### 6. 补票战法 (BBIShortLong)

- **核心逻辑**: 利用不同周期的 RSV 指标背离与共振捕捉买点。
- **特征**: BBI 向上，且短期 RSV 与长期 RSV 出现特定的交叉或背离形态，配合 MACD 确认。
- **适用场景**: 震荡上行市。

*(更多策略详情及参数调整请参阅代码 `src/strategy.py`)*

---

## 命令行使用 (高级)

除 Web 界面外，你也支持使用命令行进行自动化集成：

- **单日选股**: `python scripts/select_stock.py --date 2026-01-20`
- **单日回测**: `python scripts/backtest.py logs/2026-01-20选股.log`
- **批量运行**: `python scripts/batch_run.py 2026-01`
- **全量分析**: `python scripts/analyze_results.py`

## 致谢

设计与开发 by **Antigravity**.
Based on Python, Pandas, Streamlit & Plotly.
