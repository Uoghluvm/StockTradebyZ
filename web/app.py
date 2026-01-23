import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import subprocess
import os
import json
import time
from datetime import datetime, date, timedelta

# 引入自定义 Swiss Style 样式
from utils.ui import inject_swiss_style, swiss_header
# 引入多语言支持
from utils.lang import get_text, TRANSLATIONS

# 页面配置
st.set_page_config(
    page_title="StockTrade Swiss Lab",
    page_icon="🇨🇭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 注入 CSS
inject_swiss_style()

# ---------- 状态管理 ----------
if 'language' not in st.session_state:
    st.session_state['language'] = 'CN'

def T(key, **kwargs):
    return get_text(st.session_state['language'], key, **kwargs)

# ---------- 工具函数 ----------

@st.cache_data
def load_summary(file_mtime: float = 0):
    """加载策略评测报告 (参数 file_mtime 用于缓存刷新)"""
    file_path = Path("results/策略评测报告_汇总.csv")
    if file_path.exists():
        return pd.read_csv(file_path)
    return pd.DataFrame()

def get_summary_with_refresh():
    """获取策略报告，自动根据文件修改时间刷新缓存"""
    file_path = Path("results/策略评测报告_汇总.csv")
    mtime = file_path.stat().st_mtime if file_path.exists() else 0
    return load_summary(mtime)

@st.cache_data
def get_index_stats(code):
    """获取指数统计信息 (Sharpe, WR, Score)"""
    try:
        p = Path(f"data_parquet/{code}.parquet")
        if p.exists():
            df = pd.read_parquet(p, columns=['date', 'close'])
            df['pct_change'] = df['close'].pct_change() * 100
            df = df.dropna()
            # 仅取最近1年
            min_d = df['date'].max() - timedelta(days=365)
            df = df[df['date'] >= min_d]
            
            if df.empty: return None
            
            ret_mean = df['pct_change'].mean()
            ret_std = df['pct_change'].std()
            win_rate = (df['pct_change'] > 0).sum() / len(df)
            
            sharpe = ret_mean / ret_std if ret_std > 0 else 0
            score = sharpe * win_rate
            
            return {
                "sharpe": sharpe,
                "win_rate": win_rate * 100,
                "score": score
            }
    except:
        return None

def get_logs_dates():
    """获取 logs/ 目录下所有的日志日期"""
    files = list(Path("logs").glob("*选股.csv"))
    dates = []
    for f in files:
        # 2026-01-20选股.csv -> 2026-01-20
        d_str = f.stem.replace("选股", "")
        try:
            dates.append(datetime.strptime(d_str, "%Y-%m-%d").date())
        except ValueError:
            pass
    dates.sort(reverse=True)
    return dates

def is_trading_day(date_str: str) -> bool:
    """检查某日是否为交易日 (优先使用 Parquet，回退到 CSV)"""
    parquet_dir = Path("data_parquet")
    data_dir = Path("data")
    
    # 抽样检查几只大盘股的数据
    sample_stocks = ["000001", "600000", "000002"]
    
    for code in sample_stocks:
        # 优先检查 Parquet
        parquet_path = parquet_dir / f"{code}.parquet"
        if parquet_path.exists():
            try:
                df = pd.read_parquet(parquet_path, columns=['date'])
                if date_str in df['date'].astype(str).values:
                    return True
            except Exception:
                pass
        
        # 回退到 CSV
        csv_path = data_dir / f"{code}.csv"
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path, usecols=['date'])
                if date_str in df['date'].values:
                    return True
            except Exception:
                continue
    
    return False

def load_daily_result_by_date(d: date):
    """加载指定日期的回测结果 (优先找CSV，没有则尝试实时回测)"""
    date_str = d.strftime("%Y-%m-%d")
    csv_path = Path(f"results/回测结果_{date_str}.csv")
    
    if csv_path.exists():
        return pd.read_csv(csv_path)
    
    # 如果 CSV 不存在但有 Log，说明可能还没回测，尝试自动回测
    log_path = Path(f"logs/{date_str}选股.csv")
    if log_path.exists():
        try:
            # 自动触发回测
            subprocess.run([sys.executable, "scripts/backtest.py", str(log_path)], check=True)
            if csv_path.exists():
                return pd.read_csv(csv_path)
        except Exception:
            pass
            
    return pd.DataFrame()

def get_activity_data():
    """获取每日选股数量统计 (从 logs/ 读取选股 CSV)"""
    data = []
    logs_dir = Path("logs")
    if logs_dir.exists():
        for f in logs_dir.glob("*选股.csv"):
            try:
                # 2026-01-20选股.csv -> 2026-01-20
                date_str = f.stem.replace("选股", "")
                
                # CSV 文件行数 = 股票数 + 1 (表头)
                with open(f, 'rb') as fp:
                    count = sum(1 for _ in fp) - 1
                if count < 0:
                    count = 0
                
                data.append({
                    'date': pd.to_datetime(date_str).date(),
                    'count': count
                })
            except Exception:
                pass
    
    if not data:
        return pd.DataFrame(columns=['date', 'count'])
        
    df = pd.DataFrame(data)
    df = df.sort_values('date')
    return df

