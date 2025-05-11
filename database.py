import os
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

# Create database connection
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_qK7lf8DtWdzc@ep-flat-rice-a4txj3f4.us-east-1.aws.neon.tech/neondb?sslmode=require')
if DATABASE_URL is None:
    raise ValueError("DATABASE_URL environment variable is not set")
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define Signal model
class Signal(Base):
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    action = Column(String(10), nullable=False)  # BUY or SELL
    time = Column(DateTime, nullable=False)
    duration = Column(String(20))
    rsi_value = Column(Float)
    rsi_condition = Column(String(20))
    macd_condition = Column(String(40))
    ma_condition = Column(String(40))
    pattern = Column(String(40))
    confidence = Column(String(10))
    price = Column(Float)
    result = Column(String(20), nullable=True)  # WIN, LOSS, or NULL if not determined yet
    profit_loss = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'action': self.action,
            'time': self.time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration': self.duration,
            'rsi_value': self.rsi_value,
            'rsi_condition': self.rsi_condition,
            'macd_condition': self.macd_condition,
            'ma_condition': self.ma_condition,
            'pattern': self.pattern,
            'confidence': self.confidence,
            'price': self.price,
            'result': self.result,
            'profit_loss': self.profit_loss,
            'notes': self.notes
        }

# Create tables
Base.metadata.create_all(engine)

# Create session
Session = sessionmaker(bind=engine)

def save_signal(signal_dict):
    """
    Save a signal to the database
    
    Parameters:
    signal_dict (dict): Signal data dictionary
    
    Returns:
    int: ID of the saved signal
    """
    session = Session()
    try:
        # Convert time string to datetime object
        signal_time = datetime.strptime(signal_dict['time'], '%Y-%m-%d %H:%M:%S')
        
        # Check if signal already exists (avoid duplicates)
        existing_query = session.query(Signal).filter_by(
            symbol=signal_dict['symbol'],
            action=signal_dict['action']
        )
        
        for row in existing_query:
            # Manual time comparison to avoid SQLAlchemy expression issues
            if row.time == signal_time:
                return row.id
        
        # Create new signal
        signal = Signal(
            symbol=signal_dict['symbol'],
            action=signal_dict['action'],
            time=signal_time,
            duration=signal_dict['duration'],
            rsi_value=signal_dict['rsi_value'],
            rsi_condition=signal_dict['rsi_condition'],
            macd_condition=signal_dict['macd_condition'],
            ma_condition=signal_dict['ma_condition'],
            pattern=signal_dict['pattern'],
            confidence=signal_dict['confidence'],
            price=signal_dict.get('price', 0.0)
        )
        
        session.add(signal)
        session.commit()
        return signal.id
    except Exception as e:
        session.rollback()
        print(f"Error saving signal: {e}")
        return None
    finally:
        session.close()

def get_signals(hours=24, symbol=None, result=None, limit=100):
    """
    Get signals from the database
    
    Parameters:
    hours (int): Get signals from the last N hours (default: 24)
    symbol (str): Filter by symbol (optional)
    result (str): Filter by result (WIN, LOSS) (optional)
    limit (int): Maximum number of signals to return (default: 100)
    
    Returns:
    list: List of signal dictionaries
    """
    session = Session()
    try:
        query = session.query(Signal)
        
        # Filter by time
        if hours > 0:
            time_threshold = datetime.now() - timedelta(hours=hours)
            query = query.filter(Signal.time >= time_threshold)
        
        # Additional filters
        if symbol:
            query = query.filter(Signal.symbol == symbol)
            
        if result:
            query = query.filter(Signal.result == result)
        
        # Order by time (newest first) and limit
        query = query.order_by(Signal.time.desc()).limit(limit)
        
        # Convert to list of dictionaries
        signals = [signal.to_dict() for signal in query.all()]
        return signals
    except Exception as e:
        print(f"Error getting signals: {e}")
        return []
    finally:
        session.close()

def update_signal_result(signal_id, result, profit_loss=None, notes=None):
    """
    Update a signal's result (win/loss)
    
    Parameters:
    signal_id (int): Signal ID
    result (str): Result (WIN or LOSS)
    profit_loss (float): Profit or loss amount (optional)
    notes (str): Additional notes (optional)
    
    Returns:
    bool: Success or failure
    """
    session = Session()
    try:
        signal = session.query(Signal).filter(Signal.id == signal_id).first()
        if not signal:
            return False
        
        signal.result = result
        
        if profit_loss is not None:
            signal.profit_loss = profit_loss
            
        if notes is not None:
            signal.notes = notes
            
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error updating signal result: {e}")
        return False
    finally:
        session.close()

def get_signals_performance(days=30):
    """
    Get performance statistics of trading signals
    
    Parameters:
    days (int): Get statistics from the last N days (default: 30)
    
    Returns:
    dict: Dictionary with performance statistics
    """
    session = Session()
    try:
        time_threshold = datetime.now() - timedelta(days=days)
        
        # Get all signals with results in the time period
        signals = session.query(Signal).filter(
            Signal.time >= time_threshold,
            Signal.result.in_(['WIN', 'LOSS'])
        ).all()
        
        # Initialize statistics
        total_signals = len(signals)
        win_count = sum(1 for s in signals if s.result == 'WIN')
        loss_count = sum(1 for s in signals if s.result == 'LOSS')
        
        # Profit calculation
        total_profit = sum(s.profit_loss for s in signals if s.profit_loss is not None)
        
        # Win rate calculation
        win_rate = (win_count / total_signals * 100) if total_signals > 0 else 0
        
        # Symbol-specific performance
        symbols = {}
        for s in signals:
            if s.symbol not in symbols:
                symbols[s.symbol] = {
                    'total': 0,
                    'wins': 0,
                    'losses': 0,
                    'profit': 0
                }
            
            symbols[s.symbol]['total'] += 1
            if s.result == 'WIN':
                symbols[s.symbol]['wins'] += 1
            else:
                symbols[s.symbol]['losses'] += 1
                
            if s.profit_loss is not None:
                symbols[s.symbol]['profit'] += s.profit_loss
        
        # Calculate win rates for each symbol
        for symbol in symbols:
            symbol_total = symbols[symbol]['total']
            symbols[symbol]['win_rate'] = (symbols[symbol]['wins'] / symbol_total * 100) if symbol_total > 0 else 0
        
        return {
            'total_signals': total_signals,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'symbols': symbols,
            'days': days
        }
    except Exception as e:
        print(f"Error getting performance statistics: {e}")
        return {
            'total_signals': 0,
            'win_count': 0,
            'loss_count': 0,
            'win_rate': 0,
            'total_profit': 0,
            'symbols': {},
            'days': days,
            'error': str(e)
        }
    finally:
        session.close()

def get_signals_dataframe(days=30, symbol=None):
    """
    Get signals as a pandas DataFrame
    
    Parameters:
    days (int): Get signals from the last N days (default: 30)
    symbol (str): Filter by symbol (optional)
    
    Returns:
    pd.DataFrame: DataFrame with signals
    """
    signals = get_signals(hours=days*24, symbol=symbol)
    if not signals:
        return pd.DataFrame()
    
    df = pd.DataFrame(signals)
    # Convert time string to datetime
    df['time'] = pd.to_datetime(df['time'])
    return df