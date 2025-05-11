import threading
import time
import pandas as pd
from datetime import datetime
import streamlit as st
from utils.deriv_api import DerivAPI

class AutoTrader:
    def __init__(self, api_token=None):
        self.api_token = api_token
        self.api = None
        self.active_trades = []  # Now properly initialized as a list
        self.trade_history = []  # Now properly initialized as a list
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.amount = 10.0
        self.take_profit = 5.0
        self.stop_loss = 2.0
        self.trade_duration = 5

    def connect(self, api_token=None):
        """Connect to Deriv API"""
        if api_token:
            self.api_token = api_token
            
        if not self.api_token:
            st.error("No API token provided")
            return False
            
        try:
            self.api = DerivAPI(api_token=self.api_token)
            st.success("✅ Connected to Deriv API")
            return True
        except Exception as e:
            st.error(f"🔴 Connection failed: {str(e)}")
            return False

    def start(self, amount=10.0, take_profit=5.0, stop_loss=2.0, trade_duration=5):
        """Start automated trading"""
        if self.running:
            st.warning("⚠️ Bot is already running")
            return False
            
        if not self.api:
            if not self.connect():
                return False
                
        self.amount = amount
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.trade_duration = trade_duration
        self.running = True
        
        self.thread = threading.Thread(target=self._monitor_trades)
        self.thread.daemon = True
        self.thread.start()
        
        st.success("🚀 Automated trading started")
        return True

    def stop(self):
        """Stop automated trading"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        st.warning("🛑 Automated trading stopped")
        return True

    def process_signal(self, signal):
        """Process trading signal"""
        if not self.running or not self.api:
            st.error("Trading not active or API not connected")
            return None
            
        try:
            contract_type = 'CALL' if signal['action'] == 'BUY' else 'PUT'
            
            # Dynamic position sizing
            base_amount = self.amount
            if signal.get('reversal_type'):
                multiplier = 2.0  # 2x for reversals
                if signal.get('confidence', '0%') >= '80%':
                    multiplier = 3.0  # 3x for high-confidence
                trade_amount = base_amount * multiplier
            else:
                trade_amount = base_amount

            with self.lock:
                trade = self.api.buy_contract(
                    symbol=signal['symbol'],
                    amount=trade_amount,
                    duration=self.trade_duration,
                    duration_unit='m',
                    contract_type=contract_type
                )
                
            if trade:
                trade.update({
                    'signal_id': signal.get('id'),
                    'signal_confidence': signal.get('confidence'),
                    'action': signal['action'],
                    'reversal': bool(signal.get('reversal_type')),
                    'take_profit': trade['price'] * (1 + self.take_profit/100) if contract_type == 'CALL' else trade['price'] * (1 - self.take_profit/100),
                    'stop_loss': trade['price'] * (1 - self.stop_loss/100) if contract_type == 'CALL' else trade['price'] * (1 + self.stop_loss/100),
                    'time_opened': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'amount': trade_amount
                })
                
                self.active_trades.append(trade)
                st.success(f"💰 Trade opened: {signal['symbol']} {signal['action']} (${trade_amount})")
                return trade
                
        except Exception as e:
            st.error(f"❌ Trade failed: {str(e)}")
            return None

    def _monitor_trades(self):
        """Monitor active trades"""
        while self.running:
            time.sleep(5)
            
            if not self.api or not self.active_trades:
                continue
                
            with self.lock:
                for trade in list(self.active_trades):  # Create a copy for iteration
                    try:
                        status = self.api.check_contract(trade['contract_id'])
                        if not status:
                            continue
                            
                        if status['status'] == 'closed':
                            self._close_trade(trade, status)
                        else:
                            current_price = status.get('current_spot')
                            if current_price:
                                is_buy = trade['action'] == 'BUY'
                                hit_take_profit = current_price >= trade['take_profit'] if is_buy else current_price <= trade['take_profit']
                                hit_stop_loss = current_price <= trade['stop_loss'] if is_buy else current_price >= trade['stop_loss']
                                
                                if hit_take_profit or hit_stop_loss:
                                    self._close_trade_early(trade)
                    except Exception as e:
                        st.error(f"Monitoring error: {str(e)}")

    def _close_trade(self, trade, status):
        """Handle closed trade"""
        with self.lock:
            trade.update(status)
            self.trade_history.append(trade)
            if trade in self.active_trades:
                self.active_trades.remove(trade)
        
        if 'st' in globals():
            profit = status.get('profit', 0)
            st.session_state.total_profit = st.session_state.get('total_profit', 0) + profit
            st.session_state.wins = st.session_state.get('wins', 0) + (1 if profit > 0 else 0)
            st.session_state.losses = st.session_state.get('losses', 0) + (1 if profit <= 0 else 0)

    def _close_trade_early(self, trade):
        """Handle early trade closure"""
        try:
            sell_result = self.api.sell_contract(trade['contract_id'])
            if sell_result:
                self._close_trade(trade, sell_result)
                st.success(f"🔚 Trade closed early: {trade['symbol']}")
        except Exception as e:
            st.error(f"Early closure failed: {str(e)}")

    def get_status(self):
        """Get current bot status with proper list handling"""
        return {
            'running': self.running,
            'connected': self.api is not None,
            'active_trades': self.active_trades.copy(),  # Ensure this is always a list
            'total_trades': len(self.trade_history),
            'last_trade': self.trade_history[-1] if self.trade_history else None
        }

    def get_trade_history(self):
        """Get complete trade history as DataFrame"""
        return pd.DataFrame(self.trade_history if isinstance(self.trade_history, list) else [])

    def clear_history(self):
        """Clear trade history"""
        with self.lock:
            self.trade_history = []
            return True

    def get_active_trades(self):
        """Get current active trades"""
        return self.active_trades.copy() if isinstance(self.active_trades, list) else []