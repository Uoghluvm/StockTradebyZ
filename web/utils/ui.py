import streamlit as st

def inject_swiss_style():
    """注入瑞士国际主义风格 (Swiss International Style) CSS"""
    
    # 核心设计 Token
    # 颜色: White(#FFF), Black(#000), Red(#FF3000), Muted(#F2F2F2)
    # 边框: 2px solid black (Standard), 4px (Heavy)
    # 圆角: 0px (Strict)
    
    css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

        /* ---------- 全局重置 ---------- */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #000000;
        }
        
        /* 移除 Streamlit 默认 header/footer */
        header[data-testid="stHeader"] { display: none; }
        footer { display: none; }
        
        /* 主背景纹理 (Noise + Grid) */
        .stApp {
            background-color: #FFFFFF;
            background-image: 
                linear-gradient(#00000008 1px, transparent 1px),
                linear-gradient(90deg, #00000008 1px, transparent 1px);
            background-size: 24px 24px;
        }

        /* ---------- 标题与排版 ---------- */
        h1, h2, h3 {
            font-weight: 900 !important;
            text-transform: uppercase;
            letter-spacing: -1px;
            color: #000000;
        }
        
        h1 {
            font-size: 3.5rem !important;
            border-bottom: 4px solid #000;
            padding-bottom: 1rem;
            margin-bottom: 2rem;
        }
        
        h2 {
            font-size: 2rem !important;
            margin-top: 2rem;
            margin-bottom: 1rem;
            border-left: 8px solid #FF3000;
            padding-left: 1rem;
        }

        /* ---------- 组件样式覆盖 ---------- */
        
        /* 按钮: 直角、黑底白字、无阴影 */
        .stButton > button {
            border: 2px solid #000 !important;
            border-radius: 0px !important;
            background-color: #000 !important;
            color: #FFF !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            box-shadow: none !important;
            transition: all 0.1s ease !important;
            padding: 0.5rem 2rem !important;
        }
        
        .stButton > button:hover {
            background-color: #FF3000 !important;
            border-color: #FF3000 !important;
            color: #FFF !important;
            transform: translateY(-2px);
        }
        
        .stButton > button:active {
            transform: translateY(0px);
        }

        /* 输入框: 直角、粗框 */
        .stTextInput > div > div > input,
        .stDateInput > div > div > input,
        .stSelectbox > div > div > div {
            border: 2px solid #000 !important;
            border-radius: 0px !important;
            background-color: #FFF !important;
            color: #000 !important;
            box-shadow: none !important;
        }
        
        /* 选中状态 */
        .stTextInput > div > div > input:focus,
        .stDateInput > div > div > input:focus {
            border-color: #FF3000 !important;
        }

        /* 表格: 更明显的边框 */
        div[data-testid="stDataFrame"] {
            border: 2px solid #000 !important;
            padding: 4px;
            background: #fff;
        }

        /* Metrics 卡片模拟 */
        div[data-testid="stMetric"] {
            background-color: #F2F2F2;
            border: 2px solid #000;
            padding: 1rem;
            border-radius: 0px;
        }
        div[data-testid="stMetricLabel"] { opacity: 0.7; font-weight: 700; text-transform: uppercase; font-size: 0.8rem; }
        div[data-testid="stMetricValue"] { font-size: 2rem; font-weight: 900; }

        /* Sidebar: 简单的分割线 */
        section[data-testid="stSidebar"] {
            border-right: 2px solid #000;
            background-color: #F2F2F2;
        }
        
        /* Radio 按钮 */
        .stRadio > div[role="radiogroup"] > label {
            background-color: transparent !important;
            border: none !important;
            color: #000 !important;
            padding-left: 0.5rem;
        }
        .stRadio > div[role="radiogroup"] > label[data-checked="true"] {
            border-left: 4px solid #FF3000 !important;
            font-weight: bold;
        }
        
        /* Alert/Info/Warning */
        .stAlert {
            border-radius: 0px !important;
            border: 2px solid #000 !important;
        }

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def swiss_header(title, subtitle=None):
    st.markdown(f"# {title}")
    if subtitle:
        st.markdown(f"**{subtitle.upper()}**")
    st.markdown("---")
