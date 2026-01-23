import streamlit as st

def inject_cyberpunk_style():
    """注入 Cyberpunk / Glitch 风格 CSS"""
    
    # 核心设计 Token
    # Background: #0a0a0f (Deep void)
    # Accent: #00ff88 (Matrix Green)
    # Secondary: #ff00ff (Magenta)
    # Text: #e0e0e0
    
    css = """
    <style>
        /* 引入 Google Fonts: Orbitron (Headers), JetBrains Mono (Body/Code) */
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');

        /* ---------- 全局变量 ---------- */
        :root {
            --bg-dark: #0a0a0f;
            --bg-card: #12121a;
            --text-main: #e0e0e0;
            --text-muted: #6b7280;
            --neon-green: #00ff88;
            --neon-pink: #ff00ff;
            --neon-blue: #00d4ff;
            --border-color: #2a2a3a;
        }

        /* ---------- 关键动画 ---------- */
        @keyframes scanline {
            0% { transform: translateY(-100%); }
            100% { transform: translateY(100vh); }
        }
        
        @keyframes glitch-skew {
            0% { transform: skew(0deg); }
            20% { transform: skew(-2deg); }
            40% { transform: skew(2deg); }
            60% { transform: skew(-1deg); }
            80% { transform: skew(1deg); }
            100% { transform: skew(0deg); }
        }

        @keyframes blink {
            50% { opacity: 0; }
        }

        /* ---------- 全局重置与背景 ---------- */
        html, body, [class*="css"] {
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-main);
            background-color: var(--bg-dark);
        }
        
        /* 移除 Streamlit 默认 header/footer */
        /* 隐藏 Header 背景但保留按钮 (如 Sidebar Toggle) */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            z-index: 999999;
        }
        
        /* 隐藏顶部彩虹条 */
        header[data-testid="stHeader"] > div:first-child {
            background: transparent !important;
        }

        /* 确保所有 Header 按钮 (汉堡菜单, Sidebar Toggle, Running Man) 可见并为霓虹色 */
        header[data-testid="stHeader"] button {
            color: var(--neon-green) !important;
            display: block !important;
        }
        
        /* 针对 Sidebar Toggle 的特定增强 (如果有特定 testid, 但通用 button 选择器通常足够) */
        button[data-testid="stSidebarCollapsedControl"] {
            color: var(--neon-green) !important;
            display: block !important;
        }
        footer { display: none; }
        
        /* App 背景: Void + Grid Pattern + Scanlines */
        .stApp {
            background-color: var(--bg-dark);
            background-image:
                linear-gradient(rgba(0, 255, 136, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 255, 136, 0.03) 1px, transparent 1px);
            background-size: 50px 50px;
        }
        
        /* Scanline Overlay (Reduced Opacity for Readability) */
        .stApp::after {
            content: " ";
            display: block;
            position: fixed;
            top: 0;
            left: 0;
            bottom: 0;
            right: 0;
            background: repeating-linear-gradient(
                0deg,
                transparent,
                transparent 2px,
                rgba(0, 0, 0, 0.1) 2px,
                rgba(0, 0, 0, 0.1) 4px
            );
            pointer-events: none;
            z-index: 9999;
            opacity: 0.3; /* Decreased from 0.6 */
        }

        /* ---------- 排版 ---------- */
        h1, h2, h3 {
            font-family: 'Orbitron', sans-serif !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--text-main);
        }
        
        h1 {
            font-size: 3rem !important;
            font-weight: 900 !important;
            text-shadow: 2px 2px 0px rgba(255, 0, 255, 0.4), -2px -2px 0px rgba(0, 255, 136, 0.4);
            border-bottom: 2px solid var(--neon-green);
            padding-bottom: 1rem;
            margin-bottom: 2rem;
            display: inline-block;
        }
        
        h2 {
            font-size: 1.8rem !important;
            color: var(--neon-green) !important;
            border-left: 4px solid var(--neon-pink);
            padding-left: 1rem;
            text-shadow: 0 0 10px rgba(0, 255, 136, 0.3);
            margin-top: 2rem;
        }
        
        h3 {
            font-size: 1.4rem !important;
            color: var(--neon-blue) !important;
        }

        p, label, span, div {
            font-family: 'JetBrains Mono', monospace;
        }

        /* ---------- 组件：按钮 ---------- */
        /* Chamfered Corners via clip-path */
        .stButton > button {
            background-color: transparent !important;
            border: 1px solid var(--neon-green) !important;
            color: var(--neon-green) !important;
            font-family: 'Share Tech Mono', monospace !important;
            text-transform: uppercase !important;
            letter-spacing: 2px !important;
            border-radius: 0px !important;
            padding: 0.6rem 2rem !important;
            position: relative;
            clip-path: polygon(
                0 10px, 10px 0, 
                100% 0, 100% calc(100% - 10px), 
                calc(100% - 10px) 100%, 0 100%
            );
            transition: all 0.2s ease !important;
            box-shadow: 0 0 5px rgba(0, 255, 136, 0.2) !important;
        }
        
        .stButton > button:hover {
            background-color: var(--neon-green) !important;
            color: #000 !important;
            box-shadow: 0 0 15px var(--neon-green) !important;
            text-shadow: none !important;
            transform: translateY(-2px);
        }

        /* Secondary Button (Standard Streamlit Secondary) -> Pink */
        .stButton > button[kind="secondary"] {
            border-color: var(--neon-pink) !important;
            color: var(--neon-pink) !important;
            box-shadow: 0 0 5px rgba(255, 0, 255, 0.2) !important;
        }
        
        .stButton > button[kind="secondary"]:hover {
            background-color: var(--neon-pink) !important;
            color: #000 !important;
            box-shadow: 0 0 15px var(--neon-pink) !important;
        }

        /* ---------- 组件：输入框 & 选择框 ---------- */
        .stTextInput > div > div > input,
        .stDateInput > div > div > input,
        .stSelectbox > div > div > div {
            background-color: var(--bg-card) !important;
            color: var(--neon-green) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 0px !important;
            font-family: 'JetBrains Mono', monospace !important;
            clip-path: polygon(0 0, 100% 0, 100% 100%, 10px 100%, 0 calc(100% - 5px));
        }
        
        /* Input Focus */
        .stTextInput > div > div > input:focus,
        .stDateInput > div > div > input:focus,
        .stSelectbox > div > div > div:focus-within {
            border-color: var(--neon-green) !important;
            box-shadow: 0 0 10px rgba(0, 255, 136, 0.3) !important;
        }

        /* Labels */
        .stTextInput label, .stDateInput label, .stSelectbox label {
            color: var(--text-muted) !important;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 1px;
        }

        /* ---------- Metric Cards (HUD Style) ---------- */
        div[data-testid="stMetric"] {
            background-color: rgba(18, 18, 26, 0.8);
            border: 1px solid var(--border-color);
            border-left: 2px solid var(--neon-blue);
            padding: 1rem;
            position: relative;
        }
        
        div[data-testid="stMetric"]:hover {
            border-color: var(--neon-blue);
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.15);
        }

        div[data-testid="stMetricLabel"] {
            color: var(--neon-blue) !important;
            font-family: 'Share Tech Mono', monospace;
            text-transform: uppercase;
            font-size: 0.9rem !important;
        }
        
        div[data-testid="stMetricValue"] {
            color: #fff !important;
            font-family: 'Orbitron', sans-serif;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
            font-size: 2rem !important;
        }

        /* ---------- DataFrame / Tables / DataGrid ---------- */
        /* Target the container for st.dataframe and st.table */
        div[data-testid="stDataFrame"], div[data-testid="stTable"] {
            border: 1px solid var(--border-color);
            background-color: var(--bg-card);
        }
        
        /* Attempt to style the internal Glide Data Grid (hard via CSS) */
        /* We rely on config.toml base="dark" for the main colors, but add overrides here */
        
        /* Table Headers */
        div[data-testid="stDataFrame"] div[class*="ColumnHeaders"] {
            background-color: #0f0f15;
            color: var(--neon-green);
            font-family: 'Share Tech Mono', monospace;
            text-transform: uppercase;
            font-weight: bold;
        }
        
        /* Table Cells - ensure high contrast */
        div[data-testid="stDataFrame"] div[class*="DataCell"] {
            color: #ffffff !important; 
            font-family: 'JetBrains Mono', monospace;
        }

        /* Adjusting st.table (static HTML table) if used anywhere */
        table {
            color: var(--text-main) !important;
            background-color: transparent !important;
        }
        thead tr th {
            color: var(--neon-green) !important;
            border-bottom: 2px solid var(--border-color) !important;
            text-transform: uppercase;
        }
        tbody tr td {
            border-bottom: 1px solid #1a1a24 !important;
            color: #ddd !important;
        }
        
        /* Scrollbars (Webkit) */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
            background: #0a0a0f;
        }
        ::-webkit-scrollbar-thumb {
            background: #333;
            border-radius: 0px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--neon-green);
        }

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {
            background-color: #050508;
            border-right: 1px solid var(--border-color);
        }
        
        section[data-testid="stSidebar"] hr {
            border-color: var(--border-color) !important;
        }
        
        /* Sidebar Nav Radio */
        .stRadio > div[role="radiogroup"] > label {
            background-color: transparent !important;
            color: var(--text-muted) !important;
            font-family: 'Share Tech Mono', monospace !important;
            padding: 10px 0;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .stRadio > div[role="radiogroup"] > label:hover {
            color: var(--neon-green) !important;
            padding-left: 5px;
        }
        
        .stRadio > div[role="radiogroup"] > label[data-checked="true"] {
            color: var(--neon-green) !important;
            text-shadow: 0 0 8px var(--neon-green);
            border-left: 2px solid var(--neon-green);
            padding-left: 10px;
            background: linear-gradient(90deg, rgba(0,255,136,0.1), transparent) !important;
        }

        /* ---------- Expander ---------- */
        .streamlit-expanderHeader {
            background-color: var(--bg-card) !important;
            border: 1px solid var(--border-color) !important;
            color: var(--text-main) !important;
            font-family: 'Share Tech Mono', monospace !important;
        }
        
        .streamlit-expanderContent {
            background-color: rgba(18, 18, 26, 0.5) !important;
            border: 1px solid var(--border-color) !important;
            border-top: none !important;
            color: var(--text-muted) !important;
        }

        /* ---------- Info/Success/Error Alerts ---------- */
        .stAlert {
            background-color: transparent !important;
            border-radius: 0px !important;
            border: 1px solid;
        }
        
        div[data-testid="stNotification"] {
             background-color: var(--bg-card) !important;
             border: 1px solid var(--neon-green) !important;
        }

        /* Typewriter Cursor Effect for Empty Elements */
        .element-container:empty::before {
             content: "█";
             animation: blink 1s infinite;
             color: var(--neon-green);
        }

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def cyberpunk_header(title, subtitle=None):
    """Custom Header with Cyberpunk styling"""
    # Using raw HTML to enforce specific structure for CSS targeting if needed, 
    # but st.markdown with standard H1/H2 is cleaner for the CSS defined above.
    
    st.markdown(f"# {title}")
    if subtitle:
        # Glitch effect wrapper could be added here if needed via specialized HTML
        st.markdown(f"**// {subtitle.upper()} //** <span style='color:var(--neon-green)'>_</span>", unsafe_allow_html=True)
    
    # Grid/Circuit divider
    st.markdown("""
        <div style="height: 2px; background: repeating-linear-gradient(90deg, var(--neon-green) 0, var(--neon-green) 5px, transparent 5px, transparent 10px); margin-bottom: 20px; opacity: 0.5;"></div>
    """, unsafe_allow_html=True)
