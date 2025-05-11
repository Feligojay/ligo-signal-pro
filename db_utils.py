from utils.database import save_signal, get_signals, update_signal_result, get_signals_performance, get_signals_dataframe
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

def save_signals_to_db(signals):
    """
    Save signals to the database
    
    Parameters:
    signals (list): List of signal dictionaries
    
    Returns:
    list: List of signal IDs
    """
    saved_ids = []
    for signal in signals:
        try:
            signal_id = save_signal(signal)
            if signal_id is not None:
                saved_ids.append(signal_id)
        except Exception as e:
            print(f"Error saving signal to database: {e}")
    return saved_ids

def display_historical_signals(days=7):
    """
    Display historical signals from the database
    
    Parameters:
    days (int): Number of days to look back (default: 7)
    """
    signals = get_signals(hours=days*24)
    
    if not signals:
        st.info(f"No signals found in the last {days} days.")
        return
    
    # Sort by time (newest first)
    signals = sorted(signals, key=lambda x: x["time"], reverse=True)
    
    for signal in signals:
        if signal["action"] == "BUY":
            signal_color = "#4CAF50"  # Green
        else:
            signal_color = "#EF5350"  # Red
        
        # Add result color
        result_color = "#9E9E9E"  # Grey for no result
        if signal.get("result") == "WIN":
            result_color = "#4CAF50"  # Green for win
        elif signal.get("result") == "LOSS":
            result_color = "#EF5350"  # Red for loss
        
        # Format time
        signal_time = signal["time"]
        
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if signal["action"] == "BUY":
                    icon = "↗️"
                else:
                    icon = "↘️"
                
                result_text = signal.get("result", "PENDING")
                
                st.markdown(f"""
                <div style='background-color: #252526; border-radius: 5px; margin-bottom: 10px; padding: 12px;'>
                    <div style='display: flex; align-items: center; margin-bottom: 10px;'>
                        <div style='width: 10px; background-color: {signal_color}; height: 40px; border-radius: 3px; margin-right: 12px;'></div>
                        <div style='font-size: 18px; font-weight: bold; color: {signal_color};'>{icon} {signal["action"]} {signal["symbol"]}</div>
                        <div style='margin-left: auto; padding: 5px 10px; background-color: {result_color}; color: white; border-radius: 3px; font-weight: bold;'>{result_text}</div>
                    </div>
                    <div style='display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 8px;'>
                        <div style='background-color: #333; padding: 5px 8px; border-radius: 3px;'>
                            Time: {signal_time}
                        </div>
                        <div style='background-color: #333; padding: 5px 8px; border-radius: 3px;'>
                            Duration: {signal["duration"]}
                        </div>
                        <div style='background-color: #333; padding: 5px 8px; border-radius: 3px;'>
                            Confidence: {signal["confidence"]}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Only show result buttons if no result recorded yet
                if not signal.get("result"):
                    signal_id = signal.get("id")
                    if st.button("Win", key=f"win_{signal_id}"):
                        update_signal_result(signal_id, "WIN")
                        st.rerun()
                    if st.button("Loss", key=f"loss_{signal_id}"):
                        update_signal_result(signal_id, "LOSS")
                        st.rerun()

def display_performance_metrics(days=30):
    """
    Display performance metrics from the database
    
    Parameters:
    days (int): Number of days to look back (default: 30)
    """
    performance = get_signals_performance(days=days)
    
    if performance["total_signals"] == 0:
        st.info(f"No signals with results found in the last {days} days.")
        return
    
    # Display overall metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Signals", performance["total_signals"])
    
    with col2:
        st.metric("Win Rate", f"{performance['win_rate']:.1f}%")
    
    with col3:
        st.metric("Wins / Losses", f"{performance['win_count']} / {performance['loss_count']}")
    
    with col4:
        st.metric("Profit/Loss", f"{performance['total_profit']:.2f}")
    
    # Display performance by symbol
    st.subheader("Performance by Symbol")
    
    symbols_data = []
    for symbol, stats in performance["symbols"].items():
        symbols_data.append({
            "Symbol": symbol,
            "Total": stats["total"],
            "Wins": stats["wins"],
            "Losses": stats["losses"],
            "Win Rate": f"{stats['win_rate']:.1f}%",
            "Profit/Loss": f"{stats['profit']:.2f}"
        })
    
    if symbols_data:
        df = pd.DataFrame(symbols_data)
        st.dataframe(df)
        
        # Create win rate chart
        fig = px.bar(
            df, 
            x="Symbol", 
            y=[int(float(x.strip('%'))) for x in df["Win Rate"]], 
            title="Win Rate by Symbol",
            labels={"y": "Win Rate (%)"},
            color_discrete_sequence=["#7E57C2"]
        )
        
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            font=dict(color='#FAFAFA')
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Create a pie chart for win/loss ratio
    if performance["total_signals"] > 0:
        fig = go.Figure(data=[go.Pie(
            labels=["Wins", "Losses"],
            values=[performance["win_count"], performance["loss_count"]],
            hole=.4,
            marker=dict(colors=["#4CAF50", "#EF5350"])
        )])
        
        fig.update_layout(
            title="Win/Loss Distribution",
            template="plotly_dark",
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            font=dict(color='#FAFAFA')
        )
        
        st.plotly_chart(fig, use_container_width=True)