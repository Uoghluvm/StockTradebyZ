# StockTrade Swiss Lab 🇨🇭

[English](README.md) | [简体中文](README_CN.md)

Based on robust quantitative analysis, this project provides a professional and powerful stock strategy backtesting laboratory.

## Core Features 🚀

- **Strategy Dashboard**: Professional analytics interface with strict data visualization.
- **Stock Laboratory**:
  - **Batch Selection**: Run strategies across date ranges automatically.
  - **Auto-Backtest**: Calculate 1/3/5/10-day returns instantly.
- **Strategy Matrix**: Interactive bubble charts to find "High Win-Rate + High Return" strategies.
- **Dual Language**: One-click switch between **English** and **简体中文**.
- **Data Center**: Manage Tushare tokens and sync market data easily.

## Quick Start (Docker) -> Recommended for New Users

1. **Install Docker Desktop**.
2. **Run**:
   ```bash
   docker-compose up -d
   ```
3. **Open Browser**: Visit `http://localhost:8501`.

## Manual Installation

### Prerequisites
- Python 3.10+
- Tushare Token (Get it from [Tushare](https://tushare.pro/))

### Steps
1. **Clone repository**:
   ```bash
   git clone https://github.com/your-repo/StockTradebyZ.git
   cd StockTradebyZ
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Start Web App**:
   ```bash
   streamlit run web/app.py
   ```

## Architecture

- **Frontend**: Streamlit + Custom CSS Injection
- **Backend Scripts**:
  - `scripts/select_stock.py`: Strategy execution core.
  - `scripts/backtest.py`: Profit calculation engine.
  - `scripts/fetch_kline.py`: Data synchronization.
- **Data Storage**:
  - `logs/`: Selection logs.
  - `results/`: Backtest CSV reports.
  - `data/`: Raw K-line data.

## Credits

Designed by **Antigravity**. 
Powered by Python, Pandas, and Plotly.
