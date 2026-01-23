# StockTradebyZ

[English](README.md) | [简体中文](README_CN.md)

> **Professional A-Share Stock Selection & Backtesting Laboratory**
> 
> Built on quantitative analysis principles, this project provides a powerful strategy backtesting platform with modern Web UI and high-performance Parquet data storage.

## Core Features 🚀

- **📊 Strategy Dashboard**: Interactive bubble charts to identify "High Win-Rate + High Return" strategies.
- **🧪 Stock Laboratory**: Batch selection with auto-backtest, calculating 1/3/5/10-day returns.
- **⚡ High Performance**: Parquet-first storage, parallel processing (~1 min per 5000+ stocks).
- **🌍 Bilingual**: One-click switch between **English** / **简体中文**.
- **🐳 Docker Ready**: One-command deployment.

---

## Quick Start (Docker) → Recommended

```bash
# Clone repository
git clone https://github.com/Uoghluvm/StockTradebyZ.git
cd StockTradebyZ

# Configure Tushare Token
cp .env.example .env
# Edit .env and add your Tushare Token

# Start container
docker-compose up -d

# Open browser: http://localhost:8501
```

---

## Manual Installation

### Prerequisites
- Python 3.10+
- Tushare Token ([Get it here](https://tushare.pro/))

### Steps

```bash
# 1. Clone
git clone https://github.com/Uoghluvm/StockTradebyZ.git
cd StockTradebyZ

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure Tushare Token
cp .env.example .env
# Edit .env and add your token: TUSHARE_TOKEN=your_token_here

# 4. Download market data (saves to data_parquet/)
python scripts/fetch_kline.py

# 5. Start Web UI
streamlit run web/app.py
```

---

## Built-in Strategies

| Strategy | Core Logic | Use Case |
|----------|------------|----------|
| **暴力K战法** | High-volume breakout near chip cost | Bottom reversal |
| **填坑战法** | Double-peak + KDJ golden cross | Oversold bounce |
| **少妇战法** | BBI bullish + KDJ low resonance | Trend continuation |
| **上穿60放量** | Volume breakout above MA60 | Mid-term right-side |
| **SuperB1** | Enhanced 少妇 + sharp dip | Bull pullback |
| **补票战法** | RSV divergence + MACD confirmation | Oscillation uptrend |

See `src/strategy.py` for full implementation.

---

## CLI Usage (Advanced)

```bash
# Single-day selection
python scripts/select_stock.py --date 2026-01-20

# Single-day backtest
python scripts/backtest.py logs/2026-01-20选股.csv

# Batch run (with auto-skip and parallel processing)
python scripts/batch_run.py --start 2025-01-01 --end 2025-12-31 --skip

# Background batch (long-running)
nohup python scripts/batch_run.py --start 2025-01-01 --end 2025-12-31 --skip > batch.log 2>&1 &
```

---

## Architecture

```
StockTradebyZ/
├── .env.example             # Environment variable template
├── web/app.py               # Streamlit Web UI
├── scripts/
│   ├── fetch_kline.py       # Data sync → data_parquet/*.parquet
│   ├── select_stock.py      # Strategy engine (parallel)
│   ├── backtest.py          # Return calculation
│   ├── batch_run.py         # Batch automation
│   ├── find_stock.py        # Stock lookup utility
│   ├── sector_shift.py      # Sector rotation analysis
│   └── analyze_results.py   # Results aggregation
├── src/strategy.py          # Strategy definitions
├── config/
│   ├── strategies.json      # Strategy configs
│   └── stock_list.csv       # Stock universe
├── data_parquet/            # Stock data (Parquet format)
├── logs/                    # Selection results (CSV)
└── results/                 # Backtest results (CSV)
```

---

## Credits

Built by **Antigravity**. Powered by Python, Pandas, Streamlit & Plotly.
