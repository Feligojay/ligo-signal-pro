from utils.candlestick_patterns import get_pattern_recommendation

def generate_signals(df, symbol):
    df = calculate_divergence(df)
    df = detect_key_levels(df)
    df = calculate_volume_spike(df)
    
    signals = []
    
    for i in range(2, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Bullish Reversal Conditions
        bull_conditions = {
            'rsi_div': current['bullish_div'],
            'oversold': (current['rsi'] < 30) and (current['close'] > current['open']),
            'hammer': current['pattern'] in ('Hammer', 'Inverted Hammer'),
            'support': abs(current['low'] - current['support']) < (0.005 * current['close']),
            'macd_cross': (current['macd'] > current['macd_signal']) and (prev['macd'] <= prev['macd_signal']),
            'volume': current['volume_spike']
        }
        
        # Bearish Reversal Conditions
        bear_conditions = {
            'rsi_div': current['bearish_div'],
            'overbought': (current['rsi'] > 70) and (current['close'] < current['open']),
            'shooting_star': current['pattern'] in ('Shooting Star', 'Hanging Man'),
            'resistance': abs(current['high'] - current['resistance']) < (0.005 * current['close']),
            'macd_cross': (current['macd'] < current['macd_signal']) and (prev['macd'] >= prev['macd_signal']),
            'volume': current['volume_spike']
        }
        
        bull_score = sum(bull_conditions.values())
        bear_score = sum(bear_conditions.values())
        
        signal = {
            'symbol': symbol,
            'time': current.name,
            'price': current['close'],
            'factors': []
        }
        
        if bull_score >= 3:
            signal.update({
                'action': 'BUY',
                'reversal_type': 'bullish',
                'confidence': f"{min(100, bull_score*20)}%",
                'factors': [k for k,v in bull_conditions.items() if v]
            })
            signals.append(signal)
            
        if bear_score >= 3:
            signal.update({
                'action': 'SELL',
                'reversal_type': 'bearish',
                'confidence': f"{min(100, bear_score*20)}%",
                'factors': [k for k,v in bear_conditions.items() if v]
            })
            signals.append(signal)
    
    return signals