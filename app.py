import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="Gemini Stock Master", layout="wide", page_icon="📈")

# --- 核心逻辑：数据获取 (带缓存) ---
@st.cache_data
def load_data(ticker, start, end):
    """
    获取数据并缓存，避免重复下载
    """
    try:
        df = yf.download(ticker, start=start, end=end, progress=False)
        df.reset_index(inplace=True)
        return df
    except Exception as e:
        return None

# --- 核心逻辑：技术指标计算 ---
def add_indicators(df):
    # 简单移动平均线 (SMA)
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    return df

# --- 侧边栏：用户输入 ---
st.sidebar.header('⚙️ 参数设置')

# 1. 输入股票代码
ticker = st.sidebar.text_input("股票代码 (Yahoo 格式)", value="NVDA").upper()

# 2. 选择日期范围
today = datetime.today()
start_date = st.sidebar.date_input("开始日期", value=today - timedelta(days=365))
end_date = st.sidebar.date_input("结束日期", value=today)

# 3. 快捷链接
st.sidebar.markdown("---")
st.sidebar.markdown("### 💡 常用代码参考")
st.sidebar.code("NVDA (英伟达)\nMSFT (微软)\n0700.HK (腾讯)\nBTC-USD (比特币)", language="text")

# --- 主页面 ---
st.title(f"📈 {ticker} 股票分析仪表盘")

if st.sidebar.button('开始分析', type="primary"):
    with st.spinner('🤖 Gemini 正在通过网络抓取数据...'):
        # 1. 获取数据
        df = load_data(ticker, start_date, end_date)
        
        if df is None or df.empty:
            st.error(f"❌ 无法找到股票代码 {ticker} 的数据，请检查拼写。")
        else:
            # 2. 数据预处理
            df = add_indicators(df)
            
            # 3. 展示关键指标 (Metrics)
            last_day = df.iloc[-1]
            prev_day = df.iloc[-2]
            change = last_day['Close'] - prev_day['Close']
            pct_change = (change / prev_day['Close']) * 100
            
            col1, col2, col3 = st.columns(3)
            col1.metric("最新收盘价", f"${last_day['Close']:.2f}")
            col2.metric("涨跌幅", f"{change:.2f} ({pct_change:.2f}%)", 
                        delta_color="normal")
            col3.metric("交易量", f"{int(last_day['Volume']):,}")

            # 4. 绘制交互式 K 线图 (Candlestick)
            st.subheader("📊 交互式 K 线图与均线")
            
            fig = go.Figure()

            # 添加 K 线
            fig.add_trace(go.Candlestick(
                x=df['Date'],
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'],
                name='K线'
            ))

            # 添加均线
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_20'], 
                                     line=dict(color='blue', width=1), name='SMA 20'))
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_50'], 
                                     line=dict(color='orange', width=1), name='SMA 50'))

            fig.update_layout(
                height=600,
                xaxis_rangeslider_visible=False, # 底部滑块，可设为 True
                title=f"{ticker} 股价走势",
                yaxis_title="价格 (USD)",
                template="plotly_dark" # 使用暗色主题，更显专业
            )

            st.plotly_chart(fig, use_container_width=True)

            # 5. 展示原始数据
            with st.expander("查看原始数据表格"):
                st.dataframe(df.sort_values(by='Date', ascending=False))

else:
    st.info("👈 请在左侧输入参数并点击“开始分析”")
