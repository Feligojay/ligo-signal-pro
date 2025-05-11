import streamlit as st
import pandas as pd
import time
from datetime import datetime
from utils.indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_moving_averages,
    calculate_atr,
    calculate_divergence
)
from utils.candlestick_patterns import identify_patterns
from utils.signal_generator import generate_signals
from utils.auto_trader import AutoTrader
from utils.deriv_api import DerivAPI

# Initialize session state
if 'trader' not in st.session_state:
    st.session_state.trader = AutoTrader()
if 'signals' not in st.session_state:
    st.session_state.signals = []
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = pd.DataFrame()
if 'api_connected' not in st.session_state:
    st.session_state.api_connected = False
if 'trading_active' not in st.session_state:
    st.session_state.trading_active = False
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

# App Configuration
st.set_page_config(layout="wide")
st.title("Deriv Trading Bot Pro")

def refresh_data():
    """Automatically refresh market data and signals"""
    try:
        with st.spinner("Loading market data..."):
            raw_data = DerivAPI(st.session_state.api_token).get_candles(
                symbol="R_100", 
                timeframe="1m", 
                count=100
            )
            if raw_data:
                df = pd.DataFrame(raw_data)
                
                # Calculate indicators
                df = calculate_rsi(df)
                df = calculate_macd(df)
                df = calculate_moving_averages(df)
                df = calculate_atr(df)
                df = calculate_divergence(df)
                df = identify_patterns(df)
                
                # Update session state
                st.session_state.historical_data = df
                st.session_state.signals = generate_signals(df, "R_100")
                st.session_state.last_update = datetime.now()
                
                # Force UI update
                st.rerun()
            else:
                st.error("Received empty data from API")
    except Exception as e:
        st.error(f"Data refresh error: {str(e)}")

# Sidebar Configuration
with st.sidebar:
    st.header("API Configuration")
    
    api_token = st.text_input("Deriv API Token", type="password", key="api_token_input")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect to Deriv API", disabled=st.session_state.api_connected):
            if st.session_state.trader.connect(api_token):
                st.session_state.api_connected = True
                st.session_state.api_token = api_token
                refresh_data()  # Auto-load on connect
                st.success("✅ Connected successfully!")
            else:
                st.session_state.api_connected = False
                st.error("Connection failed")
    
    with col2:
        if st.button("Disconnect", disabled=not st.session_state.api_connected):
            st.session_state.trader.stop()
            st.session_state.api_connected = False
            st.session_state.trading_active = False
            st.warning("Disconnected from API")
            st.rerun()

    st.header("Trading Parameters")
    trade_amount = st.number_input("Trade Amount ($)", min_value=1, value=10, 
                                 disabled=st.session_state.trading_active)
    take_profit = st.number_input("Take Profit (%)", min_value=0.1, value=5.0,
                                 disabled=st.session_state.trading_active)
    stop_loss = st.number_input("Stop Loss (%)", min_value=0.1, value=2.0,
                               disabled=st.session_state.trading_active)
    trade_duration = st.number_input("Trade Duration (mins)", min_value=1, value=5,
                                    disabled=st.session_state.trading_active)

# Main App Tabs
tab1, tab2, tab3 = st.tabs(["Signal Dashboard", "Automated Trading", "Performance"])

with tab1:
    st.header("Real-time Signal Dashboard")
    
    if st.session_state.api_connected:
        if st.session_state.last_update:
            st.caption(f"Last update: {st.session_state.last_update.strftime('%H:%M:%S')}")
            
            if st.session_state.signals:
                st.subheader("Active Trading Signals")
                signals_df = pd.DataFrame(st.session_state.signals)
                
                display_columns = ['time', 'symbol', 'action', 'confidence', 'price', 'duration']
                if 'reversal_type' in signals_df.columns:
                    display_columns.append('reversal_type')
                
                st.dataframe(
                    signals_df[display_columns].sort_values('time', ascending=False),
                    height=300,
                    use_container_width=True
                )
            else:
                st.warning("No trading signals detected in current market data")
            
            # Auto-refresh
            time.sleep(30)
            refresh_data()
        else:
            refresh_data()
    else:
        st.warning("Please connect to Deriv API to view signals")

with tab2:
    st.header("Automated Trading Control")
    
    status = st.session_state.trader.get_status()
    st.write(f"**Connection Status:** {'🟢 Connected' if status['connected'] else '🔴 Disconnected'}")
    st.write(f"**Trading Status:** {'🟢 Running' if status['running'] else '🔴 Stopped'}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Trading", 
                    disabled=not status['connected'] or status['running'],
                    help="Requires active API connection"):
            if st.session_state.trader.start(
                amount=trade_amount,
                take_profit=take_profit,
                stop_loss=stop_loss,
                trade_duration=trade_duration
            ):
                st.session_state.trading_active = True
                st.rerun()
    
    with col2:
        if st.button("Stop Trading", 
                    disabled=not status['running'],
                    help="Stop automated trading"):
            st.session_state.trader.stop()
            st.session_state.trading_active = False
            st.rerun()
    
    if status['active_trades']:
        st.subheader("Active Positions")
        st.dataframe(
            pd.DataFrame(status['active_trades'])[['symbol', 'action', 'amount', 'time_opened']],
            height=200,
            use_container_width=True
        )

with tab3:
    st.header("Trading Performance")
    
    if st.button("Refresh Performance", disabled=not st.session_state.api_connected):
        history = st.session_state.trader.get_trade_history()
        if not history.empty:
            st.subheader("Trade History")
            st.dataframe(
                history.sort_values('time_opened', ascending=False),
                height=400,
                use_container_width=True
            )
            
            win_rate = (history['profit'] > 0).mean() * 100
            total_profit = history['profit'].sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Win Rate", f"{win_rate:.2f}%")
            with col2:
                st.metric("Total Profit", f"${total_profit:.2f}")
        else:
            st.warning("No trading history available")

if __name__ == "__main__":
    st.write("Application ready")