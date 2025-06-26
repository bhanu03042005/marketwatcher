import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import date
import yagmail

#Setup
st.set_page_config(page_title="📈 Stock Market App", layout="wide")
st.markdown("<h1 style='text-align: center;'>📈 Stock Market Dashboard</h1>", unsafe_allow_html=True)

#Theme Toggle
theme = st.sidebar.radio("🌗 Choose Theme", ["Light", "Dark"])
if theme == "Dark":
    st.markdown("""
        <style>
        body, .stApp { background-color: #0e1117; color: white; }
        </style>
    """, unsafe_allow_html=True)

#Sidebar Inputs
st.sidebar.header("Search Settings")
ticker = st.sidebar.text_input("Enter Stock Ticker", "AAPL")
start_date = st.sidebar.date_input("Start Date", date(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", date.today())
chart_type = st.sidebar.selectbox("📊 Chart Type", ["Line", "SMA", "Candlestick"])
sma_period = st.sidebar.slider("SMA Window", 5, 50, 20)
show_rsi = st.sidebar.checkbox("Show RSI (14-day)")
show_macd = st.sidebar.checkbox("Show MACD")
show_bollinger = st.sidebar.checkbox("Show Bollinger Bands")
show_volume = st.sidebar.checkbox("Show Volume")

#Session-based Search History
if "history" not in st.session_state:
    st.session_state.history = []

if ticker and ticker not in st.session_state.history:
    st.session_state.history.append(ticker)

# Show Search History
if st.session_state.history:
    st.sidebar.markdown("### 🔍 Search History")
    for item in st.session_state.history[-5:][::-1]:
        st.sidebar.write(f"- {item}")

# Fetch Stock Data
if ticker:
    stock = yf.Ticker(ticker)
    data = stock.history(start=start_date, end=end_date)

    if data.empty:
        st.warning("⚠️ No data found. Check ticker or date range.")
    else:
        # 🏢 Company Info
        st.sidebar.markdown("### 🏢 Company Info")
        info = stock.info
        st.sidebar.write(f"**Name:** {info.get('longName', 'N/A')}")
        st.sidebar.write(f"**Sector:** {info.get('sector', 'N/A')}")
        st.sidebar.write(f"**Industry:** {info.get('industry', 'N/A')}")
        st.sidebar.write(f"**Website:** {info.get('website', 'N/A')}")

        # 📃 Preview + CSV Download
        st.subheader("📃 Data Preview")
        st.dataframe(data.tail(), use_container_width=True)
        st.download_button("📅 Download CSV", data.to_csv().encode(), f"{ticker}_data.csv", "text/csv")

        # 🧠 Indicators
        if show_rsi:
            delta = data['Close'].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(14).mean()
            avg_loss = loss.rolling(14).mean()
            rs = avg_gain / avg_loss
            data['RSI'] = 100 - (100 / (1 + rs))

        if show_macd:
            exp1 = data['Close'].ewm(span=12, adjust=False).mean()
            exp2 = data['Close'].ewm(span=26, adjust=False).mean()
            data['MACD'] = exp1 - exp2
            data['Signal Line'] = data['MACD'].ewm(span=9, adjust=False).mean()

        if show_bollinger:
            sma = data['Close'].rolling(20).mean()
            std = data['Close'].rolling(20).std()
            data['Upper Band'] = sma + 2 * std
            data['Lower Band'] = sma - 2 * std

        #Chart
        st.subheader("📊 Stock Chart")
        fig = go.Figure()

        if chart_type == "Line":
            fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name="Close"))
        elif chart_type == "SMA":
            data['SMA'] = data['Close'].rolling(sma_period).mean()
            fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name="Close"))
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA'], name=f"{sma_period}-Day SMA"))
        elif chart_type == "Candlestick":
            fig.add_trace(go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name="Candlestick"
            ))

        if show_rsi:
            fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name="RSI", yaxis="y2"))

        if show_macd:
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name="MACD", line=dict(color='blue')))
            fig.add_trace(go.Scatter(x=data.index, y=data['Signal Line'], name="Signal", line=dict(color='orange')))

        if show_bollinger:
            fig.add_trace(go.Scatter(x=data.index, y=data['Upper Band'], name="Upper Band", line=dict(color='gray')))
            fig.add_trace(go.Scatter(x=data.index, y=data['Lower Band'], name="Lower Band", line=dict(color='gray')))

        if show_volume:
            fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name="Volume", yaxis="y3", marker=dict(color='rgba(0,100,255,0.3)')))

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            yaxis2=dict(title="RSI", overlaying='y', side='right', showgrid=False),
            yaxis3=dict(title="Volume", anchor="x", overlaying="y", side="right", position=1.0, showgrid=False),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h")
        )

        st.plotly_chart(fig, use_container_width=True)

        #Email Alert Section
        st.subheader("🔔 Set Email Alert for Price Drop")
        with st.form("email_alert_form"):
            user_email = st.text_input("Enter your email:")
            target_price = st.number_input("Alert me when price falls below ($)", value=100.0)
            submitted = st.form_submit_button("Set Alert")

            if submitted and ticker and not data.empty:
                latest_price = data['Close'][-1]
                if latest_price <= target_price:
                    try:
                        yag = yagmail.SMTP("your_email@gmail.com", "your_app_password")
                        yag.send(
                            to=user_email,
                            subject=f"{ticker} Price Alert",
                            contents=f"The price of {ticker} has dropped to ${latest_price:.2f}, below your target of ${target_price:.2f}."
                        )
                        st.success(f"✅ Email alert sent to {user_email}")
                    except Exception as e:
                        st.error(f"❌ Failed to send email: {e}")
                else:
                    st.info(f"ℹ️ Current price (${latest_price:.2f}) is still above target.")
