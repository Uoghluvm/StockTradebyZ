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
def load_summary():
    """加载策略评测报告"""
    file_path = Path("results/策略评测报告_汇总.csv")
    if file_path.exists():
        return pd.read_csv(file_path)
    return pd.DataFrame()

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
    """检查某日是否为交易日 (通过抽样检查 data/ 目录中的股票是否有该日数据)"""
    data_dir = Path("data")
    if not data_dir.exists():
        return True  # 如果没有数据目录，默认认为是交易日
    
    # 抽样检查几只大盘股的数据
    sample_stocks = ["000001.csv", "600000.csv", "000002.csv"]
    
    for stock_file in sample_stocks:
        csv_path = data_dir / stock_file
        if csv_path.exists():
            try:
                # 只读取 date 列以节省内存
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
    ["DASHBOARD", "LABORATORY", "BACKTEST", "SETTINGS"], 
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
    
    summary_df = load_summary()
    
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
                x="收盘_胜率%",
                y="收盘_5日均%",
                size="总荐股数",
                color="策略",
                hover_name="策略",
                hover_data=["最佳周期", "最佳均收"],
                height=500,
                color_discrete_sequence=px.colors.qualitative.Dark24
            )
            # Swiss Style Customization
            fig.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                font_family="Inter",
                title_font_family="Inter",
                title_font_size=20,
            )
            fig.update_xaxes(showgrid=True, gridcolor='#eee', zerolinecolor='black')
            fig.update_yaxes(showgrid=True, gridcolor='#eee', zerolinecolor='black')
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.error(T('chart_missing_mpl'))

        # 3. Table
        st.markdown(f"### {T('table_title')}")
        st.dataframe(summary_df, use_container_width=True)


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
            
            if st.button(T('btn_run_batch')):
                progress_bar = st.progress(0)
                status_text = st.empty()
                log_box = st.expander("Execution Log", expanded=True)
                
                # 生成日期序列
                delta = end_d - start_d
                date_list = [start_d + timedelta(days=i) for i in range(delta.days + 1)]
                total = len(date_list)
                
                for i, d in enumerate(date_list):
                    d_str = str(d)
                    
                    # 检查是否为交易日
                    if not is_trading_day(d_str):
                        log_box.write(f"📅 Skip {d_str} (Non-trading day)")
                        progress_bar.progress((i + 1) / total)
                        continue
                    
                    need_select = True
                    need_backtest = True
                    
                    # 检查已存在 (文件存在 且 非空)
                    log_p = Path(f"logs/{d_str}选股.csv")
                    res_p = Path(f"results/回测结果_{d_str}.csv")
                    
                    log_valid = log_p.exists() and log_p.stat().st_size > 0
                    res_valid = res_p.exists() and res_p.stat().st_size > 0
                    
                    if skip_exist:
                        if log_valid:
                            need_select = False
                            log_box.write(f"ℹ️ Skip Selection {d_str} (Log exists)")
                        
                        if res_valid:
                            need_backtest = False
                    
                    # 强制执行时，全部为 True
                    
                    # Run Selection
                    if need_select:
                        status_text.text(f"Selecting {d_str}...")
                        log_box.write(f"▶️ **Selecting {d_str}...**")
                        
                        single_prog = st.progress(0)
                        cmd_sel = [sys.executable, "scripts/select_stock.py", "--date", d_str]
                        out_sel, ret_sel = run_process_with_progress(cmd_sel, progress_bar=single_prog)
                        single_prog.empty()
                        
                        if ret_sel != 0:
                            log_box.error(f"❌ Selection Failed {d_str}")
                            need_backtest = False # 选股失败则无法回测
                        else:
                            log_box.success(f"✅ Selection Done {d_str}")
                            # 即使有日志输出，也未必需要在 batch 模式刷屏，除非出错
                    
                    # Run Backtest (Selection might have just finished, so check log again)
                    log_valid = log_p.exists() and log_p.stat().st_size > 0  # Re-check after selection
                    if need_backtest and log_valid:
                        # 如果需要回测 且 日志存在 (新生成或已存在)
                        log_box.write(f"▶️ **Backtesting {d_str}...**")
                        
                        # Use Popen to avoid blocking/buffering issues
                        cmd_bt = [sys.executable, "scripts/backtest.py", str(log_p)]
                        out_bt, ret_bt = run_process_with_progress(cmd_bt)
                        
                        if ret_bt == 0:
                            log_box.success(f"✅ Backtest Done {d_str}")
                            # Optional: Show output if verbose, but backtest output can be long.
                            # showing last few lines might be better, or just full output in code block
                            with st.expander(f"Details {d_str}", expanded=False):
                                st.code(out_bt)
                        else:
                            log_box.error(f"❌ Backtest Failed {d_str}")
                            log_box.code(out_bt)
                    elif need_backtest:
                         log_box.warning(f"⚠️ No log found for {d_str}, cannot backtest.")
                            
                    progress_bar.progress((i + 1) / total)
                    time.sleep(0.05)
                
                status_text.text("Batch processing complete!")
                st.success(T('success_finish'))
                subprocess.run([sys.executable, "scripts/analyze_results.py"], check=False)

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
