import pandas as pd
import numpy as np

def identify_patterns(df):
    """Enhanced pattern detection with reversal tagging"""
    df['pattern'] = None
    df['is_reversal'] = False
    
    # Body and shadows
    df['body_size'] = abs(df['close'] - df['open'])
    df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
    avg_body = df['body_size'].mean()

    # Reversal Patterns
    # Hammer (Bullish Reversal)
    hammer = (
        (df['body_size'] <= 0.3 * (df['high'] - df['low'])) &
        (df['lower_shadow'] >= 2 * df['body_size']) &
        (df['upper_shadow'] <= 0.1 * (df['high'] - df['low'])) &
        (df['close'].rolling(5).mean() < df['close'].rolling(10).mean())  # Downtrend
    )
    df.loc[hammer, ['pattern', 'is_reversal']] = ['Hammer', True]

    # Shooting Star (Bearish Reversal)
    shooting_star = (
        (df['body_size'] <= 0.3 * (df['high'] - df['low'])) &
        (df['upper_shadow'] >= 2 * df['body_size']) &
        (df['lower_shadow'] <= 0.1 * (df['high'] - df['low'])) &
        (df['close'].rolling(5).mean() > df['close'].rolling(10).mean())  # Uptrend
    )
    df.loc[shooting_star, ['pattern', 'is_reversal']] = ['Shooting Star', True]

    # Engulfing Patterns
    for i in range(1, len(df)):
        # Bullish Engulfing (Reversal)
        if (df['open'].iloc[i] < df['close'].iloc[i] and
            df['open'].iloc[i-1] > df['close'].iloc[i-1] and
            df['open'].iloc[i] <= df['close'].iloc[i-1] and
            df['close'].iloc[i] >= df['open'].iloc[i-1]):
            df.loc[df.index[i], ['pattern', 'is_reversal']] = ['Bullish Engulfing', True]

        # Bearish Engulfing (Reversal)
        if (df['open'].iloc[i] > df['close'].iloc[i] and
            df['open'].iloc[i-1] < df['close'].iloc[i-1] and
            df['open'].iloc[i] >= df['close'].iloc[i-1] and
            df['close'].iloc[i] <= df['open'].iloc[i-1]):
            df.loc[df.index[i], ['pattern', 'is_reversal']] = ['Bearish Engulfing', True]

    # Cleanup
    df = df.drop(['body_size', 'upper_shadow', 'lower_shadow'], axis=1)
    return df

def get_pattern_recommendation(pattern):
    """Updated with reversal strength"""
    recommendations = {
        # Reversal Patterns
        'Hammer': {'action': 'BUY', 'strength': 'strong', 'reversal': True, 'duration': '15-30m'},
        'Shooting Star': {'action': 'SELL', 'strength': 'strong', 'reversal': True, 'duration': '15-30m'},
        'Bullish Engulfing': {'action': 'BUY', 'strength': 'very strong', 'reversal': True, 'duration': '30-60m'},
        'Bearish Engulfing': {'action': 'SELL', 'strength': 'very strong', 'reversal': True, 'duration': '30-60m'},
        
        # Continuation Patterns
        'Three White Soldiers': {'action': 'BUY', 'strength': 'strong', 'reversal': False, 'duration': '60m+'},
        'Three Black Crows': {'action': 'SELL', 'strength': 'strong', 'reversal': False, 'duration': '60m+'},
        
        # Neutral Patterns
        'Doji': {'action': 'NEUTRAL', 'strength': 'weak', 'reversal': False, 'duration': 'N/A'}
    }
    return recommendations.get(pattern, {'action': 'NEUTRAL', 'strength': 'none', 'reversal': False, 'duration': 'N/A'})