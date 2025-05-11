import pandas as pd
import numpy as np

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(span=period).mean()
    avg_loss = loss.ewm(span=period).mean()
    
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def calculate_macd(df, fast=12, slow=26, signal=9):
    df['ema_fast'] = df['close'].ewm(span=fast).mean()
    df['ema_slow'] = df['close'].ewm(span=slow).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['macd_signal'] = df['macd'].ewm(span=signal).mean()
    return df.drop(['ema_fast', 'ema_slow'], axis=1)

def calculate_moving_averages(df, short_period=20, long_period=50):
    df['ma_20'] = df['close'].rolling(window=short_period).mean()
    df['ma_50'] = df['close'].rolling(window=long_period).mean()
    
    # Add crossover signals
    df['ma_cross'] = 0
    for i in range(1, len(df)):
        if df['ma_20'].iloc[i-1] <= df['ma_50'].iloc[i-1] and df['ma_20'].iloc[i] > df['ma_50'].iloc[i]:
            df['ma_cross'].iloc[i] = 1
        elif df['ma_20'].iloc[i-1] >= df['ma_50'].iloc[i-1] and df['ma_20'].iloc[i] < df['ma_50'].iloc[i]:
            df['ma_cross'].iloc[i] = -1
    
    return df

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = true_range.rolling(period).mean()
    return df

def calculate_divergence(df, rsi_period=14, lookback=5):
    """Calculate both regular and hidden RSI divergences"""
    if 'rsi' not in df.columns:
        df = calculate_rsi(df, rsi_period)
    
    # Initialize columns
    divergence_cols = ['bullish_div', 'bearish_div', 'hidden_bullish_div', 'hidden_bearish_div']
    for col in divergence_cols:
        df[col] = False
    
    # Calculate divergences
    for i in range(lookback, len(df)):
        # Price and RSI values
        price_low = df['low'].iloc[i]
        price_prev_low = df['low'].iloc[i-lookback]
        price_high = df['high'].iloc[i]
        price_prev_high = df['high'].iloc[i-lookback]
        rsi = df['rsi'].iloc[i]
        rsi_prev = df['rsi'].iloc[i-lookback]
        
        # Regular Bullish Divergence (Price Lower Low, RSI Higher Low)
        if (price_low < price_prev_low) and (rsi > rsi_prev):
            df['bullish_div'].iloc[i] = True
            
        # Regular Bearish Divergence (Price Higher High, RSI Lower High)
        elif (price_high > price_prev_high) and (rsi < rsi_prev):
            df['bearish_div'].iloc[i] = True
            
        # Hidden Bullish Divergence (Price Higher Low, RSI Lower Low)
        elif (price_low > price_prev_low) and (rsi < rsi_prev):
            df['hidden_bullish_div'].iloc[i] = True
            
        # Hidden Bearish Divergence (Price Lower High, RSI Higher High)
        elif (price_high < price_prev_high) and (rsi > rsi_prev):
            df['hidden_bearish_div'].iloc[i] = True
            
    return df

__all__ = [
    'calculate_rsi',
    'calculate_macd',
    'calculate_moving_averages',
    'calculate_atr',
    'calculate_divergence'  # Now properly included
]