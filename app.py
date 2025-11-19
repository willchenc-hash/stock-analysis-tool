import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Gemini Stock Master Pro", layout="wide", page_icon="📈")

# --- 配置：常用股票中文映射 (为了体验更好，手动定义一部分热门股) ---
KNOWN_CHINESE_NAMES = {
    "600519.SS": "贵州茅台",
    "300750.SZ": "宁德时代",
    "000858.SZ": "五粮液",
    "600036.SS": "招商银行",
    "601318.SS": "中国平安",
    "002594.SZ": "比亚迪",
    "000001.SZ": "平安银行",
    "0700.HK":   "腾讯控股 (港股)",
    "3690.HK":   "美团 (港股)",
    "9988.HK":   "阿里巴巴 (港股)",
    "NVDA":      "NVIDIA (英伟达)",
    "AAPL":      "Apple (苹果)",
    "TSLA":      "Tesla (特斯拉)",
    "MSFT":      "Microsoft (微软)"
}

# --- 辅助功能：智能识别股票代码 ---
def smart_ticker_formatter(symbol):
    symbol = symbol.strip().upper()
    # 纯数字且为6位，自动判断沪深
    if symbol.isdigit() and len(symbol) == 6:
        if symbol.startswith(('6', '9')):
            return f"{symbol}.SS"
        elif symbol.startswith(('0', '3', '2')):
            return f"{symbol}.SZ"
        elif symbol.startswith(('4', '8')):
            return f"{symbol}.BJ"
    return symbol

# --- 核心逻辑：获取数据 + 获取名称 ---
@st.cache_data
def load_data_and_name(ticker, start, end):
    formatted_ticker = smart_ticker_formatter(ticker)
    data_source = "Yahoo Finance"
    stock_name = formatted_ticker # 默认名称为代码
    
    try:
        # 1. 尝试获取名称 (先查字典，再查 API)
        if formatted_ticker in KNOWN_CHINESE_NAMES:
            stock_name = KNOWN_CHINESE_NAMES[formatted_ticker]
        else:
            # 如果不在字典里，尝试通过 API 获取 (这步可能会慢一点)
            try:
                ticker_obj = yf.Ticker(formatted_ticker)
                # 获取 info 里的 shortName 或 longName
                info = ticker_obj.info
                stock_name = info.get('shortName', info.get('longName', formatted_ticker))
            except:
                pass # 获取名称失败不影响数据展示

        # 2. 尝试下载历史数据
        df = yf.download(formatted_ticker, start=start, end=end, progress=False)
        
        if df.empty:
            raise ValueError("Empty Data")

        # 清洗数据 (处理 MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.reset_index(inplace=True)
        
    except Exception as e:
        # 降级模式：模拟数据
        data_source = "模拟演示模式 (数据获取失败)"
        stock_name = f"模拟公司 ({formatted_ticker})"
        
        date_range = pd.date_range(start=start, end=end)
        np.random.seed(42)
        price_changes = np.random.randn(len(date_range)) 
        prices = 100 + np.cumsum(price_changes)
        
        df = pd.DataFrame({
            'Date': date_range,
            'Open': prices, 'High': prices + 1, 'Low': prices - 1, 'Close': prices,
            'Volume': np.random.randint(1000000, 5000000, size=len(date_range))
        })
    
    return df, data_source, formatted_ticker, stock_name

def add_indicators(df):
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    return df

# --- 侧边栏 ---
st.sidebar.header('⚙️ 股票设置')
st.sidebar.markdown("**支持 沪深 / 港股 / 美股**")

user_input = st.sidebar.text_input("输入代码 (如 600519)", value="600519")
start_date = st.sidebar.date_input("开始日期", value=datetime.today() - timedelta(days=365))
end_date = st.sidebar.date_input("结束日期", value=datetime.today())

st.sidebar.markdown("---")
st.sidebar.caption("Gemini 3 Powered")

# --- 主页面 ---
if st.sidebar.button('🚀 开始分析', type="primary"):
    with st.spinner(f'🔍 正在搜寻 {user_input} 的详细信息...'):
        
        # 获取所有信息
        df, source_status, real_code, name = load_data_and_name(user_input, start_date, end_date)
        
        # === 标题区域优化 ===
        st.title(f"{name}") 
        st.caption(f"股票代码: {real_code} | 数据来源: {source_status}")

        if df is None or len(df) < 2:
            st.error("❌ 未找到有效数据。")
        else:
            if "模拟" in source_status:
                st.warning("⚠️ 注意：当前显示为模拟数据。")
            
            df = add_indicators(df)
            
            # 指标显示
            try:
                last_day = df.iloc[-1]
                prev_day = df.iloc[-2]
                curr_price = float(last_day['Close'])
                prev_price = float(prev_day['Close'])
                change = curr_price - prev_price
                pct_change = (change / prev_price) * 100
                
                # 货币符号逻辑
                currency = "$"
                if ".SS" in real_code or ".SZ" in real_code or ".BJ" in real_code:
                    currency = "¥" 
                elif ".HK" in real_code:
                    currency = "HK$"

                col1, col2, col3 = st.columns(3)
                col1.metric("最新收盘", f"{currency}{curr_price:.2f}")
                col2.metric("涨跌额", f"{change:.2f}", delta_color="normal")
                col3.metric("涨跌幅", f"{pct_change:.2f}%", delta_color="normal") # 直接显示百分比
            except:
                st.error("指标计算异常")

            # 绘图
            fig = go.Figure()
            
            # K线
            fig.add_trace(go.Candlestick(
                x=df['Date'], open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name='K线'
            ))
            
            # 均线
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_20'], 
                                     line=dict(color='#2962FF', width=1.5), name='20日线'))
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_50'], 
                                     line=dict(color='#FF6D00', width=1.5), name='50日线'))
            
            fig.update_layout(
                height=600, 
                template="plotly_dark", 
                xaxis_rangeslider_visible=False,
                title=f"📊 {name} ({real_code}) 股价走势图",
                hovermode="x unified" # 鼠标悬停显示所有数据
            )
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander(f"查看 {name} 历史数据报表"):
                st.dataframe(df.sort_values('Date', ascending=False))

else:
    st.info("👈 请在左侧输入代码，例如 600519，然后点击“开始分析”")