def plot_activity_heatmap(df):
    """绘制 GitHub 风格的日历热力图 (High Fidelity Replica)"""
    if df.empty:
        return None
        
    # GitHub Color Palette (Light Mode)
    # 0: Gray, 1: Light Green, 2: Medium Green, 3: Dark Green, 4: Darkest Green
    colors = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39']
    
    # Range configuration
    max_days = 365 # 1 year view
    end_date = date.today()
    start_date = end_date - timedelta(days=364) # Ensure full year relative to today
    
    # Align start_date to the previous Sunday (GitHub style columns start on Sunday)
    # But for Mon start logic:
    # Let's stick to Mon start for simplicity or adjust to Sun. GitHub is Sun-Sat. 
    # Let's use Mon-Sun (0-6) which is standard ISO.
    weekday_start = 0 # Monday
    
    start_date = start_date - timedelta(days=(start_date.weekday() - weekday_start) % 7)
    
    all_dates = pd.date_range(start_date, end_date, freq='D').date
    grid_df = pd.DataFrame({'date': all_dates})
    grid_df = grid_df.merge(df, on='date', how='left').fillna(0)
    
    # Binning counts into levels 0-4
    # Calculate quantiles for non-zero counts
    non_zero_counts = grid_df[grid_df['count'] > 0]['count']
    if not non_zero_counts.empty:
        q1 = non_zero_counts.quantile(0.25)
        q2 = non_zero_counts.quantile(0.50)
        q3 = non_zero_counts.quantile(0.75)
    else:
        q1, q2, q3 = 1, 2, 3 # Default if no data
        
    def get_level(c):
        if c == 0: return 0
        if c <= q1: return 1
        if c <= q2: return 2
        if c <= q3: return 3
        return 4
        
    grid_df['level'] = grid_df['count'].apply(get_level)
    grid_df['color'] = grid_df['level'].apply(lambda x: colors[x])
    
    # Calculate coordinates
    # X: Week number from start
    # Y: Day of week (0=Mon, 6=Sun) -> Invert for plot (0 at top)
    grid_df['week'] = grid_df.apply(lambda x: (x['date'] - start_date).days // 7, axis=1)
    grid_df['day'] = grid_df['date'].apply(lambda x: x.weekday())
    
    # Tooltip
    grid_df['text'] = grid_df.apply(lambda x: f"<b>{x['count']:.0f} stocks</b><br>{x['date'].strftime('%Y-%m-%d')}", axis=1)
    
    # Fixed size layout
    # Approx 53 weeks. Cell size ~12px + 3px gap.
    cell_size = 12
    gap = 2
    
    fig = go.Figure()
    
    fig.add_trace(go.Heatmap(
        z=grid_df['level'],
        x=grid_df['week'],
        y=grid_df['day'],
        colorscale=[
            [0.0, colors[0]], [0.2, colors[0]],
            [0.2, colors[1]], [0.4, colors[1]],
            [0.4, colors[2]], [0.6, colors[2]],
            [0.6, colors[3]], [0.8, colors[3]],
            [0.8, colors[4]], [1.0, colors[4]],
        ],
        showscale=False,
        xgap=gap,
        ygap=gap,
        hovertext=grid_df['text'],
        hoverinfo='text',
        zmin=0,
        zmax=4
    ))
    
    # Month Labels logic
    month_labels = []
    current_month = -1
    for d in all_dates:
        if d.weekday() == 0 and d.month != current_month: # First monday of new month roughly
            # Calculate simple approximate week x
            w = (d - start_date).days // 7
            month_labels.append(dict(
                x=w, y=-1, text=d.strftime('%b'), showarrow=False,
                xanchor='left', yanchor='bottom', font=dict(size=10, color='#767676')
            ))
            current_month = d.month
            
    fig.update_layout(
        height=160, # Compact height
        width=800,  # Fixed width to prevent stretching
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(
            showticklabels=False, 
            showgrid=False, 
            zeroline=False, 
            fixedrange=True,
            range=[-0.5, 53]
        ),
        yaxis=dict(
            tickmode='array',
            ticktext=['Mon', '', 'Wed', '', 'Fri', '', ''],
            tickvals=[0, 1, 2, 3, 4, 5, 6],
            showgrid=False, 
            zeroline=False, 
            autorange="reversed",
            fixedrange=True,
            tickfont=dict(size=10, color='#767676')
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        annotations=month_labels
    )
    
    return fig

def save_token(token):
    """保存 Token 到 .env"""
    env_path = Path(".env")
    lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            lines = f.readlines()
    
    # 移除旧的 TUSHARE_TOKEN
    lines = [l for l in lines if not l.startswith("TUSHARE_TOKEN=")]
    lines.append(f"TUSHARE_TOKEN={token}\n")
    
    with open(env_path, "w") as f:
        f.writelines(lines)
    
    # 立即生效
    os.environ["TUSHARE_TOKEN"] = token

def run_process_with_progress(cmd, log_container=None, progress_bar=None, status_text=None):
    """运行子进程并实时解析进度"""
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    full_output = []
    
    for line in process.stdout:
        full_output.append(line)
        line_clean = line.strip()
        
        # 解析进度 [LOAD] 100/5000 或 [PROCESS] 50/5000
        if line_clean.startswith("[LOAD]") or line_clean.startswith("[PROCESS]"):
            try:
                parts = line_clean.split("]")[1].strip().split("/")
                current = int(parts[0])
                total = int(parts[1])
                
                if progress_bar and total > 0:
                    progress_bar.progress(min(current / total, 1.0))
                
                if status_text:
                    phase = "Loading Data" if "LOAD" in line_clean else "Processing Stocks"
                    status_text.text(f"{phase}... {current}/{total}")
            except Exception:
                pass
        
    process.wait()
    return "".join(full_output), process.returncode

# ---------- 侧边栏 ----------

# 简化的语言切换
if st.sidebar.button("🇨🇳 / 🇺🇸", key="lang_toggle"):
    st.session_state['language'] = 'EN' if st.session_state['language'] == 'CN' else 'CN'
    st.rerun()

st.sidebar.markdown("### NAVIGATION")

page = st.sidebar.radio(
    "Go to", 
    ["DASHBOARD", "LABORATORY", "SIMULATION", "BACKTEST", "SETTINGS"], 
    format_func=lambda x: T(f'nav_{x.lower()}'),
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("**STATUS**")
token_set = os.environ.get("TUSHARE_TOKEN") or (
    "TUSHARE_TOKEN" in open(".env").read() if Path(".env").exists() else False
)

if token_set:
    st.sidebar.success(T('status_active'))
else:
    st.sidebar.error(T('status_missing'))

# ---------- 页面逻辑 ----------

if page == "DASHBOARD":
    swiss_header(T('dash_title'), T('dash_subtitle'))
    
    summary_df = get_summary_with_refresh()
    
    hs300 = get_index_stats('000300')
    zz1000 = get_index_stats('000852')
    
    if summary_df.empty:
        st.info(T('dash_no_data'))
    else:
        # 1. KPI
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(T('kpi_stocks'), f"{summary_df['总荐股数'].sum()}")
        col2.metric(T('kpi_strategies'), f"{len(summary_df)}")
        col3.metric(T('kpi_score'), f"{summary_df.iloc[0]['综合得分']:.1f}")
        col4.metric(T('kpi_days'), f"{len(get_logs_dates())}")
        
        st.markdown("---")
        
        # 0. 市场指数走势
        st.markdown(f"##### {'市场大盘走势' if st.session_state['language'] == 'CN' else 'Market Index Trend'}")
        
        @st.cache_data
        def load_index_data():
            indices = {
                '000300': '沪深300 (CSI300)',
                '000852': '中证1000 (CSI1000)'
            }
            dfs = []
            for code, name in indices.items():
                p = Path(f"data_parquet/{code}.parquet")
                if p.exists():
                    try:
                        df = pd.read_parquet(p, columns=['date', 'close'])
                        df['date'] = pd.to_datetime(df['date'])
                        df['name'] = name
                        df = df.sort_values('date')
                        # 仅保留最近1年
                        min_d = df['date'].max() - timedelta(days=365)
                        df = df[df['date'] >= min_d].copy()
                        
                        if not df.empty:
                            first_close = df.iloc[0]['close']
                            df['pct_change'] = (df['close'] - first_close) / first_close * 100
                            dfs.append(df)
                    except:
                        pass
            if dfs:
                return pd.concat(dfs, ignore_index=True)
            return pd.DataFrame()

        index_df = load_index_data()
        if not index_df.empty:
            fig_idx = px.line(index_df, x='date', y='pct_change', color='name', labels={'pct_change': '涨跌幅 (%)', 'date': '日期'}, height=300)
            fig_idx.update_layout(
                margin=dict(l=0, r=0, t=30, b=0),
                legend=dict(orientation="h", y=1.05, yanchor="bottom", x=0, xanchor="left"),
                hovermode="x unified",
                title="",
                plot_bgcolor="white",
                paper_bgcolor="white"
            )
            fig_idx.update_xaxes(showgrid=True, gridcolor='#eee')
            fig_idx.update_yaxes(showgrid=True, gridcolor='#eee', zeroline=True, zerolinecolor='black')
            st.plotly_chart(fig_idx, use_container_width=True)
        else:
            st.caption("暂无指数数据，请在终端运行: `python scripts/fetch_kline.py --index`")

        st.markdown("---")
        
        # Activity Map
        st.markdown(f"##### {T('activity_map')}")
        st.caption(T('activity_help'))
        
        activity_df = get_activity_data()
        fig_map = plot_activity_heatmap(activity_df)
        if fig_map:
            st.plotly_chart(fig_map, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown(f"### {T('chart_title')}")
        
        # 2. Chart
        try:
            fig = px.scatter(
                summary_df,
                x="收盘_胜率%", y="收盘_5日均%", size="总荐股数", color="策略",
                hover_name="策略", hover_data=["最佳周期", "最佳均收"],
                height=500, color_discrete_sequence=px.colors.qualitative.Dark24
            )
            fig.update_layout(title="", plot_bgcolor="white", paper_bgcolor="white", font_family="Inter")
            
            # 坐标轴优化
            min_win = max(40, summary_df['收盘_胜率%'].min() - 5)
            min_ret = min(0, summary_df['收盘_5日均%'].min() - 1)
            max_ret = summary_df['收盘_5日均%'].max() + 1
            
            fig.update_xaxes(range=[40, 105], title="胜率 (%)", showgrid=True, gridcolor='#eee', zeroline=True, zerolinecolor='black')
            fig.update_yaxes(range=[min_ret, max_ret] if min_ret < 0 else [0, max_ret], title="5日均收益 (%)", showgrid=True, gridcolor='#eee', zeroline=True, zerolinecolor='black')
            
            fig.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
            fig.add_hline(y=0, line_dash="solid", line_color="black", opacity=0.1)
            
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.error(T('chart_missing_mpl'))
            
        # 3. Table
        st.markdown(f"### {T('table_title')}")
        column_config = {
            "策略": st.column_config.TextColumn("策略名称" if st.session_state['language'] == 'CN' else "Strategy", help="选股策略组合名称"),
            "总荐股数": st.column_config.NumberColumn("样本数" if st.session_state['language'] == 'CN' else "Samples", help="该策略在回测期间总共推荐的股票数量", format="%d"),
            "收盘_5日均%": st.column_config.NumberColumn("5日收益%" if st.session_state['language'] == 'CN' else "5D Ret%", help="以收盘价买入，持有5日后的平均收益率", format="%.2f%%"),
            "开盘_5日均%": st.column_config.NumberColumn("5日收益%(开)" if st.session_state['language'] == 'CN' else "5D Ret%(O)", help="以次日开盘价买入，持有5日后的平均收益率", format="%.2f%%"),
            "收盘收益_1日(%)_mean": st.column_config.NumberColumn("1日%" if st.session_state['language'] == 'CN' else "1D%", format="%.2f%%"),
            "收盘收益_2日(%)_mean": st.column_config.NumberColumn("2日%" if st.session_state['language'] == 'CN' else "2D%", format="%.2f%%"),
            "收盘收益_3日(%)_mean": st.column_config.NumberColumn("3日%" if st.session_state['language'] == 'CN' else "3D%", format="%.2f%%"),
            "收盘收益_5日(%)_mean": st.column_config.NumberColumn("5日%" if st.session_state['language'] == 'CN' else "5D%", format="%.2f%%"),
            "收盘收益_10日(%)_mean": st.column_config.NumberColumn("10日%" if st.session_state['language'] == 'CN' else "10D%", format="%.2f%%"),
            "最佳周期": st.column_config.TextColumn("最佳持仓" if st.session_state['language'] == 'CN' else "Best Hold", help="收益最高的持有天数"),
            "最佳均收": st.column_config.NumberColumn("最佳收益%" if st.session_state['language'] == 'CN' else "Best Ret%", format="%.2f%%"),
            "周期详情": st.column_config.TextColumn("各周期收益" if st.session_state['language'] == 'CN' else "Period Details", width="large"),
            "收盘_胜率%": st.column_config.NumberColumn("胜率%" if st.session_state['language'] == 'CN' else "Win Rate%", format="%.1f%%"),
            "收益标准差": st.column_config.NumberColumn("波动率(σ)" if st.session_state['language'] == 'CN' else "Volatility(σ)", help="收益率的标准差", format="%.2f"),
            "夏普比率": st.column_config.NumberColumn("夏普比率" if st.session_state['language'] == 'CN' else "Sharpe Ratio", help="平均收益 ÷ 标准差", format="%.2f"),
            "综合得分": st.column_config.NumberColumn("综合评分" if st.session_state['language'] == 'CN' else "Score", help="夏普比率 × 胜率调整因子", format="%.2f"),
        }
        st.dataframe(summary_df, use_container_width=True, column_config=column_config, hide_index=True)
        
        # 4. Distribution Chart
        st.markdown("---")
        st.markdown(f"### {'策略收益分布' if st.session_state['language'] == 'CN' else 'Return Distribution'}")
        
        @st.cache_data
        def load_all_backtest_results():
            results_dir = Path("results")
            all_dfs = []
            for f in results_dir.glob("回测结果_*.csv"):
                try:
                    df = pd.read_csv(f)
                    all_dfs.append(df)
                except: pass
            return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
        
        all_results = load_all_backtest_results()
        if not all_results.empty and '策略' in all_results.columns:
            strategies = all_results['策略'].unique().tolist()
            selected_strategy = st.selectbox("选择策略" if st.session_state['language'] == 'CN' else "Select Strategy", strategies, index=0)
            
            if selected_strategy:
                strat_data = all_results[all_results['策略'] == selected_strategy]
                ret_col = '收盘买入收益率(%)'
                if ret_col in strat_data.columns:
                    returns = strat_data[ret_col].dropna()
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("样本数", f"{len(returns)}")
                    col2.metric("均值", f"{returns.mean():.2f}%")
                    col3.metric("标准差", f"{returns.std():.2f}")
                    col4.metric("夏普", f"{returns.mean() / returns.std():.2f}" if returns.std() > 0 else "N/A")
                    
                    fig = px.histogram(returns, nbins=30, title=f"{selected_strategy} - 5日收益分布", labels={'value': '收益率(%)', 'count': '频数'}, color_discrete_sequence=['#4CAF50'])
                    fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="零线")
                    fig.add_vline(x=returns.mean(), line_dash="dot", line_color="blue", annotation_text=f"均值:{returns.mean():.1f}%")
                    fig.update_layout(showlegend=False, height=350, plot_bgcolor="white", paper_bgcolor="white")
                    st.plotly_chart(fig, use_container_width=True)

        # 5. Scoring Formula
        st.markdown("---")
        with st.expander(T('score_formula_title'), expanded=False):
            st.markdown(T('score_formula_desc'))
            st.latex(r'''Score = Sharpe \times \frac{WinRate\%}{100} = \frac{AvgReturn}{StdDev} \times \frac{WinCount}{TotalCount}''')
            st.info("注：由于夏普比率本身数值较小（通常在0-3之间），综合评分通常小于1。评分越高越好。")
            if hs300 and zz1000:
                st.markdown("**从最近一年起的基准表现 (Benchmark):**")
                b1, b2 = st.columns(2)
                b1.metric("沪深300 (CSI300)", f"Score: {hs300['score']:.4f}", f"Sharpe: {hs300['sharpe']:.2f} | WR: {hs300['win_rate']:.1f}%")
                b2.metric("中证1000 (CSI1000)", f"Score: {zz1000['score']:.4f}", f"Sharpe: {zz1000['sharpe']:.2f} | WR: {zz1000['win_rate']:.1f}%")

elif page == "LABORATORY":
    swiss_header(T('lab_title'), T('lab_subtitle'))
    
    tab1, tab2 = st.tabs([T('tab_daily'), T('tab_exec')])
    
    with tab1:
        st.markdown(f"##### {T('sel_date')}")
        available_dates = get_logs_dates()
        
        default_date = available_dates[0] if available_dates else date.today()
        
        # 使用日历控件
        selected_date = st.date_input("Calendar", value=default_date, label_visibility="collapsed")
        
        daily_df = load_daily_result_by_date(selected_date)
        
        if daily_df.empty:
            st.info(T('no_data_date', date=selected_date))
        else:
            # 1. 自动识别代码列并补全
            code_col = None
            if 'code' in daily_df.columns:
                code_col = 'code'
            elif 'symbol' in daily_df.columns:
                code_col = 'symbol'
            elif 'ts_code' in daily_df.columns:
                daily_df['code'] = daily_df['ts_code'].astype(str).str.split('.').str[0]
                code_col = 'code'
            
            if code_col:
                daily_df[code_col] = daily_df[code_col].astype(str).str.zfill(6)

            rec_count = len(daily_df)
            # 尝试获取平均收益列
            ret_col = [c for c in daily_df.columns if '收盘收益' in c or '收盘买入' in c][-1]
            avg_ret = daily_df[ret_col].mean() if not daily_df.empty else 0
            
            c1, c2 = st.columns(2)
            c1.metric(T('metric_selected'), f"{rec_count}")
            c2.metric(T('metric_avg_ret'), f"{avg_ret:.2f}%")
            
            st.markdown(f"##### {T('section_details')}")
            
            # 强制将代码列显示为纯文本，避免被识别为数字去掉前导0
            # 自动调整列宽: use_container_width=True
            column_config = {}
            if code_col:
                column_config[code_col] = st.column_config.TextColumn("Code", width="medium")
                
            st.dataframe(
                daily_df, 
                use_container_width=True, 
                height=600,
                column_config=column_config
            )

    with tab2:
        st.markdown(f"##### {T('run_title')}")
        
        col_type, col_params = st.columns([1, 3])
        run_mode = col_type.radio("Mode", ["SINGLE DATE", "BATCH RANGE"], label_visibility="collapsed")
        
        if run_mode == "SINGLE DATE":
            exec_date = col_params.date_input(T('run_single_date'), value=date.today())
            
            if st.button(T('btn_run_single')):
                log_container = st.empty()
                try:
                    log_container.code(T('log_running', date=exec_date))
                    
                    # 使用进度条运行
                    prog_bar = st.progress(0)
                    status_txt = st.empty()
                    
                    cmd_select = [sys.executable, "scripts/select_stock.py", "--date", str(exec_date)]
                    output, ret_code = run_process_with_progress(cmd_select, progress_bar=prog_bar, status_text=status_txt)
                    
                    if ret_code == 0:
                        prog_bar.empty()
                        status_txt.empty()
                        st.success(T('success_select'))
                        
                        log_path = f"logs/{exec_date}选股.csv"
                        subprocess.run([sys.executable, "scripts/backtest.py", log_path], capture_output=True)
                        
                        st.success(T('success_finish'))
                        subprocess.run([sys.executable, "scripts/analyze_results.py"], check=False)
                    else:
                        st.error("Select failed")
                        log_container.code(output)
                except Exception as e:
                    st.error(f"{T('error_failed')} {e}")
                    
        else: # BATCH RANGE
            c1, c2 = col_params.columns(2)
            start_d = c1.date_input(T('run_start_date'), value=date.today() - timedelta(days=7))
            end_d = c2.date_input(T('run_end_date'), value=date.today())
            skip_exist = col_params.checkbox(T('run_skip_existing'), value=True)
            
            # 并行度控制
            parallel_degree = col_params.slider(
                "⚡ " + ("Parallel Degree" if st.session_state.get('lang') == 'en' else "并行度"),
                min_value=1, max_value=6, value=2,
                help="Number of dates to process simultaneously. Higher = faster but more resource usage."
            )
            
            if st.button(T('btn_run_batch')):
                progress_bar = st.progress(0)
                status_text = st.empty()
                log_box = st.expander("Execution Log", expanded=True)
                
                # 使用 batch_run.py 进行并行处理
                start_str = str(start_d)
                end_str = str(end_d)
                
                log_box.write(f"🚀 Starting parallel batch: {start_str} → {end_str} (parallel={parallel_degree})")
                
                cmd = [
                    sys.executable, "scripts/batch_run.py",
                    "--start", start_str,
                    "--end", end_str,
                    "--parallel", str(parallel_degree)
                ]
                if skip_exist:
                    cmd.append("--skip")
                
                # 运行批量脚本并实时读取输出
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                total_days_estimate = (end_d - start_d).days + 1
                completed = 0
                
                for line in process.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 解析进度
                    if line.startswith("[") and "%]" in line:
                        try:
                            pct = int(line.split("%]")[0].replace("[", "").strip())
                            progress_bar.progress(pct / 100)
                            completed += 1
                        except:
                            pass
                        log_box.write(line)
                    elif "===" in line or "找到" in line:
                        log_box.write(f"**{line}**")
                    else:
                        log_box.write(line)
                
                process.wait()
                progress_bar.progress(1.0)
                
                if process.returncode == 0:
                    st.success("✅ Batch processing complete!")
                    st.balloons()
                else:
                    st.error("❌ Batch processing failed")


elif page == "SIMULATION":
    swiss_header(T('sim_title'), T('sim_subtitle'))
    
    # 1. Settings
    with st.container():
        st.markdown(f"##### {T('sim_settings')}")
        c1, c2, c3 = st.columns(3)
        init_capital = c1.number_input(T('sim_capital'), value=1000000, step=100000)
        hold_period = c2.number_input(T('sim_period'), value=10, min_value=1)
        
        # Get strategies from logs or summary
        summary_df = get_summary_with_refresh()
        strategies = summary_df['策略'].unique().tolist() if not summary_df.empty else []
        target_strat = c3.selectbox(T('sim_strategy'), strategies)
        
        # Date Range Selection
        available_dates = get_logs_dates()
        min_date = available_dates[0] if available_dates else date.today()
        max_date = date.today()
        
        c4, c5 = st.columns(2)
        start_date_input = c4.date_input("Start Date", value=min_date, min_value=date(2020, 1, 1), max_value=max_date)
        end_date_input = c5.date_input("End Date", value=max_date, min_value=date(2020, 1, 1), max_value=max_date)

    if st.button(T('sim_run'), type="primary", disabled=not strategies):
        # 2. Simulation Logic
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        status_text.text("Loading logs...")
        
        # A. Load all relevant logs
        logs_dir = Path("logs")
        log_files = sorted(list(logs_dir.glob("*选股.csv")))
        
        signals = {} # Date -> [Codes]
        
        for f in log_files:
            try:
                date_str = f.stem.replace("选股", "") # YYYY-MM-DD
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                # Filter by date range
                if d < start_date_input or d > end_date_input:
                    continue
                
                df_log = pd.read_csv(f, dtype=str, encoding='utf-8-sig') # Handle BOM
                
                # Map Chinese columns
                col_map = {
                    '代码': 'code',
                    'symbol': 'code',
                    'ts_code': 'code',
                    '策略': 'strategies',
                    'strategy': 'strategies'
                }
                df_log = df_log.rename(columns=col_map)
                
                # Normalize code
                if 'code' in df_log.columns:
                     # Remove .SZ/.SH if present
                    df_log['code'] = df_log['code'].astype(str).str.split('.').str[0].str.zfill(6)
                
                if 'code' in df_log.columns and 'strategies' in df_log.columns:
                    # Filter for strategy
                    df_strat = df_log[df_log['strategies'].astype(str).str.contains(target_strat, regex=False)]
                    codes = df_strat['code'].tolist()
                    if codes:
                        signals[d] = codes
            except Exception as e:
                pass
        
        if not signals:
            st.warning(T('sim_no_logs'))
        else:
            # Sort dates
            sorted_dates = sorted(signals.keys())
            # Use user selected range (though signals are already filtered, simulation timeline should match)
            start_date = start_date_input
            end_date = end_date_input
            
            status_text.text(f"Simulating range: {start_date} -> {end_date}")

            
            # Load Index for Benchmark (HS300)
            bm_df = pd.DataFrame()
            try:
                bm_df = pd.read_parquet("data_parquet/000300.parquet", columns=['date', 'open', 'close'])
                bm_df['date'] = pd.to_datetime(bm_df['date']).dt.date
                bm_df = bm_df.sort_values('date').set_index('date')
            except:
                pass

            # B. Portfolio Simulation
            # Rules:
            # - T: Generate Signal
            # - T+1: Buy at Open
            # - T+1+HoldDays: Sell at Close
            # - Allocation: Divide capital into (HoldDays + 2) parts to ensure liquidity
            
            cash = init_capital
            positions = {} # Code -> {shares, cost, buy_date}
            total_assets = [] # [{date, value}]
            
            # Create full timeline
            timeline = pd.date_range(start_date, end_date, freq='B').date
            
            # Cache stock data to avoid repeated reads
            stock_cache = {}
            
            def get_stock_price(code, d):
                if code not in stock_cache:
                    p = Path(f"data_parquet/{code}.parquet")
                    if p.exists():
                        try:
                            df = pd.read_parquet(p, columns=['date', 'open', 'close'])
                            df['date'] = pd.to_datetime(df['date']).dt.date
                            stock_cache[code] = df.set_index('date')
                        except:
                            stock_cache[code] = pd.DataFrame()
                    else:
                        stock_cache[code] = pd.DataFrame()
                
                df = stock_cache[code]
                if d in df.index:
                    return df.loc[d]
                return None

            allocation_per_slot = init_capital / (hold_period * 1.5) # Conservative allocation
            
            for i, today in enumerate(timeline):
                progress_bar.progress(min(i / len(timeline), 1.0))
                status_text.text(f"Processing {today}...")
                
                # 1. Update Positions & Check Sell
                current_pos_val = 0
                to_remove = []
                
                for code, pos in positions.items():
                    price_data = get_stock_price(code, today)
                    
                    if price_data is not None:
                        current_price = price_data['close']
                        days_held = (today - pos['buy_date']).days
                        # Wait, trading days diff would be better, but simple days is ok for sim
                        
                        # Sell Logic
                        if days_held >= hold_period:
                            # Sell at Close
                            cash += pos['shares'] * current_price
                            to_remove.append(code)
                        else:
                            current_pos_val += pos['shares'] * current_price
                    else:
                        # No data today (suspended?), keep last value (approx) or 0? 
                        # Use cost as proxy if suspended
                        current_pos_val += pos['shares'] * pos['cost'] # Simplified
                
                for c in to_remove:
                    del positions[c]
                    
                # 2. Check Buy (Signals from T-1? Or T? user said "Next day open")
                # So if signal is on T-1 (yesterday), we buy Today Open
                
                # Get signals from Yesterday (or previous trading day in logs)
                # Since 'signals' dict uses log date (which is usually signal date),
                # We need to find if there was a signal yesterday?
                # Actually, iterate days. If 'today' is T, we check signals from T-1.
                # But timeline is business days.
                
                # Simplified: Loop through past dates in signals that match (today - 1_day)?
                # Or just check if today is a trading day and buy based on "pending signals".
                
                # Let's say: Signal produced on Date X. Execution on Date X+1 (if trading day).
                prev_day = today - timedelta(days=1)
                # Find closest signal date <= prev_day? 
                # Actually, simplest is: Check if (today - 1) in signals?
                # But weekends exist.
                
                # Better approach: Iterate signals. If signal_date == prev_trading_day -> Buy Today.
                # However, we are iterating days.
                
                # Let's check if there are signals with date < today that haven't been processed?
                # No, just check specific previous day is tricky.
                # Let's look up signals for (today - gap).
                # But gap varies.
                
                # Workaround: Check signals for yesterday, day before yesterday... up to 5 days?
                # Only if not bought yet.
                # Actually, strict T+1 means: if Signal on Fri, Buy on Mon.
                
                # Let's try: Check signals[today] -> Queue for purchase Next Day?
                # Yes.
                # But this loop is "Today". So we check "Queue".
                
                pass 
                
            # Re-implement loop with Queue
            cash = init_capital
            positions = {}
            queue = [] # (code, signal_date)
            
            history_equity = []
            
            # Align timeline with signals
            # Merge signals keys into timeline to ensure we cover all signal days
            all_days = sorted(list(set(list(timeline) + list(signals.keys()))))
            start_idx = 0
            # Find start index
            for idx, d in enumerate(all_days):
                if d >= start_date:
                    start_idx = idx
                    break
            
            sim_dates = all_days[start_idx:]
            
            for i, today in enumerate(sim_dates):
                progress_bar.progress(min(i / len(sim_dates), 1.0))
                
                # 1. Process Buy Queue (from previous signal)
                new_queue = []
                for code in queue:
                    # Try buy at Open
                    price_data = get_stock_price(code, today)
                    if price_data is not None:
                        open_price = price_data['open']
                        if open_price > 0 and cash > allocation_per_slot:
                            # Buy
                            shares = int(allocation_per_slot / open_price / 100) * 100
                            if shares > 0:
                                cost = shares * open_price
                                cash -= cost
                                positions[code] = {'shares': shares, 'cost': open_price, 'buy_date': today, 'last_price': open_price}
                    else:
                        # Keep in queue for next day? Or discard?
                        # Usually discard if not actionable immediately to avoid piling up
                        pass
                queue = [] # Clear queue, unprocessed are dropped (strict timing)
                
                # 2. Update Position Values & Check Sell
                pos_val = 0
                to_sell = []
                for code, pos in positions.items():
                    price_data = get_stock_price(code, today)
                    price = pos['last_price']
                    
                    if price_data is not None:
                        price = price_data['close']
                        positions[code]['last_price'] = price
                        
                        # Check exit
                        # Hold period check (Trading days vs Calendar days?)
                        # User said "Hold 10 days". Usually calendar days or N trading bars.
                        # Let's use Calendar days for simplicity.
                        if (today - pos['buy_date']).days >= hold_period:
                            to_sell.append(code)
                    
                    pos_val += pos['shares'] * price
                
                # Process Sells
                for code in to_sell:
                    # Sell at Close price of today
                    p = positions[code]
                    cash += p['shares'] * p['last_price']
                    # Remove from pos_val (it's now cash)
                    pos_val -= p['shares'] * p['last_price']
                    del positions[code]
                
                total_equity = cash + pos_val
                
                # Benchmark return
                bm_ret = 0
                if not bm_df.empty and today in bm_df.index:
                    # Relative to start
                    # Look up start price?
                    pass 
                
                history_equity.append({'date': today, 'equity': total_equity})
                
                # 3. Add Today's Signals to Queue (for tomorrow)
                if today in signals:
                    for code in signals[today]:
                        # Avoid buying if already held
                        if code not in positions:
                            queue.append(code)
            
            # C. Visualisation
            res_df = pd.DataFrame(history_equity)
            if not res_df.empty:
                res_df['date'] = pd.to_datetime(res_df['date'])
                
                # Calculate metrics
                final_equity = res_df.iloc[-1]['equity']
                total_ret_pct = (final_equity - init_capital) / init_capital * 100
                res_df['dd'] = (res_df['equity'].cummax() - res_df['equity']) / res_df['equity'].cummax() * 100
                max_dd = res_df['dd'].max()
                
                st.markdown(f"### {T('sim_result')}")
                m1, m2, m3 = st.columns(3)
                m1.metric(T('sim_final_asset'), f"¥{final_equity:,.0f}")
                m2.metric(T('sim_total_ret'), f"{total_ret_pct:+.2f}%")
                m3.metric(T('sim_max_dd'), f"{max_dd:.2f}%", delta_color="inverse")
                
                st.markdown("#### 资金曲线 (Net Value)")
                # Add benchmark to chart
                chart_df = res_df[['date', 'equity']].copy()
                chart_df['Strategy'] = (chart_df['equity'] - init_capital) / init_capital * 100
                
                # HS300 Benchmark
                if not bm_df.empty:
                    # Align dates
                    bm_chart = bm_df.loc[res_df.iloc[0]['date'].date():res_df.iloc[-1]['date'].date()]
                    if not bm_chart.empty:
                        base_idx = bm_chart.iloc[0]['close']
                        # Map dates to chart_df
                        # We can merge
                        bm_series = bm_chart['close'].reindex(res_df['date'].dt.date).fillna(method='ffill')
                        chart_df['HS300'] = (bm_series.values - base_idx) / base_idx * 100
                
                fig = px.line(chart_df, x='date', y=['Strategy', 'HS300'] if 'HS300' in chart_df.columns else ['Strategy'])
                fig.update_layout(title="累计收益率 (%)", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.error("Simulation produced no data.")
                
        status_text.empty()
        progress_bar.empty()

elif page == "BACKTEST":
    swiss_header(T('bt_title'), T('bt_subtitle'))
    
    st.markdown(f"##### {T('bt_select_logs')}")
    
    # scan logs and results
    data = []
    log_dir = Path("logs")
    res_dir = Path("results")
    
    # 查找所有日期
    dates = get_logs_dates()
    
    for d in dates:
        d_str = str(d)
        log_p = log_dir / f"{d_str}选股.csv"
        res_p = res_dir / f"回测结果_{d_str}.csv"
        
        data.append({
            "date": d,
            "log": "✅" if log_p.exists() else "❌",
            "result": "✅" if res_p.exists() else "❌",
            # internal use
            "date_str": d_str,
            "log_path": str(log_p) if log_p.exists() else None,
            "has_log": log_p.exists()
        })
    
    if not data:
        st.info("No logs found.")
    else:
        df_status = pd.DataFrame(data)
        
        # 使用 DataEditor 让用户选择
        # 添加一个 'Select' 列
        df_status.insert(0, "select", False)

        # 全选未回测按钮
        # 必须使用 st.session_state 来更新 data_editor 的数据
        if "pending_select_updates" not in st.session_state:
            st.session_state["pending_select_updates"] = {}

        if st.button(T('bt_btn_select_pending')):
            # 找到所有没有回测结果（result == '❌'）且有日志的行
            mask = (df_status['result'] == '❌') & (df_status['has_log'])
            # 将这些行的 select 设为 True
            # 注意: st.data_editor 会重新加载 df_status，所以我们直接修改 df_status
            df_status.loc[mask, 'select'] = True
            st.success(f"Selected {mask.sum()} pending logs.")

        # 配置列显示
        edited_df = st.data_editor(
            df_status,
            column_config={
                "select": st.column_config.CheckboxColumn("Run", default=False),
                "date": st.column_config.DateColumn(T('bt_table_date'), disabled=True),
                "log": st.column_config.TextColumn(T('bt_table_log'), disabled=True),
                "result": st.column_config.TextColumn(T('bt_table_result'), disabled=True),
                # Hide internal columns
                "date_str": None,
                "log_path": None,
                "has_log": None
            },
            hide_index=True,
            use_container_width=True,
            height=400,
            key="bt_editor" # 给一个 key 以便可能的状态管理
        )
        
        # 提取选中的行
        selected_rows = edited_df[edited_df["select"] == True]
        
        if st.button(T('bt_btn_run'), type="primary", disabled=selected_rows.empty):
            count = len(selected_rows)
            st.info(f"Queueing {count} tasks...")
            
            prog_bar = st.progress(0)
            log_area = st.expander(T('bt_log_preview'), expanded=True)
            
            for i, row in enumerate(selected_rows.itertuples()):
                d_str = row.date_str
                log_path = row.log_path
                
                if not row.has_log:
                    log_area.warning(f"Skipping {d_str}: No log file.")
                    continue
                
                log_area.write(f"▶️ **Backtesting {d_str}...**")
                
                try:
                    cmd_bt = [sys.executable, "scripts/backtest.py", log_path]
                    ret = subprocess.run(cmd_bt, capture_output=True, text=True)
                    
                    if ret.returncode == 0:
                        log_area.code(ret.stdout)
                        log_area.success(f"✅ {d_str} Done")
                    else:
                        log_area.error(f"❌ {d_str} Failed")
                        log_area.code(ret.stderr)
                except Exception as e:
                    log_area.error(f"Error: {e}")
                
                prog_bar.progress((i + 1) / count)
                
            st.success(T('success_finish'))
            # 更新分析结果
            subprocess.run([sys.executable, "scripts/analyze_results.py"], check=False)


elif page == "SETTINGS":
    swiss_header(T('set_title'), T('set_subtitle'))
    
    st.markdown(f"##### {T('set_token_config')}")
    
    current_token = os.environ.get("TUSHARE_TOKEN", "")
    new_token = st.text_input(T('input_token'), value=current_token, type="password")
    
    if st.button(T('btn_save_token')):
        save_token(new_token)
        st.success(T('msg_token_saved'))
        
    st.markdown("---")
    st.markdown(f"##### {T('set_update_data')}")
    st.markdown(T('set_update_desc'))
    
    c1, c2 = st.columns(2)
    with c1:
        start_d = st.date_input(T('input_start'), value=date(2026, 1, 1))
    with c2:
        end_d = st.date_input(T('input_end'), value=date.today())
        
    st.markdown(f"**{T('set_workers')}**")
    workers_opt = st.radio(
        T('set_workers_help'),
        [1, 6],
        format_func=lambda x: T('set_workers_low') if x == 1 else T('set_workers_high')
    )
        
    if st.button(T('btn_fetch')):
        st.info(T('msg_fetch_start'))
        cmd_fetch = [
            sys.executable, "scripts/fetch_kline.py", 
            "--start", str(start_d), 
            "--end", str(end_d),
            "--workers", str(workers_opt),
            "--use-token" 
        ]
        
        try:
            subprocess.Popen(cmd_fetch) 
            st.success(T('msg_bg_start'))
        except Exception as e:
            st.error(T('err_start_fail', e=e))
