import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Gemini Stock Master (A-Share Edition)", layout="wide", page_icon="📈")

# --- 辅助功能：智能识别股票代码 ---
def smart_ticker_formatter(symbol):
    """
    自动为 A 股代码添加后缀
    """
    symbol = symbol.strip().upper()
    
    # 如果用户输入的是 6 位数字，尝试自动判断
    if symbol.isdigit() and len(symbol) == 6:
        if symbol.startswith('6') or symbol.startswith('9'):
            return f"{symbol}.SS" # 上海主板/科创板
        elif symbol.startswith('0') or symbol.startswith('3') or symbol.startswith('2'):
            return f"{symbol}.SZ" # 深圳主板/创业板
        elif symbol.startswith('4') or symbol.startswith('8'):
            return f"{symbol}.BJ" # 北京证券交易所
            
    return symbol

# --- 核心逻辑：数据获取 ---
@st.cache_data
def load_data(ticker, start, end):
    data_source = "Yahoo Finance"
    
    # 应用智能格式化
    formatted_ticker = smart_ticker_formatter(ticker)
    
    try:
        # 尝试下载
        df = yf.download(formatted_ticker, start=start, end=end, progress=False)
        
        if df.empty:
            raise ValueError("Empty Data")

        # === 修复 1: 处理 MultiIndex ===
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.reset_index(inplace=True)
        
        # 标记一下实际上查的是哪个代码
        real_ticker = formatted_ticker
        
    except Exception as e:
        # 降级：模拟数据
        data_source = "模拟演示数据 (无法连接 Yahoo)"
        real_ticker = ticker
        date_range = pd.date_range(start=start, end=end)
        np.random.seed(42)
        price_changes = np.random.randn(len(date_range)) 
        prices = 100 + np.cumsum(price_changes)
        
        df = pd.DataFrame({
            'Date': date_range,
            'Open': prices, 'High': prices + 1, 'Low': prices - 1, 'Close': prices,
            'Volume': np.random.randint(1000000, 5000000, size=len(date_range))
        })
    
    return df, data_source, real_ticker

def add_indicators(df):
    # === 修复 2: 强制转 Float ===
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    return df

# --- 侧边栏 ---
st.sidebar.header('⚙️ 参数设置')

# 提示用户支持 A 股
st.sidebar.markdown("**支持 A 股/美股/港股**")
user_input = st.sidebar.text_input("股票代码 (直接输数字即可)", value="600519").upper()

today = datetime.today()
start_date = st.sidebar.date_input("开始日期", value=today - timedelta(days=365))
end_date = st.sidebar.date_input("结束日期", value=today)

st.sidebar.info("💡 **A 股小贴士**：\n直接输入 600519，系统会自动识别为 600519.SS")

# --- 主页面 ---
st.title(f"📈 股票分析仪表盘")

if st.sidebar.button('开始分析', type="primary"):
    with st.spinner(f'🤖 正在抓取 {user_input} 的数据...'):
        
        # 1. 获取数据
        df, source_status, real_ticker = load_data(user_input, start_date, end_date)
        
        # 更新标题显示真实代码
        st.subheader(f"当前分析: {real_ticker}")

        if df is None or len(df) < 2:
            st.error(f"❌ 未找到代码 {real_ticker} 的数据。")
        else:
            if "模拟" in source_status:
                st.warning(f"⚠️ 网络原因切换至：{source_status}")
            
            # 2. 处理
            df = add_indicators(df)
            
            # 3. 指标
            try:
                last_day = df.iloc[-1]
                prev_day = df.iloc[-2]
                current_price = float(last_day['Close'])
                prev_price = float(prev_day['Close'])
                change = current_price - prev_price
                pct_change = (change / prev_price) * 100
                
                # 判断货币符号
                currency = "¥" if ".SS" in real_ticker or ".SZ" in real_ticker else "$"
                
                col1, col2, col3 = st.columns(3)
                col1.metric("最新收盘价", f"{currency}{current_price:.2f}")
                col2.metric("涨跌幅", f"{change:.2f} ({pct_change:.2f}%)", delta_color="normal")
                col3.metric("交易量", f"{int(last_day['Volume']):,}")
            except:
                st.error("指标计算出错，请查看下方图表")

            # 4. 绘图
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'],
                                        low=df['Low'], close=df['Close'], name='K线'))
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_20'], line=dict(color='blue', width=1), name='20日均线'))
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_50'], line=dict(color='orange', width=1), name='50日均线'))
            
            fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False,
                             title=f"{real_ticker} 股价走势")
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👈 在左侧输入股票代码 (例如 600519) 并点击“开始分析”")
